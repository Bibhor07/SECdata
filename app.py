import streamlit as st
import pandas as pd
from edgar_functions import get_same_sic_companies, generate_main_df
import streamlit.components.v1 as components

# Load the data
df = pd.read_csv("Final_company_data.csv")

# Define the list of companies
companies_data = [
    {"Company": "Hershey Co.", "Ticker": "HSY", "Cik": "0000047111"},
    {"Company": "Walmart", "Ticker": "WMT", "Cik": "0000104169"},
    {"Company": "Paccar", "Ticker": "PCAR", "Cik": "0000075362"},
    {"Company": "Sysco Corp.", "Ticker": "SYY", "Cik": "0000096021"},
    {"Company": "Tesla", "Ticker": "TSLA", "Cik": "0001318605"},
    {"Company": "General Motors", "Ticker": "GM", "Cik": "0001467858"},
    {"Company": "Target Corp", "Ticker": "TGT", "Cik": "0000027419"},
    {"Company": "Kraft Inc.", "Ticker": "KHC", "Cik": "0001637459"},
    {"Company": "The Clorox Company", "Ticker": "CLX", "Cik": "0000021076"},
    {"Company": "Amazon Inc.", "Ticker": "AMZN", "Cik": "0001018724"},
    {"Company": "Nike Inc.", "Ticker": "NKE", "Cik": "0000320187"},
    {"Company": "Chipotle Mexican Grill Inc.", "Ticker": "CMG", "Cik": "0001058090"},
    {"Company": "McDonald's Inc", "Ticker": "MCD", "Cik": "0000063908"},
    {"Company": "Lululemon Athletics Inc. (LULU)", "Ticker": "LULU", "Cik": "0001397187"},
    {"Company": "Coca Cola", "Ticker": "KO", "Cik": "0000021344"},
    {"Company": "Molson Coors", "Ticker": "TAP", "Cik": "0000024545"}
]
# Function to get or create session state
def get_session_state():
    if 'selected_similar_companies' not in st.session_state:
        st.session_state.selected_similar_companies = set()

# First Page
if 'page' not in st.session_state:
    st.session_state.page = 1

if st.session_state.page == 1:
    st.title('Select a Company')

    # Selectbox for choosing a company
    selected_company_name = st.selectbox('Choose a company:', [company['Company'] for company in companies_data])

    # Number of fiscal years' data input
    num_fiscal_years = st.number_input('Number of fiscal years data:', min_value=1, step=1)

    # Number of similar companies input
    num_similar_companies = st.number_input('Number of similar companies:', min_value=1, step=1)

    # Next button
    if st.button("Next"):
        st.session_state.selected_company_name = selected_company_name
        st.session_state.num_fiscal_years = num_fiscal_years
        st.session_state.num_similar_companies = num_similar_companies
        st.session_state.page = 2

# Second Page
elif st.session_state.page == 2:
    st.title('Similar Companies')

    # Display selected input selections from the first page
    st.write('Selected Company:', st.session_state.selected_company_name)
    st.write('Number of fiscal years data:', st.session_state.num_fiscal_years)
    st.write('Number of similar companies:', st.session_state.num_similar_companies)

    # Call your function to get similar companies
    selected_company_cik = next(
        company['Cik'] for company in companies_data if company['Company'] == st.session_state.selected_company_name)
    similar_companies = get_same_sic_companies(df, cik=int(selected_company_cik),
                                               n_accessions=st.session_state.num_fiscal_years,
                                               n_companies=st.session_state.num_similar_companies)

    # Set similar companies in session state
    st.session_state.similar_companies = similar_companies

    # Set ticker of initially selected company
    st.session_state.initial_selected_company_ticker = next(
        company['Ticker'] for company in companies_data if company['Company'] == st.session_state.selected_company_name)

    # Get or create session state for selected similar companies
    get_session_state()

    # Display similar companies as checkboxes
    st.write('Similar Companies:')
    for company in similar_companies:
        checkbox_value = st.checkbox(f"{company[2]} ({company[0]})", value=(
                    f"{company[2]} ({company[0]})" in st.session_state.selected_similar_companies))
        if checkbox_value:
            st.session_state.selected_similar_companies.add(f"{company[2]} ({company[0]})")
        elif f"{company[2]} ({company[0]})" in st.session_state.selected_similar_companies:
            st.session_state.selected_similar_companies.remove(f"{company[2]} ({company[0]})")

    # Back button
    if st.button("Back"):
        st.session_state.page = 1

    # Finalize Selection button
    if st.button("Finalize Selection"):
        st.session_state.page = 3

# Final Page
elif st.session_state.page == 3:
    st.title('Finalized Selection')

    # Retrieve similar companies from session state
    similar_companies = st.session_state.similar_companies

    # Display selected similar companies
    st.write('Selected Companies are:')
    for company in st.session_state.selected_similar_companies:
        st.write('- ' + company)

    # Get the CIKs and tickers of all selected similar companies
    selected_ciks = []
    selected_tickers = []
    for company in similar_companies:
        if f"{company[2]} ({company[0]})" in st.session_state.selected_similar_companies:
            selected_ciks.append(company[1])
            selected_tickers.append(company[0])

    # Add CIK of initially selected company
    selected_company_cik = next(
        company['Cik'] for company in companies_data if company['Company'] == st.session_state.selected_company_name)
    selected_ciks.append(selected_company_cik)
    selected_tickers.append(st.session_state.initial_selected_company_ticker)

    # Print selected CIKs
    st.write('Selected CIKs are:')
    for cik in selected_ciks:
        st.write('- ' + cik)

    # Print selected tickers
    st.write('Selected Tickers are:')
    for ticker in selected_tickers:
        st.write('- ' + ticker)

    # Store fys and selected_tickers in session state
    st.session_state.fys = [2023 - i for i in range(st.session_state.num_fiscal_years)]
    st.session_state.selected_tickers = selected_tickers

    # Create a list of fiscal years
    fys = st.session_state.fys

    # Display the list of fiscal years
    st.write('Fiscal Years:', fys)

    # Next button
    if st.button("Next"):
        st.session_state.page = 4

# Get Data Page
elif st.session_state.page == 4:
    st.title('Get Data')

    # Button to get data
    if st.button("Get Data"):
        # Get the data
        main_df = generate_main_df(st.session_state.fys, st.session_state.selected_tickers)

        # Display the data as a Streamlit DataFrame
        st.write(main_df)

        # Print message indicating data is ready
        st.write("Your data is ready to download.")


    # Back button
    if st.button("Back"):
        st.session_state.page = 3


