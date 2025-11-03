import streamlit as st
import pandas as pd
import json
import sys
import load
# company_dict = pickle.load( open("../ipynb/company_dict.pkl", "rb" ))


pg = st.navigation([
    st.Page("index_gpt.py", title="Main"),
    st.Page('ind.py', title="More details",),
])
pg.run()

