# AI-Powered Resume Analyzer & Job Fit Chatbot

## Overview
This project contains a Streamlit frontend and a FastAPI backend that together implement an **AI-powered Resume Analyzer & Job Fit Chatbot**. Users upload resumes and provide (or paste) a job description. The backend extracts skills, computes a match score, and returns suggestions and an editable report. The project supports optional integration with OpenAI (via `OPENAI_API_KEY`) for richer suggestions, or falls back to heuristic rules if the key is not provided.

## Structure
- `frontend/` - Streamlit UI
  - `app.py` - Streamlit application
  - `requirements.txt`
- `backend/` - FastAPI backend
  - `main.py` - FastAPI server
  - `nlp.py` - simple NLP utilities and LLM wrapper (OpenAI optional)
  - `requirements.txt`
- `docker-compose.yml` - example to run both services
- `README.md` - this file

## How to run (local)
1. Create a Python virtual environment for frontend and backend or use docker-compose.
2. Install backend requirements: `pip install -r backend/requirements.txt`
3. Run backend: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
4. Install frontend requirements: `pip install -r frontend/requirements.txt`
5. Run frontend: `streamlit run frontend/app.py --server.port 8501`

## Using OpenAI (optional)
If you want better AI-generated suggestions, set the environment variable:
```
OPENAI_API_KEY=sk-...
```
The backend will use OpenAI's ChatCompletion if available. If not provided, it uses a heuristic-based fallback.

## Docker (example)
`docker-compose.yml` included to run both services. You may need to build/pull images depending on your environment.

## Notes
- This project is a starter template. You should improve NLP pipelines, add authentication (Java microservice suggested separately), and secure the deployment for production.
- The included skill list is illustrative. Replace/extend with a domain-specific skill taxonomy for better results.