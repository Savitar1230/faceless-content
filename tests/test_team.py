"""Login, keys and who can see what. Uses a temporary database and folder, never the real ones."""
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import team

TMP = Path(tempfile.mkdtemp())
team.DB = TMP / "data" / "app.db"
import app as web
import pipeline
import scenes
import spec as gate

pipeline.VIDEOS = TMP / "videos"
SECRET_WORDS = "That key did not work."  # the queue's workers are not started, so tasks here only wait


def signed_in(key):
    c = web.app.test_client()
    r = c.post("/login", data={"key": key})
    assert r.status_code == 302, "a good key should sign in"
    return c


def rejected(key):
    r = web.app.test_client().post("/login", data={"key": key})
    return r.status_code == 200 and SECRET_WORDS in r.text


def video(client, topic):
    r = client.post("/api/videos", json={"topic": topic, "facts": "x"})
    assert r.status_code == 200, r.text
    return r.json["slug"]


def make_admin():
    first = team.setup()
    assert first and team.setup() is None, "the admin key is made once"
    assert first.encode() not in team.DB.read_bytes(), "keys are stored hashed"
    return first


def test_every_route_needs_a_key(admin_key):
    anon = web.app.test_client()
    for rule in web.app.url_map.iter_rules():
        if rule.endpoint in ("login", "static"): continue
        url = rule.rule.replace("<slug>", "x").replace("<cid>", "x").replace("<path:name>", "x").replace("<plugin>", "x").replace("<int:pid>", "1")
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            assert anon.open(url, method=method).status_code in (302, 401), f"{method} {url} is open"


def test_keys(admin):
    alice = admin.post("/api/team", json={"name": "Alice", "flow": True}).json["key"]
    assert not rejected(alice)
    assert rejected("wrong")

    pid = next(p["id"] for p in admin.get("/api/team").json if p["name"] == "Alice")
    session = signed_in(alice)
    assert session.get("/api/me").json["name"] == "Alice"

    # expired, then revoked, then paused, then removed: each stops the live session at once
    team.sql("UPDATE keys SET expires=? WHERE person=?", time.time() - 1, pid)
    assert session.get("/api/videos").status_code == 401 and rejected(alice)
    alice = admin.post(f"/api/team/{pid}", json={"new_key": True}).json["key"]
    session = signed_in(alice)
    admin.post(f"/api/team/{pid}", json={"revoke": True})
    assert session.get("/api/videos").status_code == 401 and rejected(alice)
    alice = admin.post(f"/api/team/{pid}", json={"new_key": True}).json["key"]
    session = signed_in(alice)
    admin.post(f"/api/team/{pid}", json={"status": "paused"})
    assert session.get("/api/videos").status_code == 401
    admin.post(f"/api/team/{pid}", json={"status": "active"})
    assert session.get("/api/videos").status_code == 200
    admin.post(f"/api/team/{pid}", json={"status": "removed"})
    assert session.get("/api/videos").status_code == 401 and rejected(alice)
    assert admin.post(f"/api/team/{pid}", json={"new_key": True}).status_code == 404, "a removed person cannot be re-keyed"

    admin_row = next(p["id"] for p in admin.get("/api/team").json if p["role"] == "admin")
    assert admin.post(f"/api/team/{admin_row}", json={"status": "removed"}).status_code == 404


def test_lockout():
    for _ in range(team.WRONG_LIMIT): team.login("wrong")
    assert team.wrong["until"] > time.time()
    team.wrong.update(count=0, until=0)


def test_owners(admin):
    a = signed_in(admin.post("/api/team", json={"name": "A", "flow": True}).json["key"])
    b = signed_in(admin.post("/api/team", json={"name": "B"}).json["key"])
    one, two = video(a, "First topic"), video(b, "Second topic")
    assert [v["slug"] for v in a.get("/api/videos").json] == [one]
    assert b.get(f"/api/videos/{one}/spec").status_code == 404
    assert b.post(f"/api/videos/{one}/run", json={}).status_code == 404
    assert b.post(f"/api/videos/{one}/delete", json={}).status_code == 404
    assert b.get(f"/files/{one}/x.mp4").status_code == 404
    assert {two, one} <= {v["slug"] for v in admin.get("/api/videos").json}, "the admin sees everything"
    assert a.get("/api/team").status_code == 403 and a.post("/api/accounts/flow_image", json={"label": "x"}).status_code == 403
    assert a.post("/api/videos", json={"topic": "t", "facts": "x", "writer": "claude_writer"}).status_code == 400

    # a saved file cannot approve a script, take a video or rename it
    s = a.get(f"/api/videos/{one}/spec").json
    assert a.post(f"/api/videos/{one}/spec", json=dict(s, approved=True, slug="other")).json["approved"] is False
    assert a.get(f"/api/videos/{one}/spec").json["slug"] == one

    # Flow access comes from the admin's tick
    s = dict(s, pictures={"pic": {"image": "a calf"}})
    b.post(f"/api/videos/{two}/spec", json=dict(s, slug=two))
    assert b.post(f"/api/videos/{two}/approve", json={}).status_code == 403
    assert b.get(f"/api/videos/{two}/spec").json["approved"] is False
    a.post(f"/api/videos/{one}/spec", json=s)
    assert a.post(f"/api/videos/{one}/approve", json={}).status_code == 200
    changed = a.post(f"/api/videos/{one}/spec", json=dict(s, approved=True, facts="new")).json
    assert changed["approved"] is False, "a changed script needs approving again"


def test_assistant(admin):
    key = admin.post("/api/team", json={"name": "Assistant", "assistant": True}).json["key"]
    assert admin.post("/api/team", json={"name": "Again", "assistant": True}).status_code == 409
    h = {"Authorization": f"Bearer {key}"}
    c = web.app.test_client()
    slug = c.post("/api/videos", json={"topic": "From Muse", "facts": "x"}, headers=h).json["slug"]
    assert c.get("/api/videos", headers=h).status_code == 200
    assert c.post(f"/api/videos/{slug}/approve", json={}, headers=h).status_code == 403
    assert c.post("/api/team", json={"name": "x"}, headers=h).status_code == 403, "the assistant cannot make keys"
    assert c.get("/api/videos", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_hostile_scripts():
    good = {"blocks": [], "ratios": ["9x16"]}
    for change, word in (({"pictures": {"../../data/accounts": {}}}, "picture names"), ({"style": "../x"}, "style"),
                         ({"ratios": ["../x"]}, "sizes"), ({"voice": "x"}, "voice"),
                         ({"blocks": [{"line": "x", "scenes": [{"type": "number", "value": "1); fetch('/x"}]}]}, "value")):
        assert any(word in b for b in gate.shape(dict(good, **change))), word

    job = TMP / "videos" / "hostile"
    job.mkdir(parents=True)
    for path in ("data/app.db", "../outside.png", "videos/other/out/x.mp4"):
        try:
            pipeline.pictures(job, {"pictures": {"p": {"file": path}}, "ratios": ["9x16"]}, [], [])
            raise AssertionError(f"{path} should be refused")
        except pipeline.Blocked:
            pass

    evil = "<script>fetch('http://127.0.0.1:8901')</script>"
    spec = {"blocks": [{"line": "x", "scenes": [{"type": "text", "title": [evil], "sub": evil, "dur": 5}, {"type": "compare", "left": evil, "right": evil, "dur": 5}]}]}
    html = scenes.Page(spec, "9x16", dict(head="h", body="b", paper="#fff", ink="#000", accent="#f00", second="#0f0")).build({}, [dict(w=evil, s=0, e=1)])
    assert "fetch('http" in html and "<script>fetch" not in html, "script text must stay text"


if __name__ == "__main__":
    key = make_admin()
    admin = signed_in(key)
    test_every_route_needs_a_key(key)
    test_keys(admin)
    test_lockout()
    test_owners(admin)
    test_assistant(admin)
    test_hostile_scripts()
    shutil.rmtree(TMP, ignore_errors=True)
    print("ALL TEAM TESTS PASSED")
