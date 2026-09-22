import streamlit as st
import pymssql
import pandas as pd 

st.title("ASRA Database Connection Test")
 
try:
 conn = pymssql.connect(
        server=st.secrets["DB_SERVER"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_DATABASE"],
        login_timeout=10,
        timeout=10
    )
 
    cursor = conn.cursor()

    cursor.execute("SELECT 1")
 
    result = cursor.fetchone()
 
    st.success("Database connection successful")

 
except Exception as e:

    st.error("Database connection failed")

    st.exception(e)
 
