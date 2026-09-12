# AIVOA Copilot — AI-Powered Pharmaceutical Customer Complaint Management System

![AIVOA System Banner](https://img.shields.io/badge/FDA_GxP-21_CFR_Part_211-00d4ff)
![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-7928ca)
![Groq](https://img.shields.io/badge/Groq-gemma2--9b--it-ff0080)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688)
![React](https://img.shields.io/badge/React-18-61dafb)
![Redux Toolkit](https://img.shields.io/badge/Redux_Toolkit-State-764abc)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791)

An enterprise-grade, AI-assisted Customer Complaint Management System built for pharmaceutical and medical device manufacturing companies (compliant with FDA 21 CFR Part 211 and ISO 13485 concepts). 

The system accepts unstructured customer complaint narratives via **PDF/DOCX/TXT document uploads** or **direct chat input**, automatically parses and populates 13 mandatory GxP complaint fields, performs automated risk & duplicate analysis, suggests 5-Why root cause & CAPA recommendations, and provides a real-time **AIVOA Copilot** assistant for field corrections.

---

## 📹 Code Explanation Video

> **Video Link**: [Watch the Full End-to-End Code & Architecture Walkthrough](https://youtu.be/YOUR_VIDEO_LINK_HERE) *(Replace with your uploaded Loom/YouTube/Drive link)*  
>
> **Walkthrough Scope**:
> 1. **Frontend Input**: User narrative submission & PDF/DOCX document upload via React & Redux Toolkit.
> 2. **API Layer**: FastAPI endpoints (`/api/v1/complaints/process`, `/upload`, `/copilot/chat`).
> 3. **AI & Workflow**: 7-node LangGraph State Machine pipeline powered by Groq (`gemma2-9b-it`) and PostgreSQL.
> 4. **Output & UI Sync**: Real-time form population, risk scoring, duplicate banners, Ishikawa/CAPA display, and field highlight animations.

---

## 💡 Key Features

1. **Dual-Input Complaint Processing**:
   - **Document Upload**: Drop PDF, DOCX, or TXT complaint letters or customer report files.
   - **Copilot Narrative Paste**: Directly paste unstructured narrative text into the input panel.
2. **13 Structured GxP Fields Extraction**:
   - *Complaint Source*, *Customer Name*, *Product Name*, *Product Strength / Grade*, *Batch / Lot Number*, *Affected Quantity*, *Manufacturing Date*, *Expiry Date*, *Manufacturing Site*, *Material Type*, *Complaint Date*, *Complaint Type*, *Complaint Description*.
3. **LangGraph State Machine AI Workflow**:
   - Sequential, modular 7-node pipeline balancing pure Python deterministic validation with Groq LLM intelligence.
4. **Automated Risk Assessment & Patient Safety Flags**:
   - Evaluates severity (*Critical*, *Major*, *Minor*, *Low*) and flags immediate clinical/patient hazards under FDA guidelines.
5. **PostgreSQL Duplicate Complaint Detection**:
   - Queries DB for matching Product Name + Batch/Lot number to flag recurring quality issues.
6. **AI Root Cause & CAPA Recommendations**:
   - Generates 5-Why & Fishbone (Ishikawa) root cause hypotheses and ISO 13485 aligned Corrective and Preventive Actions.
7. **AIVOA Copilot Form Synchronization**:
   - Natural language field corrections (e.g. *"The batch number is CHG 260712A and affected quantity is 50 kg"*) automatically update form inputs with visual glow highlights.

---

## 🛠️ Technology Stack

- **Frontend**: React 18, Redux Toolkit, Vite, Vanilla Glassmorphism CSS, Lucide Icons
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 ORM
- **AI & Workflow**: LangGraph (`StateGraph`), Groq API (`gemma2-9b-it`), LangChain
- **Document Processing**: `pypdf`, `pdfplumber`, `python-docx`
- **Database**: PostgreSQL (with SQLite zero-setup local dev fallback)
- **Containerization & Testing**: Docker, Docker Compose, Pytest

---

## 🚀 Quickstart Guide

### Option 1: Zero-Setup Local Development (SQLite & Python)

#### 1. Backend Setup:
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy .env configuration
cp ../.env.example .env

# Run FastAPI dev server
uvicorn main:app --reload --port 8000
```
Backend API interactive documentation will be available at: `http://localhost:8000/docs`

#### 2. Frontend Setup:
```bash
# Open new terminal and navigate to frontend
cd frontend

# Install Node modules
npm install

# Run Vite dev server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

### Option 2: Docker Compose (PostgreSQL + FastAPI + React)

Ensure Docker Desktop is running, then run:

```bash
docker compose up --build
```

Services started:
- Frontend UI: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- PostgreSQL DB: `localhost:5432` (`aivoa_db`)

---

## 🧠 LangGraph Architecture & Technical Interview Preparation

### LangGraph Workflow Diagram

```
[START] ➔ [1. Extraction Node] ➔ [2. Validation Node] ➔ [3. Severity Node] 
            │ (LLM)                  │ (Python Rules)       │ (LLM + Rules)
            ▼                        ▼                      ▼
        [END]  [7. Summary Node]  [6. CAPA Node]  [5. Root Cause Node]  [4. Duplicate Node]
                 (LLM)                (LLM)             (LLM)                 (PostgreSQL Query)
```

### Interview Q&A Cheatsheet

#### Q1: Why use LangGraph instead of a single giant prompt?
> *"A single prompt combining extraction, validation, risk scoring, duplicate checking, and CAPA generation suffers from high latency, prompt bloat, hallucination, and zero testability. LangGraph structures the AI into a stateful directed graph. Each node has a single responsibility. Deterministic operations like required field validation and DB duplicate lookups run in Python/SQL, while semantic tasks like entity extraction and root cause reasoning use Groq LLM."*

#### Q2: How does LangGraph State work?
> *"State is declared as a `TypedDict` (`ComplaintGraphState`) containing raw text, extracted fields, validation results, risk scores, duplicate flags, and CAPA arrays. Each node consumes the state, executes its logic, and returns state key updates that LangGraph automatically merges."*

#### Q3: How do natural language corrections work in Copilot?
> *"When a user types a correction in the chat (e.g. 'The batch number is CHG 260712A'), FastAPI routes the current form state and message to `/api/copilot/chat`. The service extracts the changed keys and dispatches an update to the Redux `complaintFormSlice`, triggering a re-render and visual highlight animation on the target form inputs."*

#### Q4: How is hallucination prevented in field extraction?
> *"We use Groq's `with_structured_output` backed by Pydantic schemas. System prompts explicitly instruct the LLM to extract strictly stated facts and set unmentioned fields to `null` rather than guessing."*

---

## 📋 Sample Demo Complaint Narratives

### Sample 1: Metformin 500mg (Broken Tablets)
```text
A customer reported that several Metformin 500 mg tablets from batch MET500-KP4821 had broken tablets inside 15 blister packs. The batch was manufactured on 18 March 2026 and expires on 17 March 2029. The complaint was received on 11 September 2026. No patient injury was reported.
```

### Sample 2: Copilot Natural Language Correction
```text
The batch number is CHG 260712A and affected quantity is 50 kg
```

---

## 🧪 Running Backend Unit Tests

```bash
cd backend
python -m pytest tests
```

---

## 📄 License

MIT License. Built for technical demonstration and GitHub publication.
