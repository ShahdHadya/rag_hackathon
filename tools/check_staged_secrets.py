"""Fail-closed review of this code-only Git snapshot; never print secret values."""
import re
import subprocess
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

root=Path(__file__).resolve().parents[1]
files=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=root).decode().split('\0')
files=[p for p in files if p]
issues=[]
secret_values=[]
for path in [root/'.env',root/'bousala/.env']:
    if not path.exists():
        continue
    env=dotenv_values(path)
    for key,value in env.items():
        if value and re.search(r'PASSWORD|TOKEN|SECRET|API_KEY',key,re.I) and len(value)>=6:
            secret_values.append(value)
    if env.get('DATABASE_URL'):
        try:
            password=make_url(env['DATABASE_URL']).password
            if password and len(password)>=6:
                secret_values.append(password)
        except Exception:
            raise SystemExit('Could not inspect local secret configuration safely; review required.')
patterns=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'sk-[A-Za-z0-9_-]{30,}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
for name in files:
    path=Path(name)
    prohibited=(path.name.startswith('.env') and path.name!='.env.example') or path.suffix.lower() in ('.pdf','.db','.sqlite3','.pem','.key','.pfx','.p12','.log','.bin','.dll','.obj')
    prohibited=prohibited or any(name.startswith(prefix) for prefix in ('data/','tmp/','output/','bousala/sources/','bousala/data/','bousala/quality/','bousala/vendor/','bousala/frontend/node_modules/','bousala/frontend/dist/'))
    prohibited=prohibited or (name.startswith('bousala/reports/') and name!='bousala/reports/KNOWN_GAPS.md')
    if prohibited:
        issues.append((name,'prohibited runtime/input/secret file'))
        continue
    raw=subprocess.check_output(['git','show',':'+name],cwd=root)
    text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8',errors='replace')
    if any(secret in text for secret in secret_values):
        issues.append((name,'matches a configured local secret'))
    if any(re.search(pattern,text) for pattern in patterns):
        issues.append((name,'credential signature detected'))
if issues:
    for name,reason in issues:
        print(name+': '+reason)
    raise SystemExit('Staged snapshot failed secret/data review.')
print(f'PASS: {len(files)} staged code/configuration files reviewed; no prohibited files or detected local secret values.')
