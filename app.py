import streamlit as st
import pymssql
from datetime import date, timedelta


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="DCR Performance Dashboard",
    layout="wide"
)

st.title("DCR Performance Dashboard")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    return pymssql.connect(
        server=st.secrets["DB_SERVER"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        login_timeout=15,
        timeout=300
    )


# =========================================================
# SIMPLE QUERY HELPER
# =========================================================

def fetch_list(query, params=None):

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            query,
            params or ()
        )

        rows = cursor.fetchall()

        return [
            row[0]
            for row in rows
            if row[0] is not None
        ]

    finally:
        conn.close()


# =========================================================
# ACTUAL DCR DATE RANGE
# =========================================================

@st.cache_data(ttl=3600)
def get_dcr_date_range():

    conn = get_connection()

    try:
        cursor = conn.cursor()

        # Earliest available ReportDate
        cursor.execute("""
            SELECT TOP 1 ReportDate
            FROM dbo.DCRReport
            WHERE ReportDate IS NOT NULL
            ORDER BY ReportDate ASC
        """)

        min_row = cursor.fetchone()

        # Latest available ReportDate
        cursor.execute("""
            SELECT TOP 1 ReportDate
            FROM dbo.DCRReport
            WHERE ReportDate IS NOT NULL
            ORDER BY ReportDate DESC
        """)

        max_row = cursor.fetchone()

        if min_row is None or max_row is None:
            return None, None

        return min_row[0], max_row[0]

    finally:
        conn.close()


min_report_date, max_report_date = get_dcr_date_range()


if min_report_date is None or max_report_date is None:
    st.error("No ReportDate values were found in DCRReport.")
    st.stop()


# =========================================================
# FILTER VALUES
# =========================================================

@st.cache_data(ttl=3600)
def get_designations():

    return fetch_list("""
        SELECT DISTINCT
            LTRIM(RTRIM(newdesg))
        FROM dbo.employeedata
        WHERE newdesg IS NOT NULL
          AND LTRIM(RTRIM(newdesg)) <> ''
          AND LTRIM(RTRIM(newdesg)) <> '--Select--'
        ORDER BY LTRIM(RTRIM(newdesg))
    """)


@st.cache_data(ttl=3600)
def get_divisions():

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT
                DivisionCode,
                DivisionName
            FROM dbo.Division
            WHERE DivisionCode IS NOT NULL
              AND DivisionName IS NOT NULL
            ORDER BY DivisionName
        """)

        return cursor.fetchall()

    finally:
        conn.close()


# =========================================================
# DATE RANGE FUNCTION
# =========================================================

def get_date_range(year, quarter=None, month=None):

    # Month selected
    if month is not None:

        start_date = date(
            year,
            month,
            1
        )

        if month == 12:
            end_date = date(
                year + 1,
                1,
                1
            )

        else:
            end_date = date(
                year,
                month + 1,
                1
            )

        return start_date, end_date


    # Quarter selected
    if quarter is not None:

        start_month = ((quarter - 1) * 3) + 1

        start_date = date(
            year,
            start_month,
            1
        )

        if quarter == 4:
            end_date = date(
                year + 1,
                1,
                1
            )

        else:
            end_date = date(
                year,
                start_month + 3,
                1
            )

        return start_date, end_date


    # Whole year
    return (
        date(year, 1, 1),
        date(year + 1, 1, 1)
    )


# =========================================================
# DCR KPI QUERY
# =========================================================

@st.cache_data(ttl=600)
def get_dcr_kpis(
    start_date,
    end_date,
    designation=None,
    division_code=None
):

    query = """
        SELECT

            COUNT(DISTINCT d.C_EmpNo)
                AS ActiveEmployees,

            COUNT(DISTINCT d.C_DSC_Code)
                AS UniqueDoctors,

            COUNT(
                DISTINCT CONCAT(
                    d.C_EmpNo,
                    '|',
                    d.C_DSC_Code,
                    '|',
                    CONVERT(VARCHAR(10), d.ReportDate, 23)
                )
            ) AS DoctorDayContacts,

            COUNT(DISTINCT d.ItemCode)
                AS ProductsDetailed,

            COUNT_BIG(*)
                AS TotalDCRRecords

        FROM dbo.DCRReport d
    """

    conditions = [
        "d.ReportDate >= %s",
        "d.ReportDate < %s",
        "d.C_EmpNo IS NOT NULL",
        "LTRIM(RTRIM(d.C_EmpNo)) <> '000000'"
    ]

    params = [
        start_date,
        end_date
    ]


    # -----------------------------------------------------
    # DESIGNATION
    # -----------------------------------------------------

    if designation is not None:

        query += """
            INNER JOIN dbo.employeedata e
                ON LTRIM(RTRIM(d.C_EmpNo))
                 = LTRIM(RTRIM(e.empCODE))
        """

        conditions.append(
            "LTRIM(RTRIM(e.newdesg)) = %s"
        )

        params.append(designation)


    # -----------------------------------------------------
    # DIVISION
    # -----------------------------------------------------

    if division_code is not None:

        conditions.append(
            "LTRIM(RTRIM(d.DivisionCode)) = %s"
        )

        params.append(division_code)


    query += "\nWHERE " + "\nAND ".join(conditions)


    conn = get_connection()

    try:
        cursor = conn.cursor(as_dict=True)

        cursor.execute(
            query,
            tuple(params)
        )

        result = cursor.fetchone()

        return result

    finally:
        conn.close()


# =========================================================
# AVAILABLE YEARS
# =========================================================

available_years = list(
    range(
        max_report_date.year,
        min_report_date.year - 1,
        -1
    )
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Filters")


# =========================================================
# YEAR
# =========================================================

selected_year = st.sidebar.selectbox(
    "Year",
    available_years
)


# =========================================================
# QUARTER
# =========================================================

quarter_options = {
    "All": None,
    "Q1": 1,
    "Q2": 2,
    "Q3": 3,
    "Q4": 4
}

selected_quarter_label = st.sidebar.selectbox(
    "Quarter",
    list(quarter_options.keys())
)

selected_quarter = quarter_options[
    selected_quarter_label
]


# =========================================================
# MONTH
# =========================================================

all_months = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December"
}


# Months according to quarter
if selected_quarter == 1:
    valid_months = [1, 2, 3]

elif selected_quarter == 2:
    valid_months = [4, 5, 6]

elif selected_quarter == 3:
    valid_months = [7, 8, 9]

elif selected_quarter == 4:
    valid_months = [10, 11, 12]

else:
    valid_months = list(range(1, 13))


# Remove months before first available DCR month
# and after latest available DCR month
valid_months = [
    month_number
    for month_number in valid_months

    if not (
        selected_year == min_report_date.year
        and month_number < min_report_date.month
    )

    and not (
        selected_year == max_report_date.year
        and month_number > max_report_date.month
    )
]


month_options = {
    "All": None
}

for month_number in valid_months:

    month_options[
        all_months[month_number]
    ] = month_number


selected_month_label = st.sidebar.selectbox(
    "Month",
    list(month_options.keys())
)

selected_month = month_options[
    selected_month_label
]


# =========================================================
# DESIGNATION
# =========================================================

designations = get_designations()

selected_designation = st.sidebar.selectbox(
    "Designation",
    ["All"] + designations
)

designation_value = (
    None
    if selected_designation == "All"
    else selected_designation
)


# =========================================================
# DIVISION
# =========================================================

division_rows = get_divisions()

division_map = {
    division_name: division_code
    for division_code, division_name in division_rows
}

selected_division = st.sidebar.selectbox(
    "Division",
    ["All"] + list(division_map.keys())
)

division_code = (
    None
    if selected_division == "All"
    else division_map[selected_division]
)


# =========================================================
# CONVERT FILTERS TO DATE RANGE
# =========================================================

start_date, end_date = get_date_range(
    selected_year,
    selected_quarter,
    selected_month
)


# =========================================================
# CLAMP RANGE TO ACTUAL DCR DATA
# =========================================================

if start_date < min_report_date:
    start_date = min_report_date


actual_max_end = (
    max_report_date
    + timedelta(days=1)
)


if end_date > actual_max_end:
    end_date = actual_max_end


# =========================================================
# HANDLE PERIOD WITH NO DATA
# =========================================================

if start_date >= end_date:

    st.warning(
        "No DCR data is available for the selected period."
    )

    st.stop()


# =========================================================
# DISPLAY AVAILABLE / SELECTED RANGE
# =========================================================

st.caption(
    f"Data available: "
    f"{min_report_date.strftime('%d %b %Y')} "
    f"to "
    f"{max_report_date.strftime('%d %b %Y')}"
)


selected_end_display = (
    end_date
    - timedelta(days=1)
)


st.caption(
    f"Selected period: "
    f"{start_date.strftime('%d %b %Y')} "
    f"to "
    f"{selected_end_display.strftime('%d %b %Y')}"
)


# =========================================================
# GET KPI DATA
# =========================================================

try:

    with st.spinner("Loading dashboard..."):

        kpis = get_dcr_kpis(
            start_date=start_date,
            end_date=end_date,
            designation=designation_value,
            division_code=division_code
        )

except Exception as error:

    st.error(
        "The DCR query could not be completed. "
        "Please try selecting a smaller period such as a month or quarter."
    )

    st.exception(error)

    st.stop()


# =========================================================
# KPI CARDS
# =========================================================

if kpis is None:

    st.warning(
        "No DCR records were found for the selected filters."
    )

    st.stop()


col1, col2, col3, col4, col5 = st.columns(5)


with col1:

    st.metric(
        "Active Employees",
        f"{int(kpis['ActiveEmployees'] or 0):,}"
    )


with col2:

    st.metric(
        "Unique Doctors",
        f"{int(kpis['UniqueDoctors'] or 0):,}"
    )


with col3:

    st.metric(
        "Doctor-Day Contacts",
        f"{int(kpis['DoctorDayContacts'] or 0):,}"
    )


with col4:

    st.metric(
        "Products Detailed",
        f"{int(kpis['ProductsDetailed'] or 0):,}"
    )


with col5:

    st.metric(
        "DCR Records",
        f"{int(kpis['TotalDCRRecords'] or 0):,}"
    )
