"""Pages and the topic bank. Each page has one locked identity and voice, and a topic is used once across the whole app.
topics.json starts the bank. After that the database is the truth.
"""
import json
import re
import secrets
import time
from pathlib import Path

import team

BANK = Path(__file__).parent / "topics.json"
MAX_PAGES = 10
LOW_TOPICS = 10  # under this the Dashboard asks for new topics
TYPED = ""  # the category of a topic typed by hand, which was never in the bank
VOICES = ("af_heart", "af_bella", "af_sarah", "am_michael", "bm_george")  # timed: these fit the 7.8-9.5 s a block needs at speed 0.8; time a voice before adding it


class Taken(Exception): pass  # the topic cannot be used, and the message says why


def plain(text): return " ".join(re.findall(r"\w+", text.lower()))


def import_bank(path=BANK):
    """Safe on every start: a topic already here keeps its state."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for t in data["topic_bank"]:
        team.sql("INSERT OR IGNORE INTO topics (id, category, topic, why, plain, used_at) VALUES (?,?,?,?,?,?)", t["id"], t["category"], t["topic"],
                 t["why_interesting"], plain(t["topic"]), time.time() if t["id"] in data["used_topics"] else None)


def add(person, name):
    if not name: return "Give the page a name."
    if not team.sql("SELECT 1 FROM people WHERE id=? AND role != 'assistant' AND status != 'removed'", person): return "Pick a person."
    if len(listing(person)) >= MAX_PAGES: return f"A person can manage {MAX_PAGES} pages."
    team.sql("INSERT INTO pages (person, name) VALUES (?,?)", person, name)


def page(pid):
    rows = team.sql("SELECT * FROM pages WHERE id=?", pid)
    return rows[0] if rows else None


def listing(person=None):
    """Everyone's pages, or just one person's."""
    return team.sql("""SELECT x.*, p.name AS owner, (SELECT COUNT(*) FROM topics t WHERE t.page=x.id) AS used
                       FROM pages x JOIN people p ON p.id = x.person
                       WHERE p.status != 'removed' AND (? IS NULL OR x.person=?) ORDER BY x.person, x.id""", person, person)


def save(x, b):
    """Returns a problem, or None when saved."""
    name, identity, voice = [str(b.get(k, x[k])).strip() for k in ("name", "identity", "voice")]
    locked = bool(b.get("locked", x["locked"]))
    if x["locked"] and (identity != x["identity"] or voice != x["voice"]): return "This identity is locked. The admin can unlock it."
    if not name: return "Give the page a name."
    if voice and voice not in VOICES: return "Pick a voice from the list."
    if identity and team.sql("SELECT 1 FROM pages WHERE person=? AND id != ? AND lower(identity)=lower(?)", x["person"], x["id"], identity):
        return "Each page needs its own identity. Another of this person's pages has that one."
    if locked and not (identity and voice): return "Choose the identity and the voice before locking."
    team.sql("UPDATE pages SET name=?, identity=?, voice=?, locked=? WHERE id=?", name, identity, voice, int(locked), x["id"])


def last_category(pid):
    rows = team.sql("SELECT category FROM topics WHERE page=? ORDER BY used_at DESC LIMIT 1", pid)
    return rows[0]["category"] if rows else None


def suggest(pid, skip=()):
    """Three unused topics, each from a different category where possible, never the category this page used last."""
    rows = [t for t in team.sql("SELECT id, category, topic, why FROM topics WHERE used_at IS NULL AND category IS NOT ? ORDER BY RANDOM()", last_category(pid)) if t["id"] not in skip]
    one_each = list({t["category"]: t for t in rows}.values())
    return (one_each + [t for t in rows if t not in one_each])[:3]


def claim(text, job, pid=None):
    """Marks a topic used before anything is made. One statement, so two jobs cannot both win.
    A page takes bank topics only. A typed topic joins the table as used, so it can never repeat either."""
    key = plain(text)
    if not pid: team.sql("INSERT OR IGNORE INTO topics (id, category, topic, plain) VALUES (?,?,?,?)", job, TYPED, text, key)
    if team.sql("UPDATE topics SET job=?, page=?, used_at=? WHERE plain=? AND used_at IS NULL AND category IS NOT ? RETURNING id",
                job, pid, time.time(), key, last_category(pid)): return
    rows = team.sql("SELECT used_at FROM topics WHERE plain=?", key)
    if not rows: raise Taken("Pick one of the suggested topics.")
    raise Taken("That topic has been used already. Pick another." if rows[0]["used_at"] else "This page used that category last. Pick another topic.")


def used(text): return bool(team.sql("SELECT 1 FROM topics WHERE plain=? AND used_at IS NOT NULL", plain(text)))


def release(job):
    """Gives a cancelled video's topic back. Only for a video nothing was made from."""
    team.sql("DELETE FROM topics WHERE job=? AND category=?", job, TYPED)
    team.sql("UPDATE topics SET job=NULL, page=NULL, used_at=NULL WHERE job=?", job)


def add_topics(text):
    """Reads category | topic | why, one a line. A topic with the same wording as one already here, used or not, is skipped."""
    added = skipped = 0
    for line in text.splitlines():
        if not line.strip(): continue
        category, topic, why = ([c.strip() for c in line.split("|")] + ["", ""])[:3]
        fresh = category and topic and team.sql("INSERT OR IGNORE INTO topics (id, category, topic, why, plain) VALUES (?,?,?,?,?) RETURNING id",
                                                f"N{secrets.token_hex(3)}", category, topic, why, plain(topic))
        added, skipped = added + bool(fresh), skipped + (not fresh)
    return added, skipped


def unused(): return team.sql("SELECT COUNT(*) AS n FROM topics WHERE used_at IS NULL")[0]["n"]
