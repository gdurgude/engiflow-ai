# Deployment readiness checklist

## Repository hygiene
- [ ] Review staged files (`git status`, `git diff --cached --stat`) before first push.
- [ ] Confirm `.env`, DB files, uploaded PDFs, logs, credentials and personal information are absent.
- [ ] Scan git history and source code for leaked tokens; rotate any exposed key.
- [ ] Mark repository **private** while finishing the security work.

## Before public registration
- [ ] Add login/signup rate limiting and brute-force protections.
- [ ] Email verification, password reset, session revocation, registration abuse mitigation.
- [ ] HTTPS enforced, secure cookies enabled, origin controls verified, CSRF checked.
- [ ] Test authorization on every project, document, comparison and export endpoint.
- [ ] Harden PDF parsing against resource exhaustion and malicious inputs; enforce quotas.
- [ ] Durable database, schema migrations, persistent uploads, backup and recovery drills.
- [ ] Log errors without secrets or sensitive document content.
- [ ] Add production process management and uptime monitoring; no `--reload`.
- [ ] Test from a second account; verify cross-user data access is impossible.
- [ ] Prepare privacy statement and consent for uploaded document processing.

## Deployment choices
Start with a *restricted* demo deployment after review. Host the FastAPI web app on an HTTPS service with persistent disk, configured environment variables, and low resource limits. For scalable public hosting, use managed PostgreSQL and object storage instead of local SQLite and file uploads.
