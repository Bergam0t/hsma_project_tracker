import streamlit as st
from datetime import datetime, timezone
from supabase import create_client
from streamlit_gsheets import GSheetsConnection
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
        print("==Not submitted - project not selected==")
    elif st.session_state.submitter_name == "":
        message = st.warning("Please enter your name before submitting")
        print("==Not submitted - name not entered==")
    elif st.session_state.project_update == "":
        message = st.warning("Please enter your update before submitting")
        print("==Not submitted - no update entered==")
    else:
        rows = run_query_main()

        with st.spinner("Submitting Log..."):

            entry_dict = {
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "project_code": int(st.session_state.project_code), # Ensure not passing as int64, which table will reject
                        "submitter": st.session_state.submitter_name,
                        "entry_type": "Simple Log",
                        "entry": st.session_state.project_update
                    }

            try:
                print(f"Attempting to write")
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
                while i<=30:
                    try:
                        print(f"Retry {i}")
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
                        sleep(0.5)
                else:
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

st.write("""*Choose between 'Quick' for a simple one-box project log template, or 'Structured' if you'd like some more guidance on what to include in your project update*
         \nYou only need to submit your log in one format - not both!
         """)

project_form_simple, project_form_structured = st.tabs(["Quick", "Structured"])

@st.fragment
def project_form_simple_f():
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

with project_form_simple:
    project_form_simple_f()

def run_structured_submit():
    # key_progress_log, key_meetings_log, additional_notes_log
    # challenges_log, key_planned_activities_log, other_comments_log
    print(f"Project Code: {st.session_state.project_code}")
    print(f"Submitter: {st.session_state.submitter_name}")

    if st.session_state.project_code is None:
        message = st.warning("Please select a project before submitting")
        print("==Not submitted - project not selected==")
    elif st.session_state.submitter_name == "":
        message = st.warning("Please enter your name before submitting")
        print("==Not submitted - name not entered==")
    elif (st.session_state.key_progress_log == "" and
          st.session_state.key_meetings_log == "" and
          st.session_state.challenges_log == "" and
          st.session_state.key_planned_activities_log == "" and
          st.session_state.other_comments_log == ""):
        message = st.warning("Please enter an update in at least one box before submitting")
        print("==Not submitted - no update entered==")
    else:
        rows = run_query_main()

        with st.spinner("Submitting Log..."):

            structured_log_dict = [
                {"entry_type": "Structured Log - Progress", "entry": st.session_state.key_progress_log},
                {"entry_type": "Structured Log - Meetings", "entry": st.session_state.key_meetings_log},
                {"entry_type": "Structured Log - Challenges", "entry": st.session_state.challenges_log},
                {"entry_type": "Structured Log - Planned Activities", "entry": st.session_state.key_planned_activities_log},
                {"entry_type": "Structured Log - Other Comments", "entry": st.session_state.other_comments_log},
            ]

            for box in structured_log_dict:
                entry_dict = {
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "project_code": int(st.session_state.project_code), # Ensure not passing as int64, which table will reject
                            "submitter": st.session_state.submitter_name,
                            "entry_type": box["entry_type"],
                            "entry": box["entry"]
                        }

                if box["entry"] != "":
                    try:
                        print(f"Attempting to write")
                        response = (
                            supabase.table("ProjectLogs").insert(entry_dict).execute()
                        )
                        if response.data:
                            print("Successfully written to ProjectLogs table on first try")
                            message = st.success(f"""
                                                Project Log Submitted Successfully!
                                                \n\n**Project**: {st.session_state.project_code}
                                                \n\n**Submitter**: {st.session_state.submitter_name}
                                                \n\n**Log**: {box["entry"]}
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
                                print(f"Retry {i}")
                                response = (
                                    supabase.table("ProjectLogs").insert(entry_dict).execute()
                                )
                                if response.data:
                                    print(f"Successfully written on retry {i}")
                                    message = st.success(f"""
                                                Project Log Submitted Successfully!
                                                \n\n**Project**: {st.session_state.project_code}
                                                \n\n**Submitter**: {st.session_state.submitter_name}
                                                \n\n**Log**: {box["entry"]}
                                                """)
                                    celebrate()
                                else:
                                    raise Exception(response.error.message)
                                break
                            except Exception as e:
                                error_message = str(e)
                                print(f"Error occurred: {error_message}")
                                i += 1
                                sleep(0.5)
                        else:
                            message = st.warning("Error Submitting Log - Please Contact Dan or Sammi on Slack")


@st.fragment
def project_form_structured_f():

    st.write("""Fill in as many of the boxes below as you would like, **then click the 'Submit' button at the bottom of the page**.
             \n\nOnly the 'Project Progress' field is mandatory; any other fields can be filled in or left blank as you wish.""")

    st.write("---")

    key_progress, bs1, key_meetings = st.columns([0.47,0.06,0.47])

    key_progress.write("#### Project Progress")
    with key_progress.expander("Click here for an example entry"):
        st.info(
        """
        - Main area of focus was continuing with exploratory data analysis and data quality assessment of available data.
        - Continued to develop understanding of urgent care system:
        - Visually explored care pathways and diagnostic history of frequent users of and packaged into reusable interactive HTML format that could be distributed (however, further polish would be required, plus IG considerations). This is effectively an R/Plotly implementation of the Theograph concept that could be further developed.
        - Additional reading of emergency department modelling literature; storing this in Zotero for reference during writeup.
        """
        )

    st.session_state.key_progress_log = key_progress.text_area(
        """**MANDATORY FIELD**
        \n\nPlease enter what progress you have made with your project since your last update""",
        height=250
    )

    key_meetings.write("#### Project-related Meetings")
    with key_meetings.expander("Click here for an example entry"):
        st.info(
        """
        - Afternoon in-person with head of operations to discuss work so far and explore additional areas of interest
        - Chat with Bob Bobson (HSMA 5 alumni) about experience working on a similar project last year - identified areas of potential code reuse
        """
        )
    st.session_state.key_meetings_log = key_meetings.text_area(
        """*OPTIONAL FIELD*
        \n\nProvide a brief overview of any meetings you have had with stakeholders or other parties since your last update
        """,
        height=250
    )

    st.write("---")

    st.subheader("Challenges and Next Steps")

    challenges, bs3, key_planned_activities, bs4, other_comments = st.columns([0.3,0.05,0.3,0.05,0.3])

    challenges.write("#### Challenges")
    with challenges.expander("Click here for an example entry"):
        st.info(
        """
        - Continued difficulty with access to relevant ICB dashboards due to licencing.
        - Large volume of ad-hoc requests have limited additional time available for project work
        - Short month due to bank holidays and one member of team on annual leave for 2 weeks
        """
        )
    st.session_state.challenges_log = challenges.text_area(
        """*OPTIONAL FIELD*
        \n\nWhat challenges have you faced in your project since your last update?
        \n\nDo you have any updates on previous challenges you have faced?
        \n\nIf you have any blockers that you need the HSMA team's input on, please contact us on Slack.
        """,
        height=250
    )

    key_planned_activities.write("#### Next Steps")
    with key_planned_activities.expander("Click here for an example entry"):
        st.info(
        """
        Activities:
        - Get all steps required to fully automate data flows complete.
        - Various tidying up and handover work.
        - Action any key feedback from stakeholders.

        Key meetings
        - Meeting with operational lead on 6th April to discuss training and implementation plans, plus post-implementation review and next steps
        - Presenting work in emergency care board meeting on 7th April
        """
        )
    st.session_state.key_planned_activities_log = key_planned_activities.text_area(
        """*OPTIONAL FIELD*
        \n\nWhat are you planning to do in the next month?
        \n\nWhat are your key next steps?
        \n\nAre there any meetings in the diary or that you are planning to arrange?
        """,
        height=250
    )

    other_comments.write("#### Any Other Comments")

    with other_comments.expander("Click here for an example entry"):
        st.info(
        """
        A request for a dashboard to support bed delivery meetings came in – a colleague was able to adapt my work to quickly provide all of the data required for these meetings.
        Feedback from this group has been positive.

        Two follow-up meetings regarding wider implementation and potential for dissemination of learning came out of the presentation to our expert panel, and the following feedback was received
        from an ICB colleague present at this presentation: "The project team have just blown everyone’s minds with how they have engaged with operational end-users in a complex area and developed a model that are what everyone didn’t know they needed and didn’t think was possible.
        Really helped showcase the potential of data and the need to invest in the capacity and capability of data science.”
        """
        )

    st.session_state.other_comments_log = other_comments.text_area(
    """*OPTIONAL FIELD*
    \n\nUse this space for any other comments that don't fit under any of the other headers
    """,
        height=250
    )

    submit_structured_project_log = st.button("Submit Update", key="submit_update_structured",
                                              type='primary', disabled=False,
                                              on_click=run_structured_submit)

    message


with project_form_structured:
    project_form_structured_f()
