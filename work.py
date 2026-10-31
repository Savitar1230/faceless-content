"""The saved queue. Work lives in the database, so a restart loses nothing.
Each line takes its tasks in order. Nothing retries by itself, so a failure cannot burn credits.
"""
import json
import threading
import time
import traceback

import books
import team

# Workers per line. 2 renders at once were no faster than 1 after the other and used more RAM (measured 2026-10-30).
LIMITS = {"write": 1, "make": 1}
REST = 1  # seconds between looks at an empty line
ALL = "*"  # the paused row that holds the whole queue


def add(job, line, args=None):
    team.sql("INSERT INTO queue (job, line, args, created) VALUES (?,?,?,?)", job, line, json.dumps(args or {}), time.time())


def live(job): return bool(team.sql("SELECT 1 FROM queue WHERE job=? AND state IN ('queued','running')", job))


def write_args(job):
    """What the script was last asked for, so a failed writing task can run again."""
    rows = team.sql("SELECT args FROM queue WHERE job=? AND line='write' ORDER BY id DESC LIMIT 1", job)
    return json.loads(rows[0]["args"]) if rows else None


def claim(line):
    """Takes the oldest task that may run. Paused videos, and videos of a paused owner, wait their turn."""
    rows = team.sql("""UPDATE queue SET state='running', started=? WHERE id = (
                         SELECT q.id FROM queue q LEFT JOIN jobs j ON j.id = q.job LEFT JOIN people o ON o.id = j.owner
                         WHERE q.line=? AND q.state='queued' AND (o.status IS NULL OR o.status='active')
                           AND NOT EXISTS (SELECT 1 FROM paused x WHERE x.job IN (q.job, ?))
                           AND (? OR IFNULL(json_extract(q.args, '$.writer'), '') != 'ollama_writer')
                         ORDER BY q.id LIMIT 1) RETURNING *""", time.time(), line, ALL, books.ollama_hour())
    return rows[0] if rows else None


def finish(task, state): team.sql("UPDATE queue SET state=?, ended=? WHERE id=?", state, time.time(), task["id"])


def recover():
    """A task that was running when the app closed did not finish. Queued tasks simply stay queued."""
    team.sql("UPDATE queue SET state='failed', ended=? WHERE state='running'", time.time())


def drop_owner(person):
    """Ends a removed person's waiting tasks and returns their videos."""
    return [r["job"] for r in team.sql("""UPDATE queue SET state='failed', ended=? WHERE state='queued'
                                          AND job IN (SELECT id FROM jobs WHERE owner=?) RETURNING job""", time.time(), person)]


def forget(job):
    team.sql("DELETE FROM queue WHERE job=? AND state != 'running'", job)  # a deleted video must not stay in the Dashboard counts
    team.sql("DELETE FROM paused WHERE job=?", job)


def pause(job=ALL, on=True):
    team.sql("INSERT OR IGNORE INTO paused (job) VALUES (?)" if on else "DELETE FROM paused WHERE job=?", job)


def paused(): return {r["job"] for r in team.sql("SELECT job FROM paused")}


def worker(line, do):
    while True:
        try:
            task = claim(line)
            if task: finish(task, do(task))
            else: time.sleep(REST)
        except Exception:  # one bad task must not stop the line
            traceback.print_exc()
            time.sleep(REST)


def start(do):
    """do(task) runs one task and returns how it ended: done, waiting or failed."""
    for line, n in LIMITS.items():
        for _ in range(n):
            threading.Thread(target=worker, args=(line, do), daemon=True).start()
