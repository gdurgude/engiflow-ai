# EngiFlow AI account & animation upgrade

## Install safely

1. **Back up your current project** (especially the `data/` directory and `backend/.env`).
2. Merge/replace only `backend/app/main.py`, `backend/app/static/index.html`, `backend/app/static/app.js`, and `backend/app/static/styles.css` from this update into your existing project. Also copy `backend/scripts/claim_legacy_projects.py`.
3. Keep your existing `data/` and `.env` folders/files. Do not delete your SQLite database.
4. Run from `backend/`: `python -m pip install -r requirements.txt`, then `python -m uvicorn app.main:app --reload`.
5. Open http://127.0.0.1:8000/ and sign up. An intro logo will appear briefly before the sign-in/dashboard screen.

## Your previous projects

Previously-created projects stay in SQLite, **but are initially unassigned and hidden** for privacy. Once you sign up, from `backend/` run:

`python scripts/claim_legacy_projects.py your-email@example.com`

Enter `CLAIM` when prompted. This assigns all previously unowned projects to that account without deleting PDFs/chunks. Run it only on your own local database.

## Other users

Each account has isolated projects, documents, and AI access. Passwords are salted and hashed using PBKDF2; sessions use HTTP-only cookies and CSRF tokens. This is a **local multi-account MVP**. Letting other people access the site remotely requires deployment, a domain, HTTPS (set `ENGIFLOW_SECURE_COOKIES=true` when on HTTPS), rate limiting, email verification, password resets, backups, and a production security review. Do not expose this development server or real customer documents publicly yet.

## Tests

From `backend/`: `python -m pytest -q`
