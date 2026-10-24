from contextlib import contextmanager
import psycopg2, psycopg2.extras
from shared.config import DATABASE_URL

@contextmanager
def conn():
    c = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()
