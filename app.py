import streamlit as st
import pandas as pd
from edgar_functions import get_same_sic_companies

# Load the data
df = pd.read_csv("Final_company_data.csv")

# Define the list of companies
companies_data = [
    {"Company": "Hershey Co.", "Ticker": "HSY", "Cik": "0000047111"},
    {"Company": "Walmart", "Ticker": "WMT", "Cik": "0000104169"},
    # Add other companies here
]


# Function to get or create session state
def get_session_state():
    if 'selected_similar_companies' not in st.session_state:
        st.session_state.selected_similar_companies = []


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

    # Get or create session state for checkboxes
    get_session_state()

    # Display similar companies as checkboxes
    st.write('Similar Companies:')
    for company in similar_companies:
        checkbox_value = st.checkbox(f"{company[2]} ({company[0]})", value=(
                    f"{company[2]} ({company[0]})" in st.session_state.selected_similar_companies))
        if checkbox_value:
            if f"{company[2]} ({company[0]})" not in st.session_state.selected_similar_companies:
                st.session_state.selected_similar_companies.append(f"{company[2]} ({company[0]})")
        elif f"{company[2]} ({company[0]})" in st.session_state.selected_similar_companies:
            st.session_state.selected_similar_companies.remove(f"{company[2]} ({company[0]})")

    # Back button
    if st.button("Back"):
        st.session_state.selected_similar_companies.clear()
        st.session_state.page = 1

    # Finalize Selection button
    if st.button("Finalize Selection"):
        st.session_state.page = 3

# Final Page
elif st.session_state.page == 3:
    st.title('Finalized Selection')

    # Display selected similar companies
    st.write('Selected Companies are:')
    for company in st.session_state.selected_similar_companies:
        st.write('- ' + company)

    # Back button
    if st.button("Back"):
        st.session_state.page = 2
