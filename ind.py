import streamlit as st
import pandas as pd
import json
import sys
import load
from st_tables import display_table_with_expandable_rows
import ast

# Get data from session state




# ADDED: Safety check at the top
if "company" not in st.session_state or "company_data" not in st.session_state:
    st.warning(" Please select a company first from the main page")
    st.info("Go to the main page to select a company")
    st.stop()
    
    
chosen_company = st.session_state["company"]
company = st.session_state["company_data"]

# Check if company loaded
if company is None:
    st.error("Failed to load company data")
    st.stop()

# Check if documents exist
if company.documents is None:
    st.error("Documents not available for single-year view")
    st.stop()

# Step 1: Select year (convert keys to sorted list)
available_years = sorted(company.documents.keys(), reverse=True)  # Most recent first
chosen_year_for_company = st.selectbox('Select year', available_years)

if not chosen_year_for_company:
    st.stop()

# Step 2: Get AWS document for selected year
aws_doc_for_year = company.documents[chosen_year_for_company]

# Step 3: Select statement
chosen_statement_for_doc = st.selectbox('Select statement', aws_doc_for_year.all_statements)

if not chosen_statement_for_doc:
    st.stop()


#  Display the statement
# if hasattr(aws_doc_for_year, chosen_statement_for_doc):
#     statement_df = getattr(aws_doc_for_year, chosen_statement_for_doc)
#     st.subheader(f"{chosen_statement_for_doc} - {chosen_year_for_company}")

#       # CONVERT PATH COLUMN FROM STRING TO LIST
#     if 'path' in statement_df.columns:
#         statement_df['path'] = statement_df['path'].apply(
#             lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() else []
#         )
    
    # display_table_with_expandable_rows(statement_df,'path',aws_doc_for_year.notes_tables)
    
if hasattr(aws_doc_for_year, chosen_statement_for_doc):
    statement_df = getattr(aws_doc_for_year, chosen_statement_for_doc)
    st.subheader(f"{chosen_statement_for_doc} - {chosen_year_for_company}")

    # Add download button for the statement
    csv = statement_df.to_csv(index=False)
    st.download_button(
        label=f" Download {chosen_statement_for_doc}",
        data=csv,
        file_name=f"{chosen_statement_for_doc}_{chosen_year_for_company}.csv",
        mime="text/csv",
        key=f"download_{chosen_statement_for_doc}_{chosen_year_for_company}"
    )

    # CONVERT PATH COLUMN FROM STRING TO LIST
    if 'path' in statement_df.columns:
        statement_df['path'] = statement_df['path'].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() else []
        )
    
    display_table_with_expandable_rows(statement_df, 'path', aws_doc_for_year.notes_tables)