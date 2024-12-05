import streamlit as st
from datetime import datetime, timezone
import pandas as pd
from supabase import create_client
from streamlit_gsheets import GSheetsConnection
from time import sleep
import pyperclip

# Use wide layout
st.set_page_config(layout="wide",
                   page_icon="hsma_icon.png",
                   page_title="HSMA Project Progress Reporter")

# Import stylesheet for font and page margin setting
with open("style.css") as css:
    st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)

# Initialise session state variables
if 'existing_projects' not in st.session_state:
    st.session_state.existing_projects = pd.DataFrame()
if 'project_updates' not in st.session_state:
    st.session_state.project_updates = None
if 'project' not in st.session_state:
    st.session_state.project = None

st.session_state.message = {'type': "none", 'message': ''}

# Create a Google Sheets Connection
@st.cache_resource
def get_gs_connection():
    return st.connection("gsheets", type=GSheetsConnection)

gs_conn = get_gs_connection()

# Function to initialise a Supabase DB connection from details stored in secrets
@st.cache_resource
def init_supabase_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# Create Supabase DB connection
supabase = init_supabase_connection()

# Function to grab everything from the HSMA project register spreadsheet
@st.cache_data(ttl=60)
def get_proj_register_df():
    hsma_proj_reg_df = gs_conn.read()
    hsma_proj_reg_df = hsma_proj_reg_df.sort_values("Project Code")
    hsma_proj_reg_df["Full Project Title"] = hsma_proj_reg_df["Project Code"].astype('str') + ": " + hsma_proj_reg_df["Project Title"]
    hsma_proj_reg_df["Full Project Title and Leads"] = hsma_proj_reg_df["Full Project Title"] + " (" + hsma_proj_reg_df["Lead"] + ")"
    return hsma_proj_reg_df

# Function to grab everything in the Supabase table of project logs
def run_query_main():
    return supabase.table("ProjectLogs").select("*").execute()

# Set up entries for project list dropdown
hsma_proj_reg_df = get_proj_register_df()
project_list = ["Please Select a Project"]
project_list =  project_list + hsma_proj_reg_df['Full Project Title and Leads'].tolist()

def celebrate():
    if datetime.now().month == 12:
        st.snow()
    else:
        st.balloons()

def update_message():
    if st.session_state.message['type'] == 'success':
        st.success(st.session_state.message["text"])
    elif st.session_state.message['type'] == 'warning':
        st.warning(st.session_state.message["text"])

# Set up header with title and logo
header_col_l, header_col_r = st.columns([0.7, 0.3], vertical_alignment="center")

with header_col_r:
    st.image("hsma_logo_wide_white.png", width=300)

with header_col_l:
    # Title for app
    st.title("The HSMA Project Progress Tracker")

# Set up entry for project code
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

def get_projects_df():
    st.session_state.existing_projects = pd.DataFrame(run_query_main().data)
    st.session_state.existing_projects = st.session_state.existing_projects[["created_at", "project_code", "submitter"]]
    st.session_state.existing_projects["display_date"] = pd.to_datetime(st.session_state.existing_projects["created_at"]).dt.strftime("%A, %B %d %Y at %H:%M")
    st.session_state.project_updates = st.session_state.existing_projects[st.session_state.existing_projects["project_code"] == st.session_state.project_code].sort_values("display_date", ascending=False)

get_projects_df()

def refresh_status():
    get_projects_df()

col_update_status_1, col_update_status_2 = st.columns([0.6,0.4])

with col_update_status_1:
    if st.session_state.project_code is None:
        st.write("") # Blank line to try and avoid layout changing after project section
    elif len(st.session_state.project_updates) > 0:
        st.write(f"""This project last had an update recorded
                on {st.session_state.project_updates.head(1)['display_date'].values[0]}
                by {st.session_state.project_updates.head(1)['submitter'].values[0]}""")
        st.write("*:grey[If you have just submitted a project update, this information will not be up to date! Hit the refresh button.]*")
    else:
        st.write("No project updates have been provided for this project yet.")
        st.write("*:grey[If you have just submitted a project update, this information will not be up to date! Hit the refresh button.]*")

if st.session_state.project_code is not None:
    with col_update_status_2:
        st.button("Refresh last updated date", icon=":material/autorenew:", on_click=refresh_status())


st.write("---")

st.session_state.submitter_name = st.text_input(
            "**What's your name?**\n\n*Please include your first name and surname*"
        )

st.write("---")
st.subheader("Submit your Progress Report")

col_a, col_b, col_c = st.columns([0.6,0.2,0.2])

col_a.write("""*Choose between 'Quick' for a simple one-box project log template, or 'Structured' if you'd like some more guidance on what to include in your project update*
         \nYou only need to submit your log in one format - not both!
         """)

def clear_textboxes():
    st.session_state.simple_update = ""
    st.session_state.structured_progress = ""
    st.session_state.structured_meetings = ""
    st.session_state.structured_challenges = ""
    st.session_state.structured_plans = ""
    st.session_state.structured_other = ""

col_c.button("Clear All Text Boxes", icon=":material/delete:" ,
            on_click=clear_textboxes,
            help="""If you are submitting logs for multiple projects,
            use this button to clear the fields between projects""",
            type="primary")

project_form_simple, project_form_structured = st.tabs(["Quick", "Structured"])

def run_simple_submit():
    print(f"Project Code: {st.session_state.project_code}")
    print(f"Submitter: {st.session_state.submitter_name}")
    print(f"Update: {st.session_state.project_update}")
    if st.session_state.project_code is None:
        st.session_state.message = {
                "type": "warning",
                "text": "Please select a project before submitting"
                }
        print("==Not submitted - project not selected==")
    elif st.session_state.submitter_name == "":
        st.session_state.message = {
                        "type": "warning",
                        "text": "Please enter your name before submitting"
                        }
        print("==Not submitted - name not entered==")
    elif st.session_state.project_update == "":
        st.session_state.message = {
                        "type": "warning",
                        "text": "Please enter your update before submitting"
                        }
        print("==Not submitted - no update entered==")
    else:
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
                    st.session_state.message = {
                                "type": "success",
                                "text": f"""
                                         Project Log Submitted Successfully!
                                         \n\n**Project**: {st.session_state.project_code}
                                         \n\n**Submitter**: {st.session_state.submitter_name}
                                         \n\n**Log**: {st.session_state.project_update}
                                         """
                                }
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
                            st.session_state.message = {
                                "type": "success",
                                "text": f"""
                                         Project Log Submitted Successfully!
                                         \n\n**Project**: {st.session_state.project_code}
                                         \n\n**Submitter**: {st.session_state.submitter_name}
                                         \n\n**Log**: {st.session_state.project_update}
                                         """
                                }

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
                    st.session_state.message = {
                        "type": "warning",
                        "text": "Error Submitting Log - Please Contact Dan or Sammi on Slack"
                        }
    get_projects_df()


@st.fragment
def project_form_simple_f():
    col_form_left, col_form_right = st.columns([0.7, 0.3])

    with col_form_right:

        st.subheader("Example Updates")

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

        st.session_state.project_update = st.text_area("""**What is your update?**
                                        \n\nThis can be a couple of sentences or a couple of paragraphs - whatever is useful to you!
                                        \n\nWe'd recommend you keep your own copy of this update for your records.
                                        """,
                                        key="simple_update",
                                        height=400)

        def copy_simple_update_to_clipboard_as_md():

            simple_log_md = f"""## Project: {st.session_state.project}

Date: {datetime.now().strftime("%A, %B %d %Y at %H:%M")}

Submitted by {st.session_state.submitter_name}

### Project Progress

{st.session_state.simple_update}

            """

            pyperclip.copy(simple_log_md)
            st.toast("Copied Update To Your Clipboard", icon=":material/thumb_up:")

        def copy_simple_update_to_clipboard_as_pt():

            simple_log_md = f"""Project: {st.session_state.project}

Date: {datetime.now().strftime("%A, %B %d %Y at %H:%M")}

Submitted by {st.session_state.submitter_name}

Project Progress: {st.session_state.simple_update}
            """

            pyperclip.copy(simple_log_md)
            st.toast("Copied Update To Your Clipboard", icon=":material/thumb_up:")

        submit_col_1a, submit_col_2a, submit_col_3a = st.columns(3)

        submit_simple_project_log = submit_col_1a.button("Submit Update", type='primary', disabled=False,
                                                on_click=run_simple_submit, icon=":material/send:",
                                                use_container_width=True)

        submit_col_2a.button("Copy Update to Clipboard as Markdown",
                            on_click=copy_simple_update_to_clipboard_as_md,
                            key="copy_simple_md",
                            icon=":material/content_copy:",
                            use_container_width=True)

        submit_col_3a.button("Copy Update to Clipboard as Plain Text",
                                    on_click=copy_simple_update_to_clipboard_as_pt,
                                    icon=":material/content_copy:",
                                    key="copy_simple_pt",
                                    use_container_width=True)


        with st.empty():
            update_message()



with project_form_simple:
    project_form_simple_f()

def run_structured_submit():
    # key_progress_log, key_meetings_log, additional_notes_log
    # challenges_log, key_planned_activities_log, other_comments_log
    print(f"Project Code: {st.session_state.project_code}")
    print(f"Submitter: {st.session_state.submitter_name}")

    if st.session_state.project_code is None:
        st.session_state.message = {
                "type": "warning",
                "text": "Please select a project before submitting"
                }
        print("==Not submitted - project not selected==")
    elif st.session_state.submitter_name == "":
        st.session_state.message = {
                        "type": "warning",
                        "text": "Please enter your name before submitting"
                        }
        print("==Not submitted - name not entered==")
    elif (st.session_state.key_progress_log == ""):
        st.session_state.message = {
                        "type": "warning",
                        "text": "Please enter an update in at least the 'Project Progress' box before submitting"
                        }
        print("==Not submitted - no update entered==")
    else:
        with st.spinner("Submitting Log..."):

            structured_log_dict = [
                {"entry_type": "Structured Log - Progress", "entry": st.session_state.key_progress_log},
                {"entry_type": "Structured Log - Meetings", "entry": st.session_state.key_meetings_log},
                {"entry_type": "Structured Log - Challenges", "entry": st.session_state.challenges_log},
                {"entry_type": "Structured Log - Planned Activities", "entry": st.session_state.key_planned_activities_log},
                {"entry_type": "Structured Log - Other Comments", "entry": st.session_state.other_comments_log},
            ]

            for instance, box in enumerate(structured_log_dict):
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
                            if instance == 0:
                                st.session_state.message = {
                                    "type": "success",
                                    "text": f"""
                                            Project Log Submitted Successfully!
                                            \n\n**Project**: {st.session_state.project_code}
                                            \n\n**Submitter**: {st.session_state.submitter_name}
                                            \n\n**{box["entry_type"]}**: {box["entry"]}
                                            """
                                    }
                            else:
                                st.session_state.message["text"] += f"""\n\n**{box["entry_type"]}**: {box["entry"]}"""
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
                                    if instance == 0:
                                        st.session_state.message = {
                                    "type": "success",
                                    "text": f"""
                                            Project Log Submitted Successfully!
                                            \n\n**Project**: {st.session_state.project_code}
                                            \n\n**Submitter**: {st.session_state.submitter_name}
                                            \n\n**{box["entry_type"]}**: {box["entry"]}
                                            """
                                    }
                                    else:
                                        st.session_state.message["text"] += f"""\n\n**{box["entry_type"]}**: {box["entry"]}"""
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
                            st.session_state.message = {
                        "type": "warning",
                        "text": "Error Submitting Log - Please Contact Dan or Sammi on Slack"
                        }

    get_projects_df()


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
        - Continued to develop understanding of urgent care system.
        - Visually explored care pathways and diagnostic history of frequent users of and packaged into reusable interactive HTML format that could be distributed (however, further polish would be required, plus IG considerations). This is effectively an R/Plotly implementation of the Theograph concept that could be further developed.
        - Additional reading of emergency department modelling literature; storing this in Zotero for reference during writeup.
        """
        )

    st.session_state.key_progress_log = key_progress.text_area(
        """**MANDATORY FIELD**
        \n\nPlease enter what progress you have made with your project since your last update""",
        height=250,
        key="structured_progress"
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
        height=250,
        key="structured_meetings"
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
        - We're getting good engagement in general, but there's been some misunderstandings about the simplifications in the model that needs to be addressed
        """
        )
    st.session_state.challenges_log = challenges.text_area(
        """*OPTIONAL FIELD*
        \n\n• What challenges have you faced in your project since your last update?
        \n\n• Do you have any updates on previous challenges you have faced?
        \n\n:red[If you have any blockers that you need the HSMA team's input on, please contact us on Slack.]
        """,
        height=250,
        key="structured_challenges"
    )

    key_planned_activities.write("#### Next Steps")
    with key_planned_activities.expander("Click here for an example entry"):
        st.info(
        """
        Activities:
        - Get all steps required to fully automate data flows complete.
        - Add in additional sliders to model to allow for manual tweaking of demand forecasts.

        Key meetings
        - Meeting with operational lead on 6th April to discuss training and implementation plans, plus post-implementation review and next steps
        - Presenting work in emergency care board meeting on 7th April
        """
        )
    st.session_state.key_planned_activities_log = key_planned_activities.text_area(
        """*OPTIONAL FIELD*
        \n\n• What are you planning to do in the next month?
        \n\n• What are your key next steps?
        \n\n• Are there any meetings in the diary or that you are planning to arrange?
        """,
        height=250,
        key="structured_plans"
    )

    other_comments.write("#### Other Comments")

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
        height=250,
        key="structured_other"
    )

    def copy_structured_update_to_clipboard_as_md():

        structured_log_md = f"""## Project: {st.session_state.project}

Date: {datetime.now().strftime("%A, %B %d %Y at %H:%M")}

Submitted by {st.session_state.submitter_name}

### Project Progress

{st.session_state.structured_progress}

        """

        if st.session_state.structured_meetings:
            structured_log_md += f"""
### Project-related Meetings

{st.session_state.structured_meetings}
            """

        if st.session_state.structured_challenges:
            structured_log_md += f"""
### Challenges

{st.session_state.structured_challenges}
            """
        if st.session_state.structured_plans:
            structured_log_md += f"""
### Next Steps

{st.session_state.structured_plans}
            """

        if st.session_state.structured_other:
            structured_log_md += f"""
### Other Comments

{st.session_state.structured_other}
            """

        pyperclip.copy(structured_log_md)
        st.toast("Copied Update To Your Clipboard", icon=":material/thumb_up:")

    def copy_structured_update_to_clipboard_as_pt():

        structured_log_md = f"""Project: {st.session_state.project}

Date: {datetime.now().strftime("%A, %B %d %Y at %H:%M")}

Submitted by {st.session_state.submitter_name}
        """

        structured_log_md += f"\nProject Progress: {st.session_state.structured_progress}"

        if st.session_state.structured_meetings:
            structured_log_md += f"\n\nProject-related Meetings: {st.session_state.structured_meetings}"

        if st.session_state.structured_challenges:
            structured_log_md += f"\n\nChallenges: {st.session_state.structured_challenges}"

        if st.session_state.structured_plans:
            structured_log_md += f"\n\nNext Steps: {st.session_state.structured_plans}"

        if st.session_state.structured_other:
            structured_log_md += f"\n\nOther Comments: {st.session_state.structured_other}"

        pyperclip.copy(structured_log_md)
        st.toast("Copied Update To Your Clipboard", icon=":material/thumb_up:")

    st.write("---")

    submit_col_1, submit_col_2, submit_col_3 = st.columns(3)

    submit_structured_project_log = submit_col_1.button("Submit Update",
                                                        key="submit_update_structured",
                                                        type='primary',
                                                        disabled=False,
                                                        on_click=run_structured_submit,
                                                        icon=":material/send:",
                                                        use_container_width=True)

    copy_structured_log = submit_col_2.button("Copy Update to Clipboard as Markdown",
                                    on_click=copy_structured_update_to_clipboard_as_md,
                                    icon=":material/content_copy:",
                                    use_container_width=True)

    copy_structured_log = submit_col_3.button("Copy Update to Clipboard as Plain Text",
                                on_click=copy_structured_update_to_clipboard_as_pt,
                                icon=":material/content_copy:",
                                use_container_width=True)

    with st.empty():
        update_message()

with project_form_structured:
    project_form_structured_f()
