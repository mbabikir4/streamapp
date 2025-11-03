import streamlit as st
import pandas as pd
import json
import sys
from load_s3 import get_available_tickers,load_single_company

import os 
os.environ['AWS_ACCESS_KEY_ID'] = st.secrets['AWS_ACCESS_KEY_ID']
os.environ['AWS_SECRET_ACCESS_KEY'] = st.secrets['AWS_SECRET_ACCESS_KEY']
os.environ['AWS_DEFAULT_REGION'] = st.secrets['AWS_DEFAULT_REGION']


st.set_page_config(layout="wide")
st.header('Companies Info')


s3_path = 's3://project-z-test-stream/company-data'

# Step 1: Get available tickers
all_tickers = get_available_tickers()

# Step 2: Select company (wait for user selection)
chosen_company = st.selectbox('Select a company', all_tickers)

# Stop here if no company is selected
if not chosen_company:
    st.stop()


# Step 3: load_s3 company data (only runs if company is selected)
company = load_single_company(chosen_company, s3_path)

if chosen_company:
    st.session_state["company"] = chosen_company
    st.session_state["company_data"] = company

# Stop here if company failed to load
if company is None:
    st.error("Failed to load company data")
    st.stop()
    
# Step 4: Select statement (only runs if company is loaded)
chosen_statement_for_company = st.selectbox('Select merged statement', company.all_statements)

# Stop here if no statement is selected
if not chosen_statement_for_company:
    st.stop()

# Step 5: Display dataframe (only runs if statement is selected)
if hasattr(company, chosen_statement_for_company):
    statement_df = getattr(company, chosen_statement_for_company)
    st.dataframe(statement_df, width='stretch', height=600)
else:
    st.warning(f"Statement {chosen_statement_for_company} not available")


