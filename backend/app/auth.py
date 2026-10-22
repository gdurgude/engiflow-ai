from .main import *

def send_verification(email: str, raw_token: str):

    """Email through Resend. Explicit console mode is for local testing only."""

    mode = os.getenv('ENGIFLOW_EMAIL_MODE', 'console').lower()

    if mode == 'console':

        if os.getenv('ENGIFLOW_ALLOW_CONSOLE_EMAIL', '').lower() != 'true':

            raise HTTPException(503, 'Email delivery is not configured')

        print(f'\n[LOCAL DEVELOPMENT ONLY] Verification token for {email}: {raw_token}\n', flush=True)

        return

    if mode != 'resend':

        raise HTTPException(503, 'Unsupported email delivery mode')

    api_key = os.getenv('RESEND_API_KEY')

    sender = os.getenv('ENGIFLOW_FROM_EMAIL')

    if not api_key or not sender:

        raise HTTPException(503, 'Email provider is not configured')

    payload = json.dumps({
        'from': sender, 'to': [email], 'subject': 'Verify your EngiFlow AI email',
        'text': ('Your verification code is: ' + raw_token + '\n\n'
                 'This code expires in 15 minutes. Do not share it.')
    }).encode()

    req = urllib.request.Request('https://api.resend.com/emails', data=payload,
        headers={'Authorization': 'Bearer '+api_key, 'Content-Type': 'application/json'}, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=12) as res:

            if res.status >= 300: raise RuntimeError('Email provider rejected the request')

    except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
        raise HTTPException(503, 'Could not deliver verification email. Try again later') from exc

def issue_verification(user_id: str, email: str):

    now = int(time.time())

    raw = f'{secrets.randbelow(1000000):06d}'

    hashed = hashlib.sha256((user_id + ':' + raw).encode()).hexdigest()

    with db() as conn:

        prev = conn.execute('SELECT last_sent_at FROM email_verifications WHERE user_id=?', (user_id,)).fetchone()

        if prev and now - prev['last_sent_at'] < 60:

            raise HTTPException(429, 'Please wait before requesting another code')

        conn.execute('''INSERT INTO email_verifications(user_id, token_hash, expires_at, last_sent_at, attempts)
            VALUES(?,?,?,?,0) ON CONFLICT(user_id) DO UPDATE SET token_hash=excluded.token_hash,
            expires_at=excluded.expires_at, last_sent_at=excluded.last_sent_at, attempts=0''',
            (user_id, hashed, now + 900, now))

    send_verification(email, raw)

class EmailOnly(BaseModel):

    email: str = Field(min_length=3, max_length=254)

class VerifyEmailIn(EmailOnly):

    code: str = Field(pattern=r'^\d{6}$')

@app.post('/auth/signup', status_code=201)
def signup(body: SignupIn):

    email = body.email.strip().lower()

    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):

        raise HTTPException(400, 'Enter a valid email address')

    name = body.name.strip()

    if not name: raise HTTPException(400, 'Enter your name')
    uid = str(uuid4())
    with db() as conn:
        if conn.execute('SELECT 1 FROM users WHERE email=?', (email,)).fetchone():
            raise HTTPException(409, 'An account with this email already exists')
        conn.execute('INSERT INTO users(id,name,email,password_hash) VALUES (?,?,?,?)',
                     (uid,name,email,hash_password(body.password)))
    issue_verification(uid, email)
    return {'verification_required': True, 'message': 'Check your email for a six-digit verification code'}

@app.post('/auth/resend-verification')
def resend_verification(body: EmailOnly):
    email = body.email.strip().lower()
    with db() as conn:
        user = conn.execute('SELECT id,email,email_verified_at FROM users WHERE email=?', (email,)).fetchone()
    if user and user['email_verified_at'] is None:
        issue_verification(user['id'], email)
    return {'message': 'If that address has a pending account, a code will be sent'}

@app.post('/auth/verify-email')
def verify_email(body: VerifyEmailIn, response: Response):
    email = body.email.strip().lower()
    now = int(time.time())
    with db() as conn:
        u = conn.execute('SELECT id,name,email,email_verified_at FROM users WHERE email=?', (email,)).fetchone()
        if not u or u['email_verified_at'] is not None:
            raise HTTPException(400, 'Invalid or expired verification code')
        record = conn.execute('SELECT * FROM email_verifications WHERE user_id=?', (u['id'],)).fetchone()
        if not record or record['expires_at'] <= now or record['attempts'] >= 5:
            raise HTTPException(400, 'Invalid or expired verification code')
        conn.execute('UPDATE email_verifications SET attempts=attempts+1 WHERE user_id=?', (u['id'],))
        expected = hashlib.sha256((u['id'] + ':' + body.code).encode()).hexdigest()
        if not hmac.compare_digest(record['token_hash'], expected):
            raise HTTPException(400, 'Invalid or expired verification code')
        conn.execute('UPDATE users SET email_verified_at=? WHERE id=?', (now,u['id']))
        conn.execute('DELETE FROM email_verifications WHERE user_id=?',(u['id'],))
    csrf = create_session(response, u['id'])
    return {'user': {'id':u['id'],'name':u['name'],'email':u['email']}, 'csrf':csrf}

@app.post('/auth/login')
def login(body: AuthIn, response: Response):
    with db() as conn:
        u = conn.execute('SELECT * FROM users WHERE email=?', (body.email.strip().lower(),)).fetchone()
    if not u or not verify_password(body.password, u['password_hash']):
        raise HTTPException(401, 'Invalid email or password')
    if u['email_verified_at'] is None:
        raise HTTPException(403, 'Please verify your email before signing in')
    csrf = create_session(response, u['id'])
    return {'user': {'id':u['id'],'name':u['name'],'email':u['email']}, 'csrf':csrf}

@app.get('/auth/me')
def me(user=Depends(current_user)):
    return {'user': {k:user[k] for k in ('id','name','email')}, 'csrf':user['csrf']}

@app.post('/auth/logout')
def logout(response: Response, request: Request, user=Depends(current_user)):
    raw = request.cookies.get('engiflow_session')
    with db() as conn:
        conn.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(raw.encode()).hexdigest(),))
    response.delete_cookie('engiflow_session', path='/')
    return {'ok': True}
