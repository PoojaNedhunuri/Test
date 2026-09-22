import streamlit as st

import pymssql

import pandas as pd
 
st.title("ASRA Database Read Test")
 
try:

    conn = pymssql.connect(

        server=st.secrets["DB_SERVER"],

        user=st.secrets["DB_USER"],

        password=st.secrets["DB_PASSWORD"],

        database=st.secrets["DB_DATABASE"],

        login_timeout=10,

        timeout=10

    )
 
    query = """

    SELECT TOP 10 *
    FROM dbo.DCRreport

    """
 
    df = pd.read_sql(query, conn)
 
    st.success("Database connection successful")

    st.dataframe(df)
 
    conn.close()
 
except Exception as e:

    st.error("Database connection failed")

    st.exception(e)
 
