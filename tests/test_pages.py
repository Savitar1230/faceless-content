"""Pages, identities and the topic bank. Uses a temporary database and folder, never the real ones."""
import shutil
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import team

TMP = Path(tempfile.mkdtemp())
team.DB = TMP / "data" / "app.db"
import app as web
import books
import pages
import pipeline
import work

pipeline.VIDEOS = TMP / "videos"
pipeline.VIDEOS.mkdir()
ADMIN = team.setup()
pages.import_bank()


def signed_in(key):
    c = web.app.test_client()
    assert c.post("/login", data={"key": key}).status_code == 302
    return c


def person(admin, name):
    key = admin.post("/api/team", json={"name": name}).json["key"]
    return signed_in(key), next(p["id"] for p in admin.get("/api/team").json if p["name"] == name)


def add_page(admin, who, name, identity, voice="af_heart"):
    assert admin.post("/api/pages", json={"person": who, "name": name}).status_code == 200
    pid = max(x["id"] for x in pages.listing(who))
    assert admin.post(f"/api/pages/{pid}", json={"identity": identity, "voice": voice, "locked": True}).status_code == 200
    return pid


def start(client, pid, topic):
    return client.post("/api/videos", json={"topic": topic, "facts": "x", "page": pid})


def test_bank():
    assert pages.unused() == 47, "48 topics, T001 is used"
    pages.import_bank()
    assert pages.unused() == 47, "a restart changes nothing"
    assert pages.used("how bees make honey, and why bees dance to tell each other where flowers are")


def test_pages_and_identity():
    admin = signed_in(ADMIN)
    a, aid = person(admin, "Ana")
    b, bid = person(admin, "Ben")
    assert a.post("/api/pages", json={"person": aid, "name": "Mine"}).status_code == 403, "the admin adds pages"
    assert admin.post("/api/pages", json={"person": aid, "name": ""}).status_code == 400
    assert admin.post("/api/pages", json={"person": 999, "name": "Ghost"}).status_code == 400
    admin.post("/api/pages", json={"person": aid, "name": "Nature"})
    pid = pages.listing(aid)[0]["id"]

    # the person chooses the identity and voice, then locks them
    assert a.post(f"/api/pages/{pid}", json={"name": "Renamed"}).status_code == 403, "only the admin names a page"
    assert a.post(f"/api/pages/{pid}", json={"locked": True}).status_code == 400, "nothing to lock yet"
    assert a.post(f"/api/pages/{pid}", json={"identity": "Sam", "voice": "no_such"}).status_code == 400
    assert b.post(f"/api/pages/{pid}", json={"identity": "Sam"}).status_code == 404, "not Ben's page"
    assert b.get(f"/api/pages/{pid}/suggest").status_code == 404
    assert start(a, pid, pages.suggest(pid)[0]["topic"]).status_code == 400, "not locked yet"
    assert a.post(f"/api/pages/{pid}", json={"identity": "Sam", "voice": "am_michael", "locked": True}).status_code == 200
    assert a.post(f"/api/pages/{pid}", json={"identity": "Other"}).status_code == 400, "locked"
    assert a.post(f"/api/pages/{pid}", json={"locked": False}).status_code == 403
    assert admin.post(f"/api/pages/{pid}", json={"locked": False}).status_code == 200
    assert a.post(f"/api/pages/{pid}", json={"locked": True}).status_code == 200

    # one identity per page for a person, 10 pages at most
    admin.post("/api/pages", json={"person": aid, "name": "Second"})
    second = pages.listing(aid)[1]["id"]
    assert a.post(f"/api/pages/{second}", json={"identity": "sam"}).status_code == 400, "same identity, any case"
    assert a.post(f"/api/pages/{second}", json={"identity": "Noor"}).status_code == 200
    for n in range(8): assert admin.post("/api/pages", json={"person": aid, "name": f"P{n}"}).status_code == 200
    assert admin.post("/api/pages", json={"person": aid, "name": "Eleven"}).status_code == 400
    assert len(a.get("/api/pages").json["pages"]) == 10 and not b.get("/api/pages").json["pages"], "people see their own pages"


def test_suggest_and_use():
    admin = signed_in(ADMIN)
    c, cid = person(admin, "Cal")
    pid = add_page(admin, cid, "Science", "Mira", "bm_george")

    picks = c.get(f"/api/pages/{pid}/suggest").json
    assert len(picks) == 3 and len({t["category"] for t in picks}) == 3 and all(t["why"] for t in picks)
    more = c.get(f"/api/pages/{pid}/suggest?skip={','.join(t['id'] for t in picks)}").json
    assert not {t["id"] for t in more} & {t["id"] for t in picks}, "Suggest more shows new ones"

    # the video carries the page's identity and voice and belongs to the page's person
    pick = picks[0]
    slug = start(admin, pid, pick["topic"]).json["slug"]
    assert team.owner(slug) == cid
    args = work.write_args(slug)
    assert args["identity"] == "Mira" and args["voice_cfg"]["voice"] == "bm_george"
    assert pages.used(pick["topic"])

    # used means used, for this page, another page, a typed topic and a batch
    other, oid = person(admin, "Dee")
    page2 = add_page(admin, oid, "Other", "Lee")
    assert start(c, pid, pick["topic"]).status_code == 409
    assert start(other, page2, pick["topic"]).status_code == 409
    assert other.post("/api/videos", json={"topic": pick["topic"].upper(), "facts": "x"}).status_code == 409
    assert "Line 1" in admin.post("/api/batch", json={"rows": f"{pick['topic']} | x"}).json["error"]
    assert start(c, pid, "A topic of my own").status_code == 409, "a page takes bank topics only"

    # never the same category twice in a row on a page, and never a used topic
    assert all(t["category"] != pick["category"] and t["id"] != pick["id"] for _ in range(20) for t in pages.suggest(pid))
    same = team.sql("SELECT topic FROM topics WHERE category=? AND used_at IS NULL", pick["category"])[0]["topic"]
    assert start(c, pid, same).status_code == 409 and not pages.used(same)

    # two jobs at the same moment: one wins
    topic = pages.suggest(page2)[0]["topic"]
    won = []
    def race(job):
        try: pages.claim(topic, job, page2); won.append(job)
        except pages.Taken: pass
    runs = [threading.Thread(target=race, args=(f"race-{n}",)) for n in range(6)]
    for t in runs: t.start()
    for t in runs: t.join()
    assert len(won) == 1


def test_typed_topics_and_cancel():
    admin = signed_in(ADMIN)
    c, _ = person(admin, "Eli")
    r = c.post("/api/videos", json={"topic": "Why tractors let air out", "facts": "x"})
    assert r.status_code == 200
    assert c.post("/api/videos", json={"topic": "why tractors LET air out!", "facts": "x"}).status_code == 409, "typed topics never repeat"
    assert admin.post("/api/batch", json={"rows": "Fresh one | x\nfresh one | y"}).status_code == 400, "not twice in one batch"
    assert not pages.used("Fresh one"), "a bad batch queues nothing and uses nothing"

    # nothing made yet: the topic comes back, and the Dashboard stops counting the video
    team.sql("UPDATE queue SET state='waiting' WHERE job=?", r.json["slug"])
    assert c.post(f"/api/videos/{r.json['slug']}/delete", json={}).status_code == 200
    assert not team.sql("SELECT 1 FROM queue WHERE job=?", r.json["slug"])
    assert not pages.used("Why tractors let air out")
    assert not team.sql("SELECT 1 FROM topics WHERE plain=?", pages.plain("Why tractors let air out")), "a typed topic does not join the bank"

    # a voice was made: it stays used
    slug = c.post("/api/videos", json={"topic": "Made something", "facts": "x"}).json["slug"]
    (pipeline.VIDEOS / slug / "takes").mkdir()
    c.post(f"/api/videos/{slug}/delete", json={})
    assert pages.used("Made something") and not (pipeline.VIDEOS / slug).exists()


def test_bank_topic_returns():
    admin = signed_in(ADMIN)
    c, cid = person(admin, "Fay")
    pid = add_page(admin, cid, "Food", "Rae")
    pick = pages.suggest(pid)[0]
    slug = start(c, pid, pick["topic"]).json["slug"]
    assert c.post(f"/api/videos/{slug}/delete", json={}).status_code == 200
    assert not pages.used(pick["topic"]) and not pages.last_category(pid), "the page forgets a cancelled topic too"
    assert pick["id"] in [t["id"] for t in team.sql("SELECT id FROM topics WHERE used_at IS NULL")]


def test_locked_voice_in_script():
    admin = signed_in(ADMIN)
    c, cid = person(admin, "Gul")
    pid = add_page(admin, cid, "History", "Omar", "af_bella")
    slug = start(c, pid, pages.suggest(pid)[0]["topic"]).json["slug"]
    spec = dict(slug=slug, identity="Omar", voice=dict(pipeline.VOICE, voice="af_bella"), blocks=[])
    pipeline.write(pipeline.VIDEOS / slug / "spec.json", spec)
    saved = c.post(f"/api/videos/{slug}/spec", json=dict(spec, voice=dict(pipeline.VOICE, voice="af_heart"), identity="Someone else")).json
    assert saved["voice"]["voice"] == "af_bella" and saved["identity"] == "Omar"

    # the prompt tells the writer who is speaking
    prompts = []
    class Writer:
        def safe_run(self, inputs):
            prompts.append(inputs["prompt"])
            return dict(ok=True, text="{}")
    old, pipeline.plugin_for = pipeline.plugin_for, lambda name: Writer()
    pipeline.write_spec(slug, **work.write_args(slug))
    pipeline.plugin_for = old
    assert "one narrator: Omar" in prompts[0] and pipeline.read(pipeline.VIDEOS / slug / "spec.json")["voice"]["voice"] == "af_bella"


def test_low_bank():
    admin = signed_in(ADMIN)
    c, _ = person(admin, "Hal")
    assert c.post("/api/topics", json={"rows": "A | B"}).status_code == 403
    assert not any("unused topics" in w for w in admin.get("/api/dashboard").json["warnings"])
    team.sql("UPDATE topics SET used_at=1 WHERE id NOT IN ('T002','T003')")
    assert any("Only 2 unused" in w for w in admin.get("/api/dashboard").json["warnings"])
    used = team.sql("SELECT topic FROM topics WHERE id='T005'")[0]["topic"]
    r = admin.post("/api/topics", json={"rows": f"Space | Why Mars is red | Rust on a planet\nScience | {used}\nno topic here\n\nSpace | why mars is RED"}).json
    assert r == dict(added=1, skipped=3), r
    assert "added 1 topics" in str(team.sql("SELECT action FROM audit"))
    assert pages.unused() == 3


if __name__ == "__main__":
    test_bank()
    test_pages_and_identity()
    test_suggest_and_use()
    test_typed_topics_and_cancel()
    test_bank_topic_returns()
    test_locked_voice_in_script()
    test_low_bank()
    shutil.rmtree(TMP, ignore_errors=True)
    print("ALL PAGES TESTS PASSED")
