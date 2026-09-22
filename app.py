import streamlit as st

import pyodbc
import pandas as pd 
st.title("ASRA Database Connection Test")
 
try:

    conn = pyodbc.connect(

        "DRIVER={ODBC Driver 18 for SQL Server};"

        f"SERVER={st.secrets['DB_SERVER']};"

        f"DATABASE={st.secrets['DB_DATABASE']};"

        f"UID={st.secrets['DB_USER']};"

        f"PWD={st.secrets['DB_PASSWORD']};"

        "Encrypt=yes;"

        "TrustServerCertificate=yes;",

        timeout=10

    )
 
    cursor = conn.cursor()

    cursor.execute("SELECT 1")
 
    result = cursor.fetchone()
 
    st.success("Database connection successful")

    st.write(result)
    query = """
    SELECT TOP 10 *
    FROM dbo.DCRreport
    """
    
    df = pd.read_sql(query, conn)
    
    st.dataframe(df)
 
except Exception as e:

    st.error("Database connection failed")

    st.exception(e)
 