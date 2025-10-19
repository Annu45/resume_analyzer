from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from nlp import analyze_resume_and_job, extract_text_from_file

app = FastAPI(title="Resume Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    resume_text: Optional[str] = None
    job_description: Optional[str] = None

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    resume = req.resume_text or ""
    job = req.job_description or ""
    result = analyze_resume_and_job(resume, job)
    return result

@app.post("/analyze-upload")
async def analyze_upload(resume_file: UploadFile = File(...), job_description: str = Form("")):
    raw = await resume_file.read()
    text = extract_text_from_file(resume_file.filename, raw)
    result = analyze_resume_and_job(text, job_description)
    return result