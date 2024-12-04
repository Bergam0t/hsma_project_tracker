import streamlit as st
from datetime import datetime, timezone
from supabase import create_client, Client
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from time import sleep

# Use wide layout
st.set_page_config(layout="wide",
                   page_title="HSMA Project Progress Reporter")

with open("style.css") as css:
    st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)

# Create a Google Sheets Connection
gs_conn = st.connection("gsheets", type=GSheetsConnection)

# Function to initialise a Supabase DB connection from details stored in secrets
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# Create Supabase DB connection
supabase = init_connection()

# Function to grab everything in the Supabase table
def run_query_main():
    return supabase.table("ProjectLogs").select("*").execute()

hsma_proj_reg_df = gs_conn.read(ttl=60)

hsma_proj_reg_df = hsma_proj_reg_df.sort_values("Project Code")

hsma_proj_reg_df["Full Project Title"] = hsma_proj_reg_df["Project Code"].astype('str') + ": " + hsma_proj_reg_df["Project Title"]
hsma_proj_reg_df["Full Project Title and Leads"] = hsma_proj_reg_df["Full Project Title"] + " (" + hsma_proj_reg_df["Lead"] + ")"

project_list = ["Please Select a Project"]
project_list =  project_list + hsma_proj_reg_df['Full Project Title and Leads'].tolist()

# st.dataframe(hsma_proj_reg_df)

message = ""

# Title for app
st.title("Welcome to the HSMA Project Progress Tracker")

def celebrate():
    if datetime.now().month == 12:
        st.snow()
    else:
        st.balloons()

def run_simple_submit():
    print(f"Project Code: {st.session_state.project_code}")
    print(f"Submitter: {st.session_state.submitter_name}")
    print(f"Update: {st.session_state.project_update}")
    if st.session_state.project_code is None:
        message = st.warning("Please select a project before submitting")
    elif st.session_state.submitter_name == "":
        message = st.warning("Please enter your name before submitting")
    elif st.session_state.project_update == "":
        message = st.warning("Please enter your update before submitting")
    else:
        rows = run_query_main()

        with st.spinner("Submitting Log..."):

            id_of_latest_entry = rows.data[(len(rows.data) - 1)]['id']
            id_for_entry = id_of_latest_entry + 1
            print(f"ID of latest entry: {id_of_latest_entry}")

            entry_dict = {
                        "id":id_for_entry,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "project_code": int(st.session_state.project_code), # Ensure not passing as int64, which table will reject
                        "submitter": st.session_state.submitter_name,
                        "entry_type": "Simple Log",
                        "entry": st.session_state.project_update
                    }

            try:
                print(f"Attempting to write as entry {id_for_entry}")
                response = (
                    supabase.table("ProjectLogs").insert(entry_dict).execute()
                )
                if response.data:
                    print("Successfully written to ProjectLogs table on first try")
                    message = st.success(f"""
                                         Project Log Submitted Successfully!
                                         \n\n**Project**: {st.session_state.project_code}
                                         \n\n**Submitter**: {st.session_state.submitter_name}
                                         \n\n**Log**: {st.session_state.project_update}
                                         """)
                    celebrate()
                else:
                    raise Exception(response.error.message)
            except Exception as e:
                error_message = str(e)
                print(f"Error occurred: {error_message}")
                # print("Error encountered while trying to write to ProjectLogs table.")
                print("Trying again...")
                i = 1
                while i<=10:
                    try:
                        entry_dict['id'] += 1
                        print(f"Retrying with id {entry_dict['id']} - retry {i}")
                        response = (
                            supabase.table("ProjectLogs").insert(entry_dict).execute()
                        )
                        if response.data:
                            print(f"Successfully written on retry {i}")
                            message = st.success(f"""
                                         Project Log Submitted Successfully!
                                         \n\n**Project**: {st.session_state.project_code}
                                         \n\n**Submitter**: {st.session_state.submitter_name}
                                         \n\n**Log**: {st.session_state.project_update}
                                         """)
                            celebrate()
                        else:
                            raise Exception(response.error.message)
                        break
                    except Exception as e:
                        error_message = str(e)
                        print(f"Error occurred: {error_message}")
                        i += 1
                        sleep(2)
                message = st.warning("Error Submitting Log - Please Contact Dan or Sammi on Slack")

st.session_state.project = st.selectbox(
            """**What Project Does this Relate to?**
            \n\nStart typing a project code, title or team member to filter the project list, or scroll down to find your project.
            """,
            project_list,
            help="Note that only projects that have been registered via the 'new project airlock' channel on Slack will appear in this list."
        )

if st.session_state.project != "Please Select a Project":
    st.session_state.project_code = hsma_proj_reg_df[hsma_proj_reg_df['Full Project Title and Leads'] == st.session_state.project]['Project Code'].values[0]
else:
    st.session_state.project_code = None

st.session_state.submitter_name = st.text_input(
            "**What's your name?**\n\n*Please include your first name and surname*"
        )

project_form_simple, project_form_structured = st.tabs(["Quick", "Structured"])

with project_form_simple:

    col_form_left, col_form_right = st.columns([0.7, 0.3])

    with col_form_right:

        st.write("*Example Updates*")

        example_update_1, example_update_2, example_update_3 = st.tabs(["Example 1", "Example 2", "Example 3"])

        example_update_1.info(
        """
            This month we have been focussing on developing our understanding of the ED and engaging with key stakeholders.

            We have started to arrange an expert panel of ED staff to gather insights on workflow, patient flow patterns, and resource allocation challenges.

            We have also started pulling out historical arrival patterns and conducting some exploratory data analysis to see how different patient groups differ and if there are data quality issues.

            In the next month, we will be focussing on first version of a conceptual model of the ED for review by the expert panel.
            We'll also finish conducting our EDA and produce a first suggested list of patient groups that may require different activity time or arrival time distributions.
            """)
        example_update_2.info(
            """
            Due to sickness in the project team this month, we have been unable to progress the project as planned.

            We have rescheduled the planned meeting to show our model to the stakeholders to next month.

            Currently we are having trouble gaining agreement to publish our code on GitHub.
            """
                        )
        example_update_3.info("""
            Most of my project time this month has been spent exploring the literature and other sources like Github to see if anyone else has done work in this area.
            I haven't found any code I can adapt, but I did find an interesting paper on non-attendance prediction by Mark et al (2019) where they achieved an AUC of 0.79.

            I'm currently blocked by waiting for data access so will continue to explore the literature and write some template code.

                        """
                        )

    with col_form_left:
        # pass
        # update_date = st.date_input(
        #     "Please Enter the Date of the Update"
        # )

        st.session_state.project_update = st.text_area("""**What is your update?**
                                        \n\nThis can be a couple of sentences or a couple of paragraphs - whatever is useful to you!
                                        \n\nWe'd recommend you keep your own copy of this update for your records.
                                        """,
                                        height=400)

        submit_simple_project_log = st.button("Submit Update", type='primary', disabled=False,
                                                on_click=run_simple_submit)

        message


with project_form_structured:
    st.write("Coming Soon!")
