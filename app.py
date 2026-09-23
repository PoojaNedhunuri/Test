import streamlit as st

import pymssql

import pandas as pd

from datetime import date, timedelta
 
st.set_page_config(

    page_title="ASRA DCR Dashboard",

    layout="wide"

)
 
st.title("ASRA DCR Performance")
 
 
# -------------------------

# DATABASE CONNECTION

# -------------------------
 
@st.cache_resource

def get_connection():

    return pymssql.connect(

        server=st.secrets["DB_SERVER"],

        user=st.secrets["DB_USER"],

        password=st.secrets["DB_PASSWORD"],

        database=st.secrets["DB_DATABASE"],

        login_timeout=10,

        timeout=120

    )
 
 
conn = get_connection()
 
 
# -------------------------

# DATE NORMALIZATION

# -------------------------

# D_Date_Report contains multiple text formats.

# Examples:

# 13-05-2025 00:00:00

# 3/10/2026 12:00:00 AM
 
DATE_EXPR = """

COALESCE(

    TRY_CONVERT(date, D_Date_Report, 105),

    TRY_CONVERT(date, D_Date_Report, 101),

    TRY_CONVERT(date, D_Date_Report)

)

"""
 
 
# -------------------------

# FILTER VALUES

# -------------------------
 
@st.cache_data(ttl=3600)

def get_divisions():

    query = """

    SELECT DISTINCT DivisionCode

    FROM dbo.DCRReport

    WHERE DivisionCode IS NOT NULL

      AND LTRIM(RTRIM(DivisionCode)) <> ''

    ORDER BY DivisionCode

    """
 
    return pd.read_sql(query, conn)["DivisionCode"].tolist()
 
 
@st.cache_data(ttl=3600)

def get_designations():
 
    query = """

    SELECT DISTINCT

        LEFT(

            C_FS_Code,

            PATINDEX('%[0-9]%', C_FS_Code + '0') - 1

        ) AS Designation

    FROM dbo.DCRReport

    WHERE C_FS_Code IS NOT NULL

    """
 
    df = pd.read_sql(query, conn)
 
    return sorted(

        df["Designation"]

        .dropna()

        .unique()

        .tolist()

    )
 
 
# -------------------------

# SIDEBAR FILTERS

# -------------------------
 
st.sidebar.header("Filters")
 
 
default_end = date.today()

default_start = default_end - timedelta(days=30)
 
 
date_range = st.sidebar.date_input(

    "Report Date",

    value=(default_start, default_end)

)
 
 
designations = get_designations()
 
selected_designation = st.sidebar.selectbox(

    "Designation",

    ["All"] + designations

)
 
 
divisions = get_divisions()
 
selected_division = st.sidebar.selectbox(

    "Division",

    ["All"] + divisions

)
 
 
hq_input = st.sidebar.text_input(

    "HQ Code",

    placeholder="Enter HQ code"

)
 
 
# -------------------------

# BUILD WHERE CLAUSE

# -------------------------
 
start_date = date_range[0]
 
if len(date_range) == 2:

    end_date = date_range[1]

else:

    end_date = start_date
 
 
where_conditions = [

    f"{DATE_EXPR} >= %s",

    f"{DATE_EXPR} <= %s"

]
 
params = [

    start_date,

    end_date

]
 
 
if selected_designation != "All":
 
    where_conditions.append(

        """

        LEFT(

            C_FS_Code,

            PATINDEX('%[0-9]%', C_FS_Code + '0') - 1

        ) = %s

        """

    )
 
    params.append(selected_designation)
 
 
if selected_division != "All":
 
    where_conditions.append(

        "DivisionCode = %s"

    )
 
    params.append(selected_division)
 
 
if hq_input.strip():
 
    where_conditions.append(

        "C_HQ_Code = %s"

    )
 
    params.append(hq_input.strip())
 
 
where_clause = " AND ".join(where_conditions)
 
 
# -------------------------

# KPI QUERY

# -------------------------
 
@st.cache_data(ttl=600)

def get_kpis(

    start_date,

    end_date,

    designation,

    division,

    hq

):
 
    conditions = [

        f"{DATE_EXPR} >= %s",

        f"{DATE_EXPR} <= %s"

    ]
 
    query_params = [

        start_date,

        end_date

    ]
 
 
    if designation != "All":
 
        conditions.append(

            """

            LEFT(

                C_FS_Code,

                PATINDEX('%[0-9]%', C_FS_Code + '0') - 1

            ) = %s

            """

        )
 
        query_params.append(designation)
 
 
    if division != "All":
 
        conditions.append(

            "DivisionCode = %s"

        )
 
        query_params.append(division)
 
 
    if hq:
 
        conditions.append(

            "C_HQ_Code = %s"

        )
 
        query_params.append(hq)
 
 
    filters = " AND ".join(conditions)
 
 
    query = f"""

    WITH FilteredDCR AS

    (

        SELECT

            C_FS_Code,

            C_DSC_Code,

            C_HQ_Code,

            ItemCode,

            {DATE_EXPR} AS ReportDate

        FROM dbo.DCRReport

        WHERE {filters}

    ),
 
    Contacts AS

    (

        SELECT DISTINCT

            C_FS_Code,

            C_DSC_Code,

            ReportDate

        FROM FilteredDCR

        WHERE C_FS_Code IS NOT NULL

          AND C_DSC_Code IS NOT NULL

          AND ReportDate IS NOT NULL

    )
 
    SELECT
 
        (

            SELECT COUNT(DISTINCT C_FS_Code)

            FROM FilteredDCR

            WHERE C_FS_Code IS NOT NULL

        ) AS ActiveEmployees,
 
        (

            SELECT COUNT(DISTINCT C_DSC_Code)

            FROM FilteredDCR

            WHERE C_DSC_Code IS NOT NULL

        ) AS UniqueDoctors,
 
        (

            SELECT COUNT(*)

            FROM Contacts

        ) AS DoctorDayContacts,
 
        (

            SELECT COUNT(DISTINCT C_HQ_Code)

            FROM FilteredDCR

            WHERE C_HQ_Code IS NOT NULL

        ) AS UniqueHQs,
 
        (

            SELECT COUNT(DISTINCT ItemCode)

            FROM FilteredDCR

            WHERE ItemCode IS NOT NULL

        ) AS UniqueProducts

    """
 
    return pd.read_sql(

        query,

        conn,

        params=query_params

    )
 
 
kpi = get_kpis(

    start_date,

    end_date,

    selected_designation,

    selected_division,

    hq_input.strip()

)
 
 
# -------------------------

# DISPLAY KPI CARDS

# -------------------------
 
active_employees = int(

    kpi["ActiveEmployees"].iloc[0] or 0

)
 
unique_doctors = int(

    kpi["UniqueDoctors"].iloc[0] or 0

)
 
contacts = int(

    kpi["DoctorDayContacts"].iloc[0] or 0

)
 
unique_hqs = int(

    kpi["UniqueHQs"].iloc[0] or 0

)
 
unique_products = int(

    kpi["UniqueProducts"].iloc[0] or 0

)
 
 
avg_contacts = (

    contacts / active_employees

    if active_employees > 0

    else 0

)
 
 
col1, col2, col3 = st.columns(3)
 
col1.metric(

    "Active Employees",

    f"{active_employees:,}"

)
 
col2.metric(

    "Unique Doctors",

    f"{unique_doctors:,}"

)
 
col3.metric(

    "Doctor-Day Contacts",

    f"{contacts:,}"

)
 
 
col4, col5, col6 = st.columns(3)
 
col4.metric(

    "Unique HQs",

    f"{unique_hqs:,}"

)
 
col5.metric(

    "Products Detailed",

    f"{unique_products:,}"

)
 
col6.metric(

    "Avg Contacts / Employee",

    f"{avg_contacts:,.1f}"

)
 
 
st.caption(

    "Doctor-Day Contact = unique Employee + Doctor + Report Date. "

    "This definition is temporary until N_Srno business logic is confirmed."

)
 
