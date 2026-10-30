"""People and keys. A key is a login for this app only: it never signs anyone in to Flow or Muse.
Only a key's SHA-256 is stored and the plain key is shown once. Every request checks the database, so revoking is instant.
Lost the admin key? Run `python team.py` on the host to print a new one.
"""
import hashlib
import secrets
import sqlite3
import time
from pathlib import Path

DB = Path(__file__).parent / "data" / "app.db"
DAY = 86400
KEY_DAYS = 30
WRONG_LIMIT, PAUSE = 5, 60  # after 5 wrong keys in a row, login rests for a minute
wrong = {"count": 0, "until": 0}
SCHEMA = """
CREATE TABLE IF NOT EXISTS people (id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
                                   flow INTEGER NOT NULL DEFAULT 0, muse INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS keys (hash TEXT PRIMARY KEY, person INTEGER NOT NULL REFERENCES people(id), expires REAL,
                                 revoked INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, owner INTEGER NOT NULL REFERENCES people(id), created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY, job TEXT NOT NULL, line TEXT NOT NULL, args TEXT NOT NULL,
                                  state TEXT NOT NULL DEFAULT 'queued', created REAL NOT NULL, started REAL, ended REAL);
CREATE TABLE IF NOT EXISTS paused (job TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS templates (id INTEGER PRIMARY KEY, name TEXT NOT NULL, owner INTEGER NOT NULL REFERENCES people(id),
                                      format TEXT NOT NULL, ratios TEXT NOT NULL, writer TEXT NOT NULL, facts TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY, provider TEXT NOT NULL, label TEXT NOT NULL, person INTEGER NOT NULL REFERENCES people(id),
                                     is_default INTEGER NOT NULL DEFAULT 0, helps INTEGER NOT NULL DEFAULT 0, real_left REAL, real_at REAL,
                                     UNIQUE (provider, person));
CREATE TABLE IF NOT EXISTS spend (id INTEGER PRIMARY KEY, account INTEGER NOT NULL REFERENCES accounts(id), job TEXT NOT NULL, card TEXT NOT NULL,
                                  credits REAL NOT NULL, at REAL NOT NULL, UNIQUE (job, card));
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, at REAL NOT NULL, who TEXT NOT NULL, action TEXT NOT NULL, job TEXT, account TEXT, credits REAL);
CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def sql(query, *args):
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        with c:
            return [dict(r) for r in c.execute(query, args)]
    finally:
        c.close()


def digest(key): return hashlib.sha256(key.encode()).hexdigest()


def setup():
    """Creates the tables. The very first time it also makes the admin and returns the admin key, once."""
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.executescript(SCHEMA)
    c.close()
    if not sql("SELECT 1 FROM people WHERE role='admin'"):
        return new_key(add("Admin", "admin", 1, 1), None)


def secret():
    """Signs the login cookie. Made once and kept on this PC."""
    DB.parent.mkdir(exist_ok=True)
    f = DB.with_name("secret.key")
    if not f.exists(): f.write_bytes(secrets.token_bytes(32))
    return f.read_bytes()


def add(name, role="teammate", flow=0, muse=0):
    return sql("INSERT INTO people (name, role, flow, muse, created) VALUES (?,?,?,?,?) RETURNING id", name, role, flow, muse, time.time())[0]["id"]


def revoke(person): sql("UPDATE keys SET revoked=1 WHERE person=?", person)


def new_key(person, days=KEY_DAYS):
    """One live key per person: a new key ends the old one. days=None means it never ends."""
    revoke(person)
    key = secrets.token_urlsafe(32)
    sql("INSERT INTO keys (hash, person, expires, created) VALUES (?,?,?,?)", digest(key), person, days and time.time() + days * DAY, time.time())
    return key


def who(key_hash):
    rows = sql("""SELECT p.* FROM keys k JOIN people p ON p.id = k.person
                  WHERE k.hash=? AND k.revoked=0 AND (k.expires IS NULL OR k.expires>?) AND p.status='active'""", key_hash, time.time())
    return rows[0] if rows else None


def login(key):
    """Returns the key's hash if it works. Wrong, expired and revoked keys all look the same from outside."""
    if time.time() < wrong["until"]: return None
    h = digest(key)
    if who(h):
        wrong["count"] = 0
        return h
    wrong["count"] += 1
    if wrong["count"] >= WRONG_LIMIT:
        wrong.update(count=0, until=time.time() + PAUSE)
    return None


def people():
    return sql("""SELECT p.id, p.name, p.role, p.status, p.flow, p.muse,
                         (SELECT k.expires FROM keys k WHERE k.person=p.id AND k.revoked=0) AS expires,
                         EXISTS(SELECT 1 FROM keys k WHERE k.person=p.id AND k.revoked=0) AS has_key
                  FROM people p WHERE p.status != 'removed' ORDER BY p.id""")


def editable(person):
    """The admin's own row can never be paused, removed or re-keyed from the panel."""
    rows = sql("SELECT * FROM people WHERE id=? AND role != 'admin' AND status != 'removed'", person)
    return rows[0] if rows else None


def change(person, flow=None, muse=None, status=None):
    if flow is not None: sql("UPDATE people SET flow=? WHERE id=?", int(flow), person)
    if muse is not None: sql("UPDATE people SET muse=? WHERE id=?", int(muse), person)
    if status: sql("UPDATE people SET status=? WHERE id=?", status, person)
    if status == "removed": revoke(person)


def new_job(job, owner): sql("INSERT INTO jobs (id, owner, created) VALUES (?,?,?)", job, owner, time.time())


def owner(job):
    rows = sql("SELECT owner FROM jobs WHERE id=?", job)
    return rows[0]["owner"] if rows else None  # older videos have no owner, so only the admin sees them


def job_info(job):
    rows = sql("SELECT p.name, j.created FROM jobs j JOIN people p ON p.id = j.owner WHERE j.id=?", job)
    return rows[0] if rows else None


if __name__ == "__main__":
    setup()
    print("New admin key, the old one has stopped working:\n" + new_key(sql("SELECT id FROM people WHERE role='admin'")[0]["id"], None))
