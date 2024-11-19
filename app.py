import streamlit as st
from datetime import datetime
from supabase import create_client, Client
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Use wide layout
st.set_page_config(layout="wide",
                   page_title="HSMA Project Progress Reporter")

# Create a Google Sheets Connection
gs_conn = st.connection("gsheets", type=GSheetsConnection)

# Function to initialise a Supabase DB connection from details stored in secrets
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# Create Supabase DB connection
supabase = init_connection()

# Function to grab everything in the Supabase table pims_table
def run_query_main():
    return supabase.table("hsma_project_progress").select("*").execute()

hsma_proj_reg_df = gs_conn.read(ttl=60)

hsma_proj_reg_df = hsma_proj_reg_df.sort_values("Project Code")

hsma_proj_reg_df["Full Project Title"] = hsma_proj_reg_df["Project Code"].astype('str') + ": " + hsma_proj_reg_df["Project Title"]

st.dataframe(hsma_proj_reg_df)

# Title for app
st.title("Welcome to the HSMA Project Progress Tracker")

project_form_simple, project_form_structured = st.tabs(["Quick", "Structured"])

with project_form_simple:

    with st.form("project_progress_form_simple", clear_on_submit=True):
        st.write("""
                 Please enter a brief update about the progress made on your project
                 since the last time you reported back to us.

                 """)

        col_form_left, col_form_right = st.columns([0.5, 0.5])

        project_list = ["Please Select a Project"]
        project_list = project_list + hsma_proj_reg_df['Full Project Title'].tolist()

        new_area = st.selectbox(
                "What Project Does this Relate to?",
                project_list
            )

        with col_form_left:
            new_name = st.text_input(
                "What's your name?"
            )

        with col_form_right:
            update_date = st.date_input(
                "Please Enter the Date of the Update"
            )


        project_update = st.text_area("What is your update?")

        blurb_submitted = st.form_submit_button("Submit Update", disabled=True)

with project_form_structured:
    st.write("Coming Soon!")
