import streamlit as st
import requests
import json
import base64
from io import BytesIO
from datetime import datetime

# --- CONFIG ---
API_URL = st.secrets.get("API_URL", "http://localhost:8000")
st.set_page_config(page_title="AI Resume Chatbot", layout="wide")

# --- SESSION STATE FOR CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- UTILITY FUNCTIONS ---
def decode_file(file):
    """Return file content as string"""
    if not file:
        return ""
    try:
        return file.read()
    except Exception:
        return b""

def download_report(data, filename="resume_analysis.json"):
    """Generate download link for JSON report"""
    json_str = json.dumps(data, indent=2)
    b64 = base64.b64encode(json_str.encode()).decode()
    href = f'<a href="data:file/json;base64,{b64}" download="{filename}">📥 Download Analysis Report</a>'
    st.markdown(href, unsafe_allow_html=True)

def send_to_api(resume_bytes=None, job_bytes=None, resume_text="", job_text=""):
    """Call backend API depending on input type"""
    try:
        if resume_bytes:
            files = {"resume_file": ("resume", resume_bytes)}
            data = {"job_description": job_text}
            response = requests.post(f"{API_URL}/analyze-upload", files=files, data=data)
        else:
            payload = {"resume_text": resume_text, "job_description": job_text}
            response = requests.post(f"{API_URL}/analyze", json=payload)
        return response
    except Exception as e:
        st.error(f"API call failed: {str(e)}")
        return None

# --- UI HEADER ---
st.markdown("<h1 style='text-align:center'>🤖 AI Resume Analyzer Chatbot</h1>", unsafe_allow_html=True)
st.markdown("Drag & drop your resume or paste your text in the chat below.")

# --- DRAG & DROP FILE UPLOAD ---
uploaded_resume = st.file_uploader("Drag and drop resume here (pdf, txt, docx)", type=["pdf", "txt", "docx"], key="resume_drop")
uploaded_job = st.file_uploader("Optional: Job Description (pdf, txt, docx)", type=["pdf", "txt", "docx"], key="job_drop")
job_text = st.text_area("Or paste Job Description here (optional)", height=150)

# --- USER INPUT FORM ---
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("💬 Type message or paste resume text here")
    submitted = st.form_submit_button("Send")

# --- HANDLE SUBMISSION ---
if submitted or uploaded_resume:
    if uploaded_resume:
        resume_bytes = uploaded_resume.read()
        job_bytes = uploaded_job.read() if uploaded_job else None
        response = send_to_api(resume_bytes=resume_bytes, job_bytes=job_bytes, job_text=job_text)
        user_msg = "📄 Uploaded Resume"
    else:
        response = send_to_api(resume_text=user_input, job_text=job_text)
        user_msg = user_input

    # Add user message to session
    st.session_state.messages.append({"role": "user", "content": user_msg})

    # Add AI response
    if response and response.status_code == 200:
        data = response.json()
        ai_msg = f"🎯 **Match Score:** {data.get('match_score',0)}%\n\n"
        ai_msg += f"📝 **Resume Skills:** {', '.join(data.get('skills_resume', []))}\n"
        ai_msg += f"💼 **Job Skills:** {', '.join(data.get('skills_job', []))}\n\n"
        ai_msg += "**Suggestions:**\n" + "\n".join(f"- {s}" for s in data.get("suggestions", []))
        st.session_state.messages.append({"role": "ai", "content": ai_msg})
        download_report(data)
    elif response:
        st.session_state.messages.append({"role": "ai", "content": f"Error: {response.status_code} - {response.text}"})

# --- DISPLAY CHAT BUBBLES ---
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"<div style='background-color:#DCF8C6;padding:10px;border-radius:10px;margin:5px 0'><b>You:</b> {msg['content']}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='background-color:#F1F0F0;padding:10px;border-radius:10px;margin:5px 0'><b>AI:</b> {msg['content']}</div>",
            unsafe_allow_html=True
        )

st.markdown("---")
st.caption(f"Built with ❤️ using Streamlit & FastAPI | {datetime.now().year}")