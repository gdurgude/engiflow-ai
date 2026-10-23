# EngiFlow AI

### AI Powered Engineering Document Intelligence Platform

EngiFlow AI is a full stack application built to help engineers work more efficiently with technical documents. It allows users to analyze engineering specifications, ask questions about uploaded PDFs, identify conflicting requirements, and generate structured review reports using AI.

The goal is to make complex engineering documentation easier to understand, organize, and review.

## Key Features

**AI Engineering Assistant:** Ask questions about uploaded documents and receive relevant answers with references to the original specifications.

**Document Analysis:** Extract important engineering requirements and technical details from PDF documents.

**Conflict Detection:** Compare multiple specifications and identify differences in electrical capacities, equipment ratings, and other technical requirements.

**Engineering Review:** Analyze documentation to highlight missing information, potential risks, and areas that need further clarification.

**PDF Report Generation:** Generate downloadable reports summarizing engineering review findings.

**Project Management:** Create individual projects, upload documents, and manage engineering workflows.

**User Authentication:** Account registration, login, email verification, and private project access.

## Tech Stack

**Backend:** Python, FastAPI

**Frontend:** HTML, CSS, JavaScript

**AI Integration:** Groq API, Large Language Models

**Database:** SQLite

**PDF Processing:** PyMuPDF

**Report Generation:** ReportLab

**Authentication:** Password Hashing, Email Code Verification

## How It Works

1. Create an engineering project.
2. Upload technical documents in PDF format.
3. Ask the AI Assistant questions about the uploaded specifications.
4. Extract requirements and identify potential conflicts across documents.
5. Run engineering reviews and generate PDF reports.

## Getting Started

**1. Clone the repository**

```bash
git clone https://github.com/gdurgude/engiflow-ai.git
cd engiflow-ai/backend
```

**2. Set up the Python environment**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Create a `.env` file inside the `backend` directory using `.env.example` as a reference.

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b

ENGIFLOW_EMAIL_MODE=console
ENGIFLOW_ALLOW_CONSOLE_EMAIL=true
```

Console verification is intended for local testing. Actual email delivery requires an email provider.

**5. Run the application**

```bash
python -m uvicorn app.main:app --reload --port 8003
```

Open `http://127.0.0.1:8003/` in your browser.

## What's Next: Conversational Context Memory

My next focus is improving the AI Assistant by adding conversational context memory.

Currently, the assistant answers questions using information retrieved from uploaded documents. I want to extend this so it can remember previous interactions, understand follow up questions, and maintain the flow of a conversation.

For example, a user could ask about a battery storage requirement and then simply ask, "Can you explain that further?" without repeating the original question.

I also plan to improve document comparison accuracy, strengthen authentication, and explore cloud deployment.

## Project Status

**Functional MVP: Actively under development**

The core features for document analysis, AI assistance, engineering review, conflict detection, and PDF reporting are implemented.

EngiFlow AI is designed to support engineering workflows. Technical findings should always be reviewed against the original documents before making engineering decisions.

## Author

**Gaurav Durgude**
GitHub: [gdurgude](https://github.com/gdurgude)
