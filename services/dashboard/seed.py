"""Creates demo users and applies row-level-security style roles. Run once after schema init."""
from shared.db import conn
from .app.auth import hash_pw

USERS = [("officer1", "officer123", "OFFICER"), ("admin", "admin123", "ADMIN"), ("inst-APP-1001", "inst123", "INSTITUTION")]
with conn() as c:
    cur = c.cursor()
    for u, p, r in USERS:
        cur.execute("INSERT INTO users(username,password_hash,role) VALUES(%s,%s,%s) ON CONFLICT (username) DO NOTHING", (u, hash_pw(p), r))
print("seeded")
