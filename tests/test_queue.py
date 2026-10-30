"""The saved queue, batches, pause and templates. Uses a temporary database and folder, never the real ones."""
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import team

TMP = Path(tempfile.mkdtemp())
team.DB = TMP / "data" / "app.db"
import app as web
import pipeline
import work

pipeline.VIDEOS = TMP / "videos"
pipeline.VIDEOS.mkdir()
ADMIN = team.setup()


def signed_in(key):
    c = web.app.test_client()
    assert c.post("/login", data={"key": key}).status_code == 302
    return c


def wipe():
    team.sql("DELETE FROM queue")
    team.sql("DELETE FROM paused")


def states(): return [r["state"] for r in team.sql("SELECT state FROM queue ORDER BY id")]


def test_order_and_limit():
    """A real 12 task batch through real workers: in order, within the limit, each ending with a state."""
    wipe()
    jobs = [f"job-{i}" for i in range(12)]
    for j in jobs: work.add(j, "make")
    work.add("write-1", "write")
    ran, now, peak, lock = [], {"make": 0, "write": 0}, {"make": 0, "write": 0}, threading.Lock()

    def do(task):
        with lock:
            now[task["line"]] += 1
            peak[task["line"]] = max(peak[task["line"]], now[task["line"]])
            ran.append(task["job"])
        time.sleep(.05)
        with lock: now[task["line"]] -= 1
        return "failed" if task["job"] == "job-3" else "done"

    work.REST = .01
    work.start(do)
    end = time.time() + 20
    while time.time() < end and any(s in ("queued", "running") for s in states()): time.sleep(.05)
    assert [j for j in ran if j.startswith("job")] == jobs, "the line must keep order"
    assert peak == {"make": 1, "write": 1}, peak
    assert states().count("failed") == 1 and states().count("done") == 12


def test_pause():
    wipe()
    work.add("a", "make")
    work.add("b", "make")
    work.pause("a")
    assert work.claim("make")["job"] == "b", "a paused video is skipped, not lost"
    work.pause("a", False)
    work.pause()
    assert work.claim("make") is None, "pausing the queue stops everything"
    assert "a" in {r["job"] for r in team.sql("SELECT job FROM queue WHERE state='queued'")}
    work.pause(on=False)
    assert work.claim("make")["job"] == "a"
    wipe()


def test_restart():
    wipe()
    work.add("running", "make")
    work.add("queued", "make")
    work.claim("make")
    work.recover()
    assert states() == ["failed", "queued"], "a restart keeps queued work and marks what was running"
    assert not work.live("running") and work.live("queued")
    wipe()


def test_owner_status():
    wipe()
    admin = signed_in(ADMIN)
    key = admin.post("/api/team", json={"name": "Asha", "flow": True}).json["key"]
    pid = next(p["id"] for p in admin.get("/api/team").json if p["name"] == "Asha")
    a = signed_in(key)
    slug = a.post("/api/videos", json={"topic": "Paused owner", "facts": "x"}).json["slug"]
    admin.post(f"/api/team/{pid}", json={"status": "paused"})
    assert work.claim("write") is None, "a paused person's work waits"
    admin.post(f"/api/team/{pid}", json={"status": "active"})
    admin.post(f"/api/team/{pid}", json={"status": "removed"})
    assert states() == ["failed"]
    st = pipeline.read(pipeline.VIDEOS / slug / "status.json")
    assert st["state"] == "failed" and "owner was removed" in st["message"]
    wipe()


def test_batch():
    wipe()
    admin = signed_in(ADMIN)
    key = admin.post("/api/team", json={"name": "Bilal", "flow": True}).json["key"]
    b = signed_in(key)

    bad = admin.post("/api/batch", json={"rows": "Good | fact\n | no topic\nNo facts\nFine | fact | | Nobody"})
    assert bad.status_code == 400 and all(f"Line {n}" in bad.json["error"] for n in (2, 3, 4))
    assert states() == [], "one bad line queues nothing"
    assert admin.post("/api/batch", json={"rows": ""}).status_code == 400
    assert admin.post("/api/batch", json={"rows": "t | f\n" * (web.MAX_BATCH + 1)}).status_code == 400
    assert b.post("/api/batch", json={"rows": "t | f | | Admin"}).status_code == 400, "only the admin sets owners"

    rows = "Same topic | fact one | https://a.example https://b.example\n\nSame topic | fact two | | bilal"
    slugs = admin.post("/api/batch", json={"rows": rows, "facts": "Shared fact.", "format": "long", "ratios": ["16x9"]}).json["slugs"]
    assert len(set(slugs)) == 2 and states() == ["queued", "queued"]
    args = work.write_args(slugs[0])
    assert args["facts"] == "Shared fact.\nfact one" and args["sources"] == ["https://a.example", "https://b.example"]
    assert args["fmt"] == "long" and args["ratios"] == ["16x9"]
    assert [v["slug"] for v in b.get("/api/videos").json] == [slugs[1]], "each line has its own owner"
    wipe()


def test_templates():
    admin = signed_in(ADMIN)
    key = admin.post("/api/team", json={"name": "Dua"}).json["key"]
    d = signed_in(key)
    assert d.post("/api/templates", json={"name": " "}).status_code == 400
    d.post("/api/templates", json={"name": "Farm", "format": "long", "ratios": ["9x16", "3x4"], "writer": "ollama_writer", "facts": "Always farm."})
    t = admin.get("/api/templates").json[0]
    assert (t["name"], t["format"], t["ratios"]) == ("Farm", "long", "9x16,3x4"), "the whole team can read a template"
    other = signed_in(admin.post("/api/team", json={"name": "Eman"}).json["key"])
    other.post(f"/api/templates/{t['id']}/delete", json={})
    assert admin.get("/api/templates").json, "only the owner or admin can delete a template"
    d.post(f"/api/templates/{t['id']}/delete", json={})
    assert not admin.get("/api/templates").json


def test_run_rules():
    wipe()
    admin = signed_in(ADMIN)
    slug = admin.post("/api/videos", json={"topic": "Double click", "facts": "x"}).json["slug"]
    assert states() == ["queued"]
    admin.post(f"/api/videos/{slug}/run", json={})
    assert states() == ["queued"], "a second click must not queue it twice"

    # a script that never got written runs the writer again instead of failing the script check
    task = work.claim("write")
    work.finish(task, "failed")
    admin.post(f"/api/videos/{slug}/run", json={})
    assert team.sql("SELECT line FROM queue WHERE state='queued'") == [{"line": "write"}]

    assert admin.post(f"/api/videos/{slug}/delete", json={}).status_code == 200
    assert not work.live(slug), "deleting a queued video takes it out of the queue"

    # approve all skips anything that fails the script check
    slug = admin.post("/api/videos", json={"topic": "Bad script", "facts": "x"}).json["slug"]
    wipe()
    s = pipeline.read(pipeline.VIDEOS / slug / "spec.json")
    pipeline.write(pipeline.VIDEOS / slug / "spec.json", dict(s, blocks=[{"line": "Too short.", "scenes": []}], ratios=["9x16"]))
    assert admin.post("/api/approve-all", json={}).json["approved"] == 0 and states() == []

    # an unexpected crash gives a plain reason, with the details kept for the admin
    pipeline.write(pipeline.VIDEOS / "crash" / "spec.json", {"slug": "crash"})
    real, pipeline.gate.check = pipeline.gate.check, lambda s: 1 / 0
    st = pipeline.run("crash")
    pipeline.gate.check = real
    assert st["state"] == "failed" and "Traceback" not in st["message"] and (pipeline.VIDEOS / "crash" / "error.txt").exists()


if __name__ == "__main__":
    test_pause()
    test_restart()
    test_owner_status()
    test_batch()
    test_templates()
    test_run_rules()
    test_order_and_limit()
    shutil.rmtree(TMP, ignore_errors=True)
    print("ALL QUEUE TESTS PASSED")
