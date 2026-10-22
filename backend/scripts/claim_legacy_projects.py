"""One-time local-only migration of pre-auth projects to a registered account.
Run from backend folder: python scripts/claim_legacy_projects.py you@example.com
Never expose this command as an HTTP endpoint.
"""
import sys
import sqlite3
from pathlib import Path

if len(sys.argv) != 2:
    print('Usage: python scripts/claim_legacy_projects.py you@example.com')
    raise SystemExit(2)
email = sys.argv[1].strip().lower()
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'backend'))
from app.main import DB  # noqa: E402
con = sqlite3.connect(DB)
try:
    user = con.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
    if not user:
        print('Account not found. Sign up in the website first.')
        raise SystemExit(1)
    count = con.execute('SELECT count(*) FROM projects WHERE owner_id IS NULL').fetchone()[0]
    print(f'{count} legacy projects are unassigned. Assign ALL to {email}? Type CLAIM to continue:')
    if input().strip() != 'CLAIM':
        print('Cancelled.')
        raise SystemExit(1)
    con.execute('UPDATE projects SET owner_id=? WHERE owner_id IS NULL', (user[0],))
    con.commit()
    print(f'Assigned {count} legacy projects to {email}.')
finally:
    con.close()
