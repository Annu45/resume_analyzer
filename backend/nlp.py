# backend/nlp.py
import os
import re
import json
import requests
from typing import List, Dict
from collections import Counter

# Optional: import OpenAI if available
try:
    import openai
except Exception:
    openai = None

# Simple skill list - extend this with more entries or a taxonomy
COMMON_SKILLS = [
    "java","python","c++","c#","javascript","react","angular","spring","spring boot","hibernate",
    "sql","postgresql","mysql","nosql","mongodb","docker","kubernetes","aws","azure","gcp",
    "rest api","graphql","microservices","git","linux","data structures","algorithms",
    "machine learning","deep learning","nlp","pytorch","tensorflow","scikit-learn","pandas",
    "numpy","spark","hadoop","jenkins","ci/cd","prometheus","grafana","ansible","terraform"
]

def extract_text_from_file(filename: str, raw_bytes: bytes) -> str:
    # Basic readers for txt, pdf, docx (best-effort)
    text = ""
    lower = filename.lower()
    try:
        if lower.endswith(".txt"):
            text = raw_bytes.decode("utf-8", errors="ignore")
        elif lower.endswith(".pdf"):
            from io import BytesIO
            import PyPDF2
            reader = PyPDF2.PdfReader(BytesIO(raw_bytes))
            pages = [p.extract_text() for p in reader.pages]
            text = "\n".join(pages)
        elif lower.endswith(".docx"):
            import docx
            from io import BytesIO
            doc = docx.Document(BytesIO(raw_bytes))
            paragraphs = [p.text for p in doc.paragraphs]
            text = "\n".join(paragraphs)
        else:
            # try to decode
            text = raw_bytes.decode("utf-8", errors="ignore")
    except Exception:
        text = raw_bytes.decode("utf-8", errors="ignore")
    return text

def normalize_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s+#\.\-]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def extract_skills(text: str, skills_list: List[str] = COMMON_SKILLS) -> List[str]:
    t = normalize_text(text)
    found = set()
    for skill in skills_list:
        if skill in t:
            found.add(skill)
    # Also try to pick camel-case tokens (e.g., JavaScript)
    tokens = re.findall(r"[A-Za-z\+\#]{2,}", text)
    for tok in tokens:
        if tok.lower() in skills_list:
            found.add(tok.lower())
    return sorted(found)

def compute_match(skills_resume: List[str], skills_job: List[str]) -> float:
    if not skills_job:
        return 0.0
    matched = set(skills_resume).intersection(set(skills_job))
    score = len(matched) / max(1, len(set(skills_job)))
    return round(score * 100, 2)

def heuristic_suggestions(skills_resume: List[str], skills_job: List[str]) -> List[str]:
    suggestions = []
    missing = set(skills_job) - set(skills_resume)
    if missing:
        suggestions.append(f"Skills to add or highlight: {', '.join(sorted(missing))}")
    # generic suggestions
    suggestions.append("Quantify achievements (e.g., reduced latency by 30%, processed X records).")
    suggestions.append("Add a short 'Key Projects' section with tech stack and outcomes.")
    if "machine learning" in skills_job or "nlp" in skills_job:
        suggestions.append("Include datasets, model performance metrics (accuracy/F1), and deployment details.")
    return suggestions

def call_gemini_suggestions(resume: str, job: str) -> List[str]:
    """
    Calls Google Generative API (Gemini / text-bison or similar) using a simple HTTP POST.
    Requires environment variable GOOGLE_API_KEY.
    """
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return []

    # choose model by environment variable or default
    model = os.getenv("GEMINI_MODEL", "text-bison-001")  # change if you have different model name
    url = f"https://generativelanguage.googleapis.com/v1beta2/models/{model}:generateText?key={api_key}"

    prompt = (
        "You are an expert career coach.\n"
        "Given the resume text delimited by triple backticks and the job description delimited by triple backticks, "
        "provide 5 concise suggestions to improve the resume for this job. Use short bullet points.\n\n"
        f"Resume:\n```\n{resume[:4000]}\n```\n\n"
        f"Job:\n```\n{job[:4000]}\n```\n\n"
        "Respond with a JSON array of strings only (for example: [\"point1\", \"point2\", ...])."
    )

    payload = {
        "prompt": {
            "text": prompt
        },
        "temperature": 0.2,
        "maxOutputTokens": 512
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # The exact response shape differs by API version; try to extract text from common fields
        # For text-bison style responses, you might get data["candidates"][0]["output"] or data["output"]
        text_out = None
        if isinstance(data, dict):
            # try multiple places
            if "candidates" in data and isinstance(data["candidates"], list) and len(data["candidates"])>0:
                text_out = data["candidates"][0].get("output", None) or data["candidates"][0].get("content", None)
            if not text_out:
                # some versions return 'output' -> 'text' or 'output' -> 'content'
                if "output" in data:
                    if isinstance(data["output"], dict):
                        text_out = data["output"].get("text") or data["output"].get("content")
                    elif isinstance(data["output"], list) and data["output"]:
                        # join pieces
                        pieces = []
                        for item in data["output"]:
                            if isinstance(item, dict):
                                pieces.append(item.get("content",""))
                            else:
                                pieces.append(str(item))
                        text_out = "\n".join(pieces)
                # fallback to top-level 'text' or 'content'
            if not text_out:
                text_out = data.get("text") or data.get("content") or json.dumps(data)
        else:
            text_out = str(data)

        # Try to parse JSON array from model output
        try:
            parsed = json.loads(text_out)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except Exception:
            # Not JSON, split by lines or bullets
            lines = []
            for line in text_out.splitlines():
                line = line.strip()
                if not line:
                    continue
                # remove leading bullets
                line = re.sub(r"^[\-\*\u2022]+\s*", "", line)
                lines.append(line)
            # return up to 7 cleaned lines
            return lines[:7]
    except Exception as e:
        # Print minimal debug (do not crash)
        # If you run into issues, check the backend logs for the exception message.
        # print("Gemini call error:", str(e))
        return []

def call_openai_suggestions(resume: str, job: str) -> List[str]:
    if not openai or not os.getenv("OPENAI_API_KEY"):
        return []
    openai.api_key = os.getenv("OPENAI_API_KEY")
    prompt = f"""You are an expert career coach.
Given the resume text delimited by triple backticks and the job description delimited by triple backticks, provide 5 concise suggestions to improve the resume for this job. Use bullet points.\n\nResume:\n```\n{resume[:4000]}\n```\n\nJob:\n```\n{job[:4000]}\n```\n\nRespond with a JSON array of strings only."""
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini", # user can change
            messages=[{"role":"user","content":prompt}],
            temperature=0.2,
            max_tokens=400
        )
        text = resp.choices[0].message.get("content","")
        # try to parse JSON from response
        data = json.loads(text)
        if isinstance(data, list):
            return data
        lines = [l.strip("-* \t") for l in text.splitlines() if l.strip()]
        return lines[:7]
    except Exception:
        return []

def analyze_resume_and_job(resume_text: str, job_description: str) -> Dict:
    resume_text = resume_text or ""
    job_description = job_description or ""
    skills_resume = extract_skills(resume_text)
    skills_job = extract_skills(job_description)
    match_score = compute_match(skills_resume, skills_job)

    # Preference order: Gemini (Google) -> OpenAI -> Heuristics
    suggestions = []
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        suggestions = call_gemini_suggestions(resume_text, job_description)
    if not suggestions and (openai is not None) and os.getenv("OPENAI_API_KEY"):
        suggestions = call_openai_suggestions(resume_text, job_description)
    if not suggestions:
        suggestions = heuristic_suggestions(skills_resume, skills_job)

    summary = {
        "skills_resume": skills_resume,
        "skills_job": skills_job,
        "match_score": match_score,
        "suggestions": suggestions,
        "short_summary": f"Resume contains {len(skills_resume)} recognized skills. Job requires {len(skills_job)} recognized skills."
    }
    return summary