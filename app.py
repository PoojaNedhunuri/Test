import streamlit as st
import pymssql

st.set_page_config(
    page_title="SQL Server Connection Test",
    layout="wide"
)

st.title("SQL Server Connection Test")

try:
    conn = pymssql.connect(
        server=st.secrets["DB_SERVER"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        login_timeout=30,
        timeout=60
    )

    cursor = conn.cursor()

    cursor.execute("SELECT 1")

    result = cursor.fetchone()

    st.success(
        f"SQL Server connected successfully: {result[0]}"
    )

    conn.close()

except Exception as e:
    st.error("SQL Server connection failed")
    st.exception(e)
