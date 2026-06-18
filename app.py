import re
import uuid
from datetime import datetime
from io import BytesIO

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Assessment Feedback Generator", page_icon="📝", layout="wide")

DEFAULT_COLUMNS = [
    "Assessment ID", "Saved At", "Candidate", "Personal", "Interviewer", "Date and time", "Remarks",
    "Device & Internet Setup (10%)", "Appearance & Background (10%)", "Energy & Confidence (10%)",
    "Communication Skills (15%)", "Introduction Pitch (10%)", "Technical Knowledge (20%)",
    "Behavioral Responses (10%)", "Resume & Project Knowledge (10%)", "Professional Etiquette (5%)",
    "Overall Market Readiness (5%)", "Total Score", "Feedback", "Generated Feedback"
]

INPUT_COLUMNS = [c for c in DEFAULT_COLUMNS if c not in ["Assessment ID", "Saved At", "Generated Feedback"]]

SCORE_COLUMNS = [
    "Device & Internet Setup (10%)", "Appearance & Background (10%)", "Energy & Confidence (10%)",
    "Communication Skills (15%)", "Introduction Pitch (10%)", "Technical Knowledge (20%)",
    "Behavioral Responses (10%)", "Resume & Project Knowledge (10%)", "Professional Etiquette (5%)",
    "Overall Market Readiness (5%)"
]

MAX_SCORE = {
    "Device & Internet Setup (10%)": 10,
    "Appearance & Background (10%)": 10,
    "Energy & Confidence (10%)": 10,
    "Communication Skills (15%)": 15,
    "Introduction Pitch (10%)": 10,
    "Technical Knowledge (20%)": 20,
    "Behavioral Responses (10%)": 10,
    "Resume & Project Knowledge (10%)": 10,
    "Professional Etiquette (5%)": 5,
    "Overall Market Readiness (5%)": 5,
}


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def candidate_name(raw):
    text = clean_text(raw)
    return re.sub(r"\s*\([^)]*\)\s*", "", text).strip() or "Candidate"


def candidate_domain(raw):
    text = clean_text(raw)
    match = re.search(r"\(([^)]*)\)", text)
    return match.group(1).upper().strip() if match else ""


def readiness_label(score):
    try:
        score = float(score)
    except Exception:
        return "Pending Review"
    if score >= 85:
        return "Ready for Marketing"
    if score >= 70:
        return "Conditionally Ready for Marketing"
    return "Not Ready for Marketing"


def score_value(row, col):
    try:
        return float(row.get(col, 0) or 0)
    except Exception:
        return 0.0


def strengths_and_improvements(row):
    strengths = []
    improvements = []

    checks = [
        ("Device & Internet Setup (10%)", "Strong device and internet setup", "Ensure device, camera, audio, and internet are fully stable before every interview."),
        ("Appearance & Background (10%)", "Professional appearance and acceptable interview background", "Improve the interview background. Use a clean/plain background or blur, not a distracting virtual background."),
        ("Energy & Confidence (10%)", "Good energy and confidence throughout the session", "Increase energy and confidence; low energy makes even correct answers sound weak."),
        ("Communication Skills (15%)", "Clear communication and professional speaking style", "Improve communication by keeping answers direct, structured, and relevant to the question."),
        ("Introduction Pitch (10%)", "Well-structured Introduction Pitch", "Strengthen the Introduction Pitch so it clearly sells experience, skills, tools, and target role."),
        ("Technical Knowledge (20%)", "Strong Technical Knowledge and ability to explain concepts", "Strengthen technical fundamentals and practice explaining concepts with examples from project work."),
        ("Behavioral Responses (10%)", "Good behavioral response quality", "Practice behavioral questions using the STAR method with real examples and measurable outcomes."),
        ("Resume & Project Knowledge (10%)", "Strong understanding of resume, projects, and responsibilities", "Review resume and project details carefully so every claim can be explained confidently."),
        ("Professional Etiquette (5%)", "Professional Etiquette during the assessment", "Improve Professional Etiquette, especially scheduling discipline, punctuality, and interview commitment."),
    ]

    for col, good, bad in checks:
        max_v = MAX_SCORE.get(col, 10)
        val = score_value(row, col)
        ratio = val / max_v if max_v else 0
        if ratio >= 0.80:
            strengths.append(good)
        elif ratio < 0.70:
            improvements.append(bad)

    feedback_raw = clean_text(row.get("Feedback", "")) + " " + clean_text(row.get("Remarks", ""))
    lower = feedback_raw.lower()
    if "virtual background" in lower:
        improvements.append("Avoid using a virtual background. A blurred or clean plain background looks more professional.")
    if "reschedule" in lower or "schedule" in lower:
        improvements.append("Be more careful with interview scheduling and commitment management; reliability matters as much as preparation.")
    if "hospital" in lower:
        improvements.append("For unavoidable emergencies, communicate early and professionally so the interview process does not look careless.")
    if "behavioral" in lower and not any("behavioral" in x.lower() for x in improvements):
        improvements.append("Improve behavioral interviewing with structured, detailed examples instead of general answers.")

    return list(dict.fromkeys(strengths))[:5], list(dict.fromkeys(improvements))[:5]


def generate_feedback(row, sender_name, sender_title, company_name):
    name = candidate_name(row.get("Candidate"))
    domain = candidate_domain(row.get("Candidate"))
    score = row.get("Total Score", "")
    label = readiness_label(score)
    raw_feedback = clean_text(row.get("Feedback", ""))
    remarks = clean_text(row.get("Remarks", ""))
    strengths, improvements = strengths_and_improvements(row)

    if not strengths:
        strengths = ["You participated in the assessment and showed willingness to engage in the process"]
    if not improvements:
        improvements = ["Continue refining Behavioral Responses (10%) and interview presentation to make the performance stronger"]

    intro_quality = "exceptionally well" if label == "Ready for Marketing" else "reasonably well" if "Conditionally" in label else "below the expected market standard"
    result_note = {
        "Ready for Marketing": "Recommended to proceed with marketing activities while continuing to refine behavioral interview techniques and professional interview etiquette.",
        "Conditionally Ready for Marketing": "Recommended to proceed with marketing activities only with continued practice and close attention to the improvement areas mentioned above.",
        "Not Ready for Marketing": "Recommended to pause marketing activities for now and reattempt the assessment after focused preparation.",
        "Pending Review": "Recommended for manual review because the total score is missing or invalid.",
    }.get(label, "Recommended for manual review.")

    domain_label = f" ({domain})" if domain else ""
    score_line = f"\n**Total Score:** {score}/100" if str(score).strip() else ""

    text = f"""### Feedback for {name}{domain_label}

Dear {name},

Thank you for attending the assessment session.

Overall, you performed {intro_quality} during the assessment. {raw_feedback if raw_feedback else 'Your performance was reviewed based on Technical Knowledge (20%), communication, interview readiness, professionalism, and overall market expectations.'}

Some of your key strengths observed during the assessment include:

"""
    for item in strengths:
        text += f"- {item}.\n"

    text += "\nThere are, however, a few areas that need improvement:\n\n"
    for item in improvements:
        text += f"- {item}\n"

    if remarks:
        text += f"\nAdditional note: {remarks}\n"

    text += f"\nWith focused preparation in the areas above, you can improve your overall interview performance and present yourself more effectively in the job market.{score_line}\n\n**Assessment Result:** {label} – {result_note}\n\nBest Regards,  \n{sender_name}  \n{sender_title}  \n{company_name}"
    return text


def get_sheet_id():
    return st.secrets.get("GOOGLE_SHEET_ID", "") or st.secrets.get("google_sheet_id", "")


def get_worksheet():
    sheet_id = get_sheet_id()
    if not sheet_id:
        raise RuntimeError("Missing GOOGLE_SHEET_ID in Streamlit secrets.")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=scopes
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)

    try:
        worksheet = spreadsheet.worksheet("Assessments")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Assessments", rows=1000, cols=len(DEFAULT_COLUMNS))
        worksheet.append_row(DEFAULT_COLUMNS)

    existing_headers = worksheet.row_values(1)
    if existing_headers != DEFAULT_COLUMNS:
        worksheet.update("A1", [DEFAULT_COLUMNS])
    return worksheet


def load_saved_data():
    worksheet = get_worksheet()
    records = worksheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=DEFAULT_COLUMNS)
    df = pd.DataFrame(records)
    for col in DEFAULT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[DEFAULT_COLUMNS]


def save_new_rows(rows_df):
    worksheet = get_worksheet()
    rows_to_save = []
    for _, row in rows_df.iterrows():
        row_dict = {col: clean_text(row.get(col, "")) for col in INPUT_COLUMNS}
        if not row_dict.get("Candidate"):
            continue
        row_dict["Assessment ID"] = str(uuid.uuid4())
        row_dict["Saved At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_dict["Generated Feedback"] = generate_feedback(
            row_dict,
            st.session_state.get("sender_name", "Suzit Dev"),
            st.session_state.get("sender_title", "Deputy Manager"),
            st.session_state.get("company_name", "B. AND B. Soft Tech Kathmandu Pvt. Ltd."),
        )
        rows_to_save.append([row_dict.get(col, "") for col in DEFAULT_COLUMNS])

    if rows_to_save:
        worksheet.append_rows(rows_to_save, value_input_option="USER_ENTERED")
    return len(rows_to_save)


def load_excel(uploaded_file):
    raw = pd.read_excel(uploaded_file, header=None)
    header = raw.iloc[0].tolist()
    df = raw.iloc[2:].copy()
    df.columns = header
    df = df.loc[:, [c for c in df.columns if pd.notna(c)]]
    for col in INPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[INPUT_COLUMNS].reset_index(drop=True)


st.title("Candidate Assessment Feedback Generator")
st.caption("Shared version: saves assessment records to Google Sheets so everyone sees the same data.")

with st.sidebar:
    st.header("Signature")
    st.session_state["sender_name"] = st.text_input("Your Name", value="Suzit Dev")
    st.session_state["sender_title"] = st.text_input("Title", value="Deputy Manager")
    st.session_state["company_name"] = st.text_input("Company", value="B. AND B. Soft Tech Kathmandu Pvt. Ltd.")
    st.header("Readiness Rules")
    st.write("85+ = Ready | 70–84 = Conditionally Ready | Below 70 = Not Ready")

missing_secrets = False
try:
    _ = get_sheet_id()
    if not _ or "gcp_service_account" not in st.secrets:
        missing_secrets = True
except Exception:
    missing_secrets = True

if missing_secrets:
    st.error("Google Sheets database is not connected yet. Add GOOGLE_SHEET_ID and gcp_service_account in Streamlit secrets.")
    st.stop()

tab_add, tab_saved = st.tabs(["Add / Upload Assessment", "Saved Assessments"])

with tab_add:
    uploaded = st.file_uploader("Upload Technical Assessment Excel file", type=["xlsx"])

    if uploaded:
        df = load_excel(uploaded)
    else:
        df = pd.DataFrame(columns=INPUT_COLUMNS)
        st.info("Upload your Excel file or add rows manually below.")

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Feedback": st.column_config.TextColumn(width="large"),
            "Remarks": st.column_config.TextColumn(width="medium"),
            "Total Score": st.column_config.NumberColumn(min_value=0, max_value=100),
        },
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("Save Assessment Data", type="primary"):
            try:
                count = save_new_rows(edited_df)
                st.success(f"Saved {count} row(s) to the shared Google Sheet.")
            except Exception as e:
                st.error(f"Save failed: {e}")

    if len(edited_df) > 0:
        candidate_options = [f"{i + 1}. {clean_text(row.get('Candidate'))}" for i, row in edited_df.iterrows() if clean_text(row.get("Candidate"))]
        if candidate_options:
            selected = st.selectbox("Select candidate for feedback preview", candidate_options)
            selected_idx = int(selected.split(".", 1)[0]) - 1
            row = edited_df.iloc[selected_idx]
            generated = generate_feedback(
                row,
                st.session_state["sender_name"],
                st.session_state["sender_title"],
                st.session_state["company_name"],
            )

            st.subheader("Generated Feedback Preview")
            st.markdown(generated)
            st.download_button(
                "Download Feedback as .txt",
                data=generated.encode("utf-8"),
                file_name=f"feedback_{candidate_name(row.get('Candidate')).replace(' ', '_')}.txt",
                mime="text/plain",
            )

    output = BytesIO()
    edited_df.to_excel(output, index=False)
    st.download_button(
        "Download Current Edited Data",
        data=output.getvalue(),
        file_name="updated_technical_assessment.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with tab_saved:
    st.subheader("Saved Assessments")
    if st.button("Refresh Saved Data"):
        st.rerun()
    try:
        saved_df = load_saved_data()
        st.dataframe(saved_df, use_container_width=True)

        if len(saved_df) > 0:
            saved_options = [f"{i + 1}. {clean_text(row.get('Candidate'))}" for i, row in saved_df.iterrows() if clean_text(row.get("Candidate"))]
            selected_saved = st.selectbox("Select saved candidate", saved_options, key="saved_candidate")
            saved_idx = int(selected_saved.split(".", 1)[0]) - 1
            saved_row = saved_df.iloc[saved_idx]
            saved_feedback = clean_text(saved_row.get("Generated Feedback")) or generate_feedback(
                saved_row,
                st.session_state["sender_name"],
                st.session_state["sender_title"],
                st.session_state["company_name"],
            )
            st.subheader("Saved Feedback")
            st.markdown(saved_feedback)

            saved_output = BytesIO()
            saved_df.to_excel(saved_output, index=False)
            st.download_button(
                "Download All Saved Assessments",
                data=saved_output.getvalue(),
                file_name="all_saved_assessments.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    except Exception as e:
        st.error(f"Could not load saved assessments: {e}")
