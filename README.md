# Candidate Assessment Feedback Generator

A simple local Streamlit app for generating candidate feedback from the Technical Assessment Excel file.

## How to run

1. Install Python 3.10 or newer.
2. Open Command Prompt or Terminal in this folder.
3. Run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## How to use

1. Upload `Technical Assessment.xlsx`.
2. Edit candidate details, scores, remarks, or feedback if needed.
3. Select a candidate.
4. Copy or download the generated feedback.
5. Download the updated assessment data if you edited anything.

## Current readiness rules

- 85+ = Ready for Marketing
- 70–84 = Conditionally Ready for Marketing
- Below 70 = Not Ready for Marketing

These rules are editable inside `app.py` in the `readiness_label()` function.
