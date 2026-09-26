
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

@st.cache_data(ttl=3600)
def get_sales_date_range():

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                MIN(InvoiceDate_New),
                MAX(InvoiceDate_New)
            FROM dbo.PrimarySales
            WHERE InvoiceDate_New IS NOT NULL
        """)

        row = cursor.fetchone()

        if row is None:
            return None, None

        return row[0], row[1]

    finally:
        conn.close()


min_report_date, max_report_date = get_dcr_date_range()
min_sales_date, max_sales_date = get_sales_date_range()

if min_report_date is None or max_report_date is None:
    st.error("No ReportDate values were found in DCRReport.")
    st.stop()

if min_sales_date is None or max_sales_date is None:
    st.error("No InvoiceDate_New values were found in PrimarySales.")
    st.stop()

# Combined actual data range for dashboard filters
dashboard_min_date = min(
    min_report_date,
    min_sales_date
)

dashboard_max_date = max(
    max_report_date,
    max_sales_date
)

# =========================================================
# FILTER VALUES
# =========================================================

@st.cache_data(ttl=3600)
def get_designations():

    return fetch_list("""
        SELECT DISTINCT
            LEFT(
                C_FS_Code,
                PATINDEX('%[0-9]%', C_FS_Code + '0') - 1
            ) AS Designation

        FROM dbo.DCRReport

        WHERE C_FS_Code IS NOT NULL
          AND LTRIM(RTRIM(C_FS_Code)) <> ''

        ORDER BY Designation
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
# DIMDATE FILTER FUNCTIONS
# =========================================================

@st.cache_data(ttl=3600)
def get_dim_years(min_date, max_date):

    return fetch_list("""
        SELECT DISTINCT YearNumber
        FROM dbo.DimDate
        WHERE YearNumber IS NOT NULL
          AND FullDate >= %s
          AND FullDate <= %s
        ORDER BY YearNumber DESC
    """, (min_date, max_date))


@st.cache_data(ttl=3600)
def get_dim_quarters(
    year,
    min_date,
    max_date
):

    return fetch_list("""
        SELECT DISTINCT QuarterNumber
        FROM dbo.DimDate
        WHERE YearNumber = %s
          AND FullDate >= %s
          AND FullDate <= %s
        ORDER BY QuarterNumber
    """, (
        year,
        min_date,
        max_date
    ))


@st.cache_data(ttl=3600)
def get_dim_months(
    year,
    min_date,
    max_date,
    quarter=None
):

    query = """
        SELECT DISTINCT
            MonthNumber,
            MonthName
        FROM dbo.DimDate
        WHERE YearNumber = %s
          AND FullDate >= %s
          AND FullDate <= %s
    """

    params = [
        year,
        min_date,
        max_date
    ]

    if quarter is not None:

        query += """
            AND QuarterNumber = %s
        """

        params.append(quarter)

    query += """
        ORDER BY MonthNumber
    """

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            query,
            tuple(params)
        )

        return cursor.fetchall()

    finally:

        conn.close()

# =========================================================
# DCR KPI QUERY
# =========================================================
def format_indian_currency(value):

    value = float(value or 0)

    if abs(value) >= 10000000:
        return f"₹{value / 10000000:,.2f} Cr"

    elif abs(value) >= 100000:
        return f"₹{value / 100000:,.2f} L"

    elif abs(value) >= 1000:
        return f"₹{value / 1000:,.2f} K"

    else:
        return f"₹{value:,.2f}"

def format_quantity(value):

    value = float(value or 0)

    if abs(value) >= 10000000:
        return f"{value / 10000000:,.2f} Cr"

    elif abs(value) >= 100000:
        return f"{value / 100000:,.2f} L"

    elif abs(value) >= 1000:
        return f"{value / 1000:,.2f} K"

    else:
        return f"{value:,.0f}"

def format_count(value):
    return f"{int(value or 0):,}"
    
@st.cache_data(ttl=600)
def get_dcr_kpis(
    start_date,
    end_date,
    designation=None,
    division_code=None
):

    query = """
        SELECT
            COUNT(DISTINCT d.C_EmpNo) AS ActiveEmployees,
            COUNT(DISTINCT d.C_DSC_Code) AS UniqueDoctors,
            COUNT(DISTINCT d.ItemCode) AS ProductsDetailed
        FROM dbo.DCRReport d
    """

    conditions = [
        "d.ReportDate >= %s",
        "d.ReportDate < %s",
        "d.C_EmpNo IS NOT NULL",
        "d.C_EmpNo <> '000000'"
    ]

    params = [
        start_date,
        end_date
    ]


    # Designation filter
    if designation is not None:

        conditions.append("""
            LEFT(
                d.C_FS_Code,
                PATINDEX('%[0-9]%', d.C_FS_Code + '0') - 1
            ) = %s
        """)

        params.append(designation)

    # Division filter
    if division_code is not None:

        conditions.append(
            "d.DivisionCode = %s"
        )

        params.append(
            division_code
        )


    query += "\nWHERE " + "\nAND ".join(conditions)


    conn = get_connection()

    try:
        cursor = conn.cursor(as_dict=True)

        cursor.execute(
            query,
            tuple(params)
        )

        return cursor.fetchone()

    finally:
        conn.close()

# @st.cache_data(ttl=600)
# def get_doctor_day_contacts(
#     start_date,
#     end_date,
#     designation=None,
#     division_code=None
# ):

#     query = """
#         SELECT COUNT(*) AS DoctorDayContacts
#         FROM
#         (
#             SELECT
#                 d.C_EmpNo,
#                 d.C_DSC_Code,
#                 d.ReportDate

#             FROM dbo.DCRReport d
#     """

#     conditions = [
#         "d.ReportDate >= %s",
#         "d.ReportDate < %s",
#         "d.C_EmpNo IS NOT NULL",
#         "d.C_DSC_Code IS NOT NULL",
#         "d.C_EmpNo <> '000000'"
#     ]

#     params = [start_date, end_date]

#     if designation is not None:
#         conditions.append("""
#             LEFT(
#                 d.C_FS_Code,
#                 PATINDEX('%[0-9]%', d.C_FS_Code + '0') - 1
#             ) = %s
#         """)
    
#         params.append(designation)

#     if division_code is not None:
#         conditions.append("d.DivisionCode = %s")
#         params.append(division_code)

#     query += "\nWHERE " + "\nAND ".join(conditions)

#     query += """
#             GROUP BY
#                 d.C_EmpNo,
#                 d.C_DSC_Code,
#                 d.ReportDate
#         ) x
#     """

#     conn = get_connection()

#     try:
#         cursor = conn.cursor(as_dict=True)

#         cursor.execute(
#             query,
#             tuple(params)
#         )

#         row = cursor.fetchone()

#         return int(row["DoctorDayContacts"] or 0)

#     finally:
#         conn.close()



# =========================================================
# PRIMARY SALES KPI QUERY
# =========================================================
@st.cache_data(ttl=600)
def get_sales_kpis(
    start_date,
    end_date,
    division_code=None
):

    query = """
        SELECT
            SUM(
                CASE
                    WHEN NetAmount > 0
                    THEN NetAmount
                    ELSE 0
                END
            ) AS GrossSales,

            ABS(
                SUM(
                    CASE
                        WHEN NetAmount < 0
                        THEN NetAmount
                        ELSE 0
                    END
                )
            ) AS ReturnsAmount,

            SUM(NetAmount) AS NetSales,

            SUM(
                CASE
                    WHEN NetQty > 0
                    THEN NetQty
                    ELSE 0
                END
            ) AS GrossQty,

            ABS(
                SUM(
                    CASE
                        WHEN NetQty < 0
                        THEN NetQty
                        ELSE 0
                    END
                )
            ) AS ReturnQty,

            SUM(NetQty) AS NetQty,

            COUNT(DISTINCT MaterialCode) AS ProductsSold,

            COUNT_BIG(*) AS SalesRecords

        FROM dbo.PrimarySales

        WHERE InvoiceDate_New >= %s
          AND InvoiceDate_New < %s
    """

    params = [start_date, end_date]

    if division_code is not None:
        query += """
            AND DivisionCode = %s
        """
        params.append(division_code)

    conn = get_connection()

    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(query, tuple(params))
        return cursor.fetchone()

    finally:
        conn.close()

# =========================================================
# AVAILABLE YEARS
# =========================================================

available_years = get_dim_years(
    dashboard_min_date,
    dashboard_max_date
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Filters")


# =========================================================
# YEAR
# =========================================================

year_options = ["All"] + available_years

selected_year = st.sidebar.selectbox(
    "Year",
    year_options,
    index=0
)


# =========================================================
# QUARTER
# =========================================================

if selected_year == "All":

    quarter_options = {
        "All": None
    }

else:

    dim_quarters = get_dim_quarters(
        selected_year,
        dashboard_min_date,
        dashboard_max_date
    )

    quarter_options = {
        "All": None
    }

    for q in dim_quarters:

        quarter_options[
            f"Q{q}"
        ] = q


selected_quarter_label = st.sidebar.selectbox(
    "Quarter",
    list(quarter_options.keys()),
    index=0
)

selected_quarter = quarter_options[
    selected_quarter_label
]
# =========================================================
# MONTH
# =========================================================

month_options = {
    "All": None
}


if selected_year != "All":

    month_rows = get_dim_months(
        selected_year,
        dashboard_min_date,
        dashboard_max_date,
        selected_quarter
    )

    for (
        month_number,
        month_name
    ) in month_rows:

        month_options[
            month_name
        ] = month_number


selected_month_label = st.sidebar.selectbox(
    "Month",
    list(month_options.keys()),
    index=0
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

if selected_year == "All":

    start_date = dashboard_min_date

    end_date = (
        dashboard_max_date
        + timedelta(days=1)
    )

else:

    start_date, end_date = get_date_range(
        selected_year,
        selected_quarter,
        selected_month
    )
# =========================================================
# SOURCE-SPECIFIC DATE RANGES
# =========================================================

# DCR date range
dcr_start_date = max(
    start_date,
    min_report_date
)

dcr_end_date = min(
    end_date,
    max_report_date + timedelta(days=1)
)

dcr_has_data = (
    dcr_start_date
    < dcr_end_date
)


# Primary Sales date range
sales_start_date = max(
    start_date,
    min_sales_date
)

sales_end_date = min(
    end_date,
    max_sales_date + timedelta(days=1)
)

sales_has_data = (
    sales_start_date
    < sales_end_date
)



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

    with st.spinner(
        "Loading DCR KPIs..."
    ):

        if dcr_has_data:

            kpis = get_dcr_kpis(
                start_date=dcr_start_date,
                end_date=dcr_end_date,
                designation=designation_value,
                division_code=division_code
            )

        else:

            kpis = {
                "ActiveEmployees": 0,
                "UniqueDoctors": 0,
                "ProductsDetailed": 0
            }


        # Doctor-Day Contacts is temporarily kept commented
        # because the current query is expensive on the
        # large DCRReport table.
        #
        # doctor_day_contacts = get_doctor_day_contacts(
        #     start_date=dcr_start_date,
        #     end_date=dcr_end_date,
        #     designation=designation_value,
        #     division_code=division_code
        # )


except Exception as error:

    st.error(
        "The DCR query could not be completed. "
        "Please try selecting a smaller period "
        "such as a month or quarter."
    )

    st.exception(error)

    st.stop()


try:

    with st.spinner(
        "Loading Primary Sales KPIs..."
    ):

        if sales_has_data:

            sales_kpis = get_sales_kpis(
                start_date=sales_start_date,
                end_date=sales_end_date,
                division_code=division_code
            )

        else:

            sales_kpis = {
                "GrossSales": 0,
                "ReturnsAmount": 0,
                "NetSales": 0,
                "GrossQty": 0,
                "ReturnQty": 0,
                "NetQty": 0,
                "ProductsSold": 0,
                "SalesRecords": 0
            }


except Exception as error:

    st.error(
        "The Primary Sales query "
        "could not be completed."
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


col1, col2, col3 = st.columns(3)

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
        "Products Detailed",
        f"{int(kpis['ProductsDetailed'] or 0):,}"
    )

# =========================================================
# PRIMARY SALES KPI CARDS
# =========================================================
st.subheader("Primary Sales Performance")

st.caption(
    f"Data available: "
    f"{min_sales_date.strftime('%d %b %Y')} "
    f"to "
    f"{max_sales_date.strftime('%d %b %Y')}"
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

s1, s2, s3, s4 = st.columns(4)

with s1:
    st.metric(
        "Gross Sales",
        format_indian_currency(
            sales_kpis["GrossSales"]
        )
    )

with s2:
    st.metric(
        "Returns",
        format_indian_currency(
            sales_kpis["ReturnsAmount"]
        )
    )

with s3:
    st.metric(
        "Net Sales",
        format_indian_currency(
            sales_kpis["NetSales"]
        )
    )

with s4:
    st.metric(
        "Products Sold",
        format_count(
            sales_kpis["ProductsSold"]
        )
    )


s5, s6, s7, s8 = st.columns(4)

with s5:
    st.metric(
        "Gross Quantity",
        format_quantity(
            sales_kpis["GrossQty"]
        )
    )

with s6:
    st.metric(
        "Return Quantity",
        format_quantity(
            sales_kpis["ReturnQty"]
        )
    )

with s7:
    st.metric(
        "Net Quantity",
        format_quantity(
            sales_kpis["NetQty"]
        )
    )

with s8:
    st.metric(
        "Sales Records",
        format_count(
            sales_kpis["SalesRecords"]
        )
    )
