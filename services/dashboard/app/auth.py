import datetime as dt
import jwt
from passlib.hash import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from shared.config import JWT_SECRET

bearer = HTTPBearer(auto_error=False)
ROLES = ("INSTITUTION", "OFFICER", "ADMIN")

def hash_pw(p): return bcrypt.hash(p)
def verify_pw(p, h): return bcrypt.verify(p, h)

def make_token(username: str, role: str) -> str:
    return jwt.encode({"sub": username, "role": role, "exp": dt.datetime.utcnow() + dt.timedelta(hours=8)},
                      JWT_SECRET, algorithm="HS256")

def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if not cred:
        raise HTTPException(401, "Missing token")
    try:
        return jwt.decode(cred.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")

def require(*roles):
    def dep(u: dict = Depends(current_user)):
        if u["role"] not in roles:
            raise HTTPException(403, "Insufficient role")
        return u
    return dep
