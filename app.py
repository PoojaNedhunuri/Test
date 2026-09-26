
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
