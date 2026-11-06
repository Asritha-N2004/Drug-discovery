import os, secrets, time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from .database import get_db
from .models import User, Role

SECRET = os.getenv('JWT_SECRET') or secrets.token_hex(32)
if os.getenv('APP_ENV') == 'production' and (not os.getenv('JWT_SECRET') or len(SECRET) < 32):
    raise RuntimeError('Production requires JWT_SECRET of at least 32 characters')
bearer = HTTPBearer()
attempts = defaultdict(list)

def hash_password(value):
    return bcrypt.hashpw(value.encode(), bcrypt.gensalt()).decode()

def token_for(user):
    return jwt.encode({'sub': str(user.id), 'exp': datetime.now(timezone.utc) + timedelta(hours=8)}, SECRET, algorithm='HS256')

def decode_token(token):
    try:
        return int(jwt.decode(token, SECRET, algorithms=['HS256'])['sub'])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, 'Invalid or expired session')

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(get_db)):
    user = db.get(User, decode_token(credentials.credentials))
    if not user or not user.active:
        raise HTTPException(401, 'User unavailable')
    return user

def require(*roles):
    def check(user=Depends(current_user), db=Depends(get_db)):
        if db.get(Role, user.role_id).name not in roles:
            raise HTTPException(403, 'Your role cannot perform this action')
        return user
    return check

managers = require('Administrator', 'Inventory Manager')
operators = require('Administrator', 'Inventory Manager', 'Warehouse Manager')

def throttle(key):
    current = time.monotonic()
    attempts[key] = [t for t in attempts[key] if current-t < 60]
    if len(attempts[key]) >= 10:
        raise HTTPException(429, 'Too many attempts. Retry in one minute.')
    attempts[key].append(current)
