import re
from io import BytesIO

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Assessment Feedback Generator", page_icon="📝", layout="wide")

DEFAULT_COLUMNS = [
    "Candidate", "Personal", "Interviewer", "Date and time", "Remarks",
    "Device & Internet Setup", "Appearance & Background", "Energy & Confidence",
    "Communication Skills", "Introduction Pitch", "Technical Knowledge",
    "Behavioral Responses", "Resume & Project Knowledge", "Professional Etiquette",
    "Overall Market Readiness", "Total Score", "Feedback"
]

SCORE_COLUMNS = [
    "Device & Internet Setup", "Appearance & Background", "Energy & Confidence",
    "Communication Skills", "Introduction Pitch", "Technical Knowledge",
    "Behavioral Responses", "Resume & Project Knowledge", "Professional Etiquette",
    "Overall Market Readiness"
]

WEIGHTS = {
    "Device & Internet Setup": 0.10,
    "Appearance & Background": 0.10,
    "Energy & Confidence": 0.10,
    "Communication Skills": 0.15,
    "Introduction Pitch": 0.10,
    "Technical Knowledge": 0.20,
    "Behavioral Responses": 0.10,
    "Resume & Project Knowledge": 0.05,
    "Professional Etiquette": 0.05,
    "Overall Market Readiness": 0.05,
}

MAX_SCORE = {
    "Device & Internet Setup": 10,
    "Appearance & Background": 10,
    "Energy & Confidence": 10,
    "Communication Skills": 15,
    "Introduction Pitch": 10,
    "Technical Knowledge": 20,
    "Behavioral Responses": 10,
    "Resume & Project Knowledge": 10,
    "Professional Etiquette": 5,
    "Overall Market Readiness": 5,
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
        ("Device & Internet Setup", "Strong device and internet setup", "Ensure device, camera, audio, and internet are fully stable before every interview."),
        ("Appearance & Background", "Professional appearance and acceptable interview background", "Improve the interview background. Use a clean/plain background or blur, not a distracting virtual background."),
        ("Energy & Confidence", "Good energy and confidence throughout the session", "Increase energy and confidence; low energy makes even correct answers sound weak."),
        ("Communication Skills", "Clear communication and professional speaking style", "Improve communication by keeping answers direct, structured, and relevant to the question."),
        ("Introduction Pitch", "Well-structured introduction pitch", "Strengthen the introduction pitch so it clearly sells experience, skills, tools, and target role."),
        ("Technical Knowledge", "Strong technical knowledge and ability to explain concepts", "Strengthen technical fundamentals and practice explaining concepts with examples from project work."),
        ("Behavioral Responses", "Good behavioral response quality", "Practice behavioral questions using the STAR method with real examples and measurable outcomes."),
        ("Resume & Project Knowledge", "Strong understanding of resume, projects, and responsibilities", "Review resume and project details carefully so every claim can be explained confidently."),
        ("Professional Etiquette", "Professional etiquette during the assessment", "Improve professional etiquette, especially scheduling discipline, punctuality, and interview commitment."),
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
        improvements = ["Continue refining behavioral responses and interview presentation to make the performance stronger"]

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

Overall, you performed {intro_quality} during the assessment. {raw_feedback if raw_feedback else 'Your performance was reviewed based on technical knowledge, communication, interview readiness, professionalism, and overall market expectations.'}

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


def load_excel(uploaded_file):
    raw = pd.read_excel(uploaded_file, header=None)
    header = raw.iloc[0].tolist()
    df = raw.iloc[2:].copy()
    df.columns = header
    df = df.loc[:, [c for c in df.columns if pd.notna(c)]]
    for col in DEFAULT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[DEFAULT_COLUMNS].reset_index(drop=True)


st.title("Candidate Assessment Feedback Generator")
st.caption("Upload your Technical Assessment Excel file, edit the scores/details, and generate candidate-ready feedback.")

with st.sidebar:
    st.header("Signature")
    sender_name = st.text_input("Your Name", value="Suzit Dev")
    sender_title = st.text_input("Title", value="Deputy Manager")
    company_name = st.text_input("Company", value="B. AND B. Soft Tech Kathmandu Pvt. Ltd.")
    st.header("Readiness Rules")
    st.write("85+ = Ready | 70–84 = Conditionally Ready | Below 70 = Not Ready")

uploaded = st.file_uploader("Upload Technical Assessment Excel file", type=["xlsx"])

if uploaded:
    df = load_excel(uploaded)
else:
    df = pd.DataFrame(columns=DEFAULT_COLUMNS)
    st.info("Upload your Excel file to begin. You can also add rows manually below.")

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

if len(edited_df) > 0:
    candidate_options = [f"{i + 1}. {clean_text(row.get('Candidate'))}" for i, row in edited_df.iterrows() if clean_text(row.get("Candidate"))]
    selected = st.selectbox("Select candidate", candidate_options)
    selected_idx = int(selected.split(".", 1)[0]) - 1

    row = edited_df.iloc[selected_idx]
    generated = generate_feedback(row, sender_name, sender_title, company_name)

    st.subheader("Generated Feedback")
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
        "Download Updated Assessment Data",
        data=output.getvalue(),
        file_name="updated_technical_assessment.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
