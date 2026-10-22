import os
import re
import sqlite3
import secrets
import hashlib
import hmac
import time
import json
import io
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager

import fitz
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request, Response, Depends, Header, Cookie
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE = Path(os.getenv('ENGIFLOW_DATA_DIR', str(Path(__file__).resolve().parents[2] / 'data')))
BASE.mkdir(parents=True, exist_ok=True)
DB = BASE / 'engiflow.db'
UPLOADS = BASE / 'uploads'
UPLOADS.mkdir(exist_ok=True)


@contextmanager

def db():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


with db() as conn:
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, filename TEXT NOT NULL, page_count INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(project_id) REFERENCES projects(id));
        CREATE TABLE IF NOT EXISTS chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL, page_number INTEGER NOT NULL, content TEXT NOT NULL, FOREIGN KEY(document_id) REFERENCES documents(id));
        CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, csrf TEXT NOT NULL, expires_at INTEGER NOT NULL);

    ''')

# Existing projects remain unowned after upgrade until explicitly claimed locally.

with db() as conn:
    columns = [c['name'] for c in conn.execute('PRAGMA table_info(projects)')]
    if 'owner_id' not in columns:
        conn.execute('ALTER TABLE projects ADD COLUMN owner_id TEXT')
    user_columns = [c['name'] for c in conn.execute('PRAGMA table_info(users)')]
    if 'email_verified_at' not in user_columns:
        conn.execute('ALTER TABLE users ADD COLUMN email_verified_at INTEGER')
    conn.execute("""CREATE TABLE IF NOT EXISTS email_verifications (
        user_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, expires_at INTEGER NOT NULL,
        last_sent_at INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0)""")


def hash_password(password):
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 480_000)
    return 'pbkdf2_sha256$480000$' + salt.hex() + '$' + key.hex()


def verify_password(password, stored):
    try:
        algo, rounds, salt, expected = stored.split('$')
        if algo != 'pbkdf2_sha256': return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def current_user(request: Request):
    raw = request.cookies.get('engiflow_session')
    if not raw: raise HTTPException(401, 'Please sign in first')
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with db() as conn:
        user = conn.execute('''SELECT users.id, users.name, users.email, sessions.csrf
            FROM sessions JOIN users ON sessions.user_id=users.id
            WHERE token_hash=? AND expires_at>? AND users.email_verified_at IS NOT NULL''', (digest, int(time.time()))).fetchone()
    if not user: raise HTTPException(401, 'Your session expired. Please sign in again')
    if request.method not in ('GET','HEAD','OPTIONS'):
        if not hmac.compare_digest(request.headers.get('X-CSRF-Token',''), user['csrf']):
            raise HTTPException(403, 'Invalid request token')
    return dict(user)


def create_session(response, user_id):
    raw = secrets.token_urlsafe(40)
    csrf = secrets.token_urlsafe(32)
    expires = int(time.time()) + 7*24*3600
    with db() as conn:
        conn.execute('INSERT INTO sessions(token_hash,user_id,csrf,expires_at) VALUES (?,?,?,?)',
                     (hashlib.sha256(raw.encode()).hexdigest(), user_id, csrf, expires))
    response.set_cookie('engiflow_session', raw, httponly=True, samesite='strict', secure=os.getenv('ENGIFLOW_SECURE_COOKIES','false').lower()=='true', max_age=7*24*3600, path='/')
    return csrf


class AuthIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)


class SignupIn(AuthIn):
    name: str = Field(min_length=1, max_length=100)


app = FastAPI(title='EngiFlow AI', version='0.1.0', description='Prototype engineering-document intelligence API. Not an engineering validation tool.')
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')], allow_methods=['*'], allow_headers=['*'])


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class AskIn(BaseModel):
    project_id: str
    question: str = Field(min_length=3, max_length=2000)


# Load feature endpoints after shared app state and helpers have been initialized.
from . import auth, projects, reviews  # noqa: E402,F401


@app.get('/health')

def health():
    return {'status': 'ok', 'service': 'engiflow-ai'}

STATIC = Path(__file__).resolve().parent / 'static'
app.mount('/static', StaticFiles(directory=STATIC), name='static')


@app.get('/', include_in_schema=False)

def index():
    return FileResponse(STATIC / 'index.html')
