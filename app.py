except Exception as error:

    st.error(
        "The DCR query could not be completed. "
        "Please try selecting a smaller period such as a month or quarter."
    )

    st.exception(error)

    st.stop()


try:

    with st.spinner("Loading Primary Sales KPIs..."):

        sales_kpis = get_sales_kpis(
            start_date=start_date,
            end_date=end_date,
            division_code=division_code
        )

except Exception as error:

    st.error(
        "The Primary Sales query could not be completed."
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
st.subheader("Primary Sales")

s1, s2, s3, s4 = st.columns(4)

with s1:
    st.metric(
        "Gross Sales",
        f"₹{float(sales_kpis['GrossSales'] or 0):,.2f}"
    )

with s2:
    st.metric(
        "Returns",
        f"₹{float(sales_kpis['ReturnsAmount'] or 0):,.2f}"
    )

with s3:
    st.metric(
        "Net Sales",
        f"₹{float(sales_kpis['NetSales'] or 0):,.2f}"
    )

with s4:
    st.metric(
        "Products Sold",
        f"{int(sales_kpis['ProductsSold'] or 0):,}"
    )


s5, s6, s7, s8 = st.columns(4)

with s5:
    st.metric(
        "Gross Quantity",
        f"{float(sales_kpis['GrossQty'] or 0):,.0f}"
    )

with s6:
    st.metric(
        "Return Quantity",
        f"{float(sales_kpis['ReturnQty'] or 0):,.0f}"
    )

with s7:
    st.metric(
        "Net Quantity",
        f"{float(sales_kpis['NetQty'] or 0):,.0f}"
    )

with s8:
    st.metric(
        "Sales Records",
        f"{int(sales_kpis['SalesRecords'] or 0):,}"
    )
