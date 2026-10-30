"""Card inbox, credits, hand-over, audit, downloads, cleanup and reuse. Uses a temporary database and folder, never the real ones."""
import json
import os
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
import books
import pipeline
import work

pipeline.VIDEOS = TMP / "videos"
pipeline.VIDEOS.mkdir()
pipeline.LIBRARY = TMP / "library"
ADMIN = team.setup()
PNG = b"\x89PNG\r\n\x1a\n fake"
SPEC = {"title": "Calf", "facts": "x", "ratios": ["9x16"], "pictures": {"pic": {"image": "a calf"}}, "blocks": []}


def signed_in(key):
    c = web.app.test_client()
    assert c.post("/login", data={"key": key}).status_code == 302
    return c


def person(admin, name, **ticks):
    key = admin.post("/api/team", json=dict(name=name, **ticks)).json["key"]
    return signed_in(key), next(p["id"] for p in admin.get("/api/team").json if p["name"] == name)


def owned_video(client, topic):
    slug = client.post("/api/videos", json={"topic": topic, "facts": "x"}).json["slug"]
    team.sql("DELETE FROM queue")
    pipeline.write(pipeline.VIDEOS / slug / "spec.json", dict(SPEC, slug=slug))
    return slug


def make_cards(slug):
    """Runs just the picture stage, which is what writes the cards."""
    waiting = []
    pipeline.pictures(pipeline.VIDEOS / slug, pipeline.read(pipeline.VIDEOS / slug / "spec.json"), waiting, [])
    return waiting


def drop(client, slug, cid, name="out.png"):
    import io
    return client.post(f"/api/videos/{slug}/card/{cid}", data={"file": (io.BytesIO(PNG), name)}, content_type="multipart/form-data")


def test_import_old_list():
    old = TMP / "accounts.json"
    old.write_text(json.dumps({"flow_image": {"list": [{"label": "Sample", "owner": "Person"}], "active": "Sample"}, "muse_video": {"list": [], "active": None}}))
    books.import_old(old)
    rows = books.accounts("flow")
    assert [(a["label"], a["is_default"]) for a in rows] == [("Sample Person", 1)]
    team.sql("DELETE FROM accounts")
    books.import_old(old)
    assert not books.accounts("flow"), "the old list is read once, so a removed account stays removed"
    assert old.exists(), "the old file is left in place"


def test_inbox_credits_and_hand_over():
    admin = signed_in(ADMIN)
    owner_client, owner = person(admin, "Owner", flow=True)
    a_client, a = person(admin, "Ana", flow=True)
    b_client, b = person(admin, "Ben", flow=True)
    c_client, c = person(admin, "Cal", flow=True)

    # no account anywhere: the card still exists and the dashboard says so
    slug = owned_video(owner_client, "No account")
    assert make_cards(slug) == ["pic"]
    assert any("no account" in w for w in admin.get("/api/dashboard").json["warnings"])

    # a teammate with no account uses the default account, and its owner gets the card, not the video
    assert a_client.post("/api/mine/flow", json={"label": "Ana flow"}).status_code == 200
    assert a_client.post("/api/mine/flow", json={"label": "Second"}).status_code == 200, "a second save renames"
    assert len(books.accounts("flow")) == 1
    assert a_client.post("/api/mine/nothing", json={"label": "x"}).status_code == 404
    admin.post("/api/accounts/flow_image", json={"active": "Second"})
    slug = owned_video(owner_client, "Default account")
    make_cards(slug)
    card = next(x for x in a_client.get("/api/cards").json["cards"] if x["slug"] == slug)
    assert card["account"] == "Second" and "a calf" in card["prompt"]
    assert a_client.get(f"/api/videos/{slug}/spec").status_code == 404, "running a card does not open the video"
    assert not owner_client.get("/api/cards").json["cards"], "the video owner has no card to run"
    assert not b_client.get("/api/cards").json["cards"]
    assert drop(b_client, slug, "pic").status_code == 404, "a stranger cannot drop a file on someone's card"

    # the owner's own account comes first, and is never swapped because of its balance
    assert owner_client.post("/api/mine/flow", json={"label": "Owner flow"}).status_code == 200
    slug = owned_video(owner_client, "Own account")
    make_cards(slug)
    card = next(x for x in owner_client.get("/api/cards").json["cards"] if x["slug"] == slug)
    assert card["account"] == "Owner flow"

    # out of credits: the prompt is held back, the drop is refused, nothing moves by itself
    books.save_settings(dict(flow_limit=2, flow_image=2))
    me = next(x for x in books.accounts("flow") if x["label"] == "Owner flow")
    assert not books.held(card)
    assert drop(owner_client, slug, "pic").status_code == 200
    assert books.spend(slug, card) == 2 and books.used(me) == 2, "a card is only counted once"
    assert next(x for x in books.accounts("flow") if x["id"] == me["id"])["left"] == 0

    slug2 = owned_video(owner_client, "Out of credits")
    make_cards(slug2)
    card = next(x for x in owner_client.get("/api/cards").json["cards"] if x["slug"] == slug2)
    assert card["held"] and card["prompt"] == "" and card["account"] == "Owner flow", "it waits on the same account"
    assert drop(owner_client, slug2, "pic").status_code == 409
    report = admin.get("/api/dashboard").json
    assert report["cards_held"] >= 1 and any("nothing left" in w for w in report["warnings"])

    # handing over needs the other person to have agreed, and uses their own account
    b_client.post("/api/mine/flow", json={"label": "Ben flow"})
    ben = next(x for x in books.accounts("flow") if x["label"] == "Ben flow")
    assert owner_client.post(f"/api/videos/{slug2}/card/pic/hand", json={"account": ben["id"]}).status_code == 403
    assert admin.post(f"/api/videos/{slug2}/card/pic/hand", json={"account": ben["id"]}).status_code == 400, "Ben has not agreed"
    b_client.post("/api/mine/flow", json={"helps": True})
    assert admin.post(f"/api/videos/{slug2}/card/pic/hand", json={"account": ben["id"]}).status_code == 200
    card = next(x for x in b_client.get("/api/cards").json["cards"] if x["slug"] == slug2)
    assert card["account"] == "Ben flow" and not card["held"]
    make_cards(slug2)
    assert pipeline.read(pipeline.VIDEOS / slug2 / "cards" / "pic.json")["account"] == "Ben flow", "a handed card stays handed"
    assert drop(b_client, slug2, "pic").status_code == 200
    assert work.live(slug2), "the last file sends the video on, whoever dropped it"

    # a real balance replaces the estimate, and resets after the window
    assert owner_client.post("/api/mine/flow", json={"left": "x"}).status_code == 400
    owner_client.post("/api/mine/flow", json={"left": 7})
    assert next(x for x in books.accounts("flow") if x["id"] == me["id"])["left"] == 7
    team.sql("UPDATE accounts SET real_at=? WHERE id=?", time.time() - 2 * books.DAY, me["id"])
    team.sql("UPDATE spend SET at=? WHERE account=?", time.time() - 2 * books.DAY, me["id"])
    assert next(x for x in books.accounts("flow") if x["id"] == me["id"])["left"] == 2, "a new day gives the limit back"

    # one person, one account per provider
    assert admin.post("/api/accounts/flow_image", json={"label": "Extra", "person": owner}).status_code == 400
    books.save_settings(dict(flow_limit=50, flow_image=1))

    # teammates cannot read the dashboard or change settings; the assistant can read it
    assert a_client.get("/api/dashboard").status_code == 403 and a_client.post("/api/settings", json={"flow_limit": 1}).status_code == 403
    key = admin.post("/api/team", json={"name": "Assistant", "assistant": True}).json["key"]
    c2 = web.app.test_client()
    h = {"Authorization": f"Bearer {key}"}
    assert c2.get("/api/dashboard", headers=h).status_code == 200 and c2.post("/api/settings", json={"flow_limit": 1}, headers=h).status_code == 403
    assert admin.post("/api/settings", json={"flow_limit": "lots"}).status_code == 400 and admin.post("/api/settings", json={"flow_limit": -1}).status_code == 400


def test_start_image():
    admin = signed_in(ADMIN)
    owner_client, _ = person(admin, "Dee", flow=True, muse=True)
    muse_client, _ = person(admin, "Muse person", muse=True)
    muse_client.post("/api/mine/muse", json={"label": "Muse one"})
    admin.post("/api/accounts/muse_video", json={"active": "Muse one"})
    slug = owned_video(owner_client, "Clip")
    job = pipeline.VIDEOS / slug
    (job / "inbox").mkdir()
    (job / "inbox" / "still.png").write_bytes(PNG)
    pipeline.card("muse_video", job, "clip_t1", "the calf moves", ratio="9x16", start_image=str(job / "inbox" / "still.png"), **{"try": 1})
    r = muse_client.get(f"/api/videos/{slug}/card/clip_t1/start")
    assert r.status_code == 200 and r.data == PNG, "the person running a clip can fetch its start image"
    outsider, _ = person(admin, "Eli")
    assert outsider.get(f"/api/videos/{slug}/card/clip_t1/start").status_code == 404
    c = pipeline.read(job / "cards" / "clip_t1.json")
    pipeline.write(job / "cards" / "clip_t1.json", dict(c, start_image=r"C:\Windows\win.ini"))
    assert muse_client.get(f"/api/videos/{slug}/card/clip_t1/start").status_code == 404, "a card cannot be pointed at other files"


def test_library():
    admin = signed_in(ADMIN)
    owner_client, _ = person(admin, "Fay", flow=True)
    owner_client.post("/api/mine/flow", json={"label": "Fay flow"})
    me = next(x for x in books.accounts("flow") if x["label"] == "Fay flow")
    one, two = owned_video(owner_client, "One"), owned_video(owner_client, "Two")
    make_cards(one)
    drop(owner_client, one, "pic")
    used = books.used(me)
    assert make_cards(one) == [], "the file is in"
    assert list(pipeline.LIBRARY.iterdir()), "a passed file is kept"
    assert make_cards(two) == [], "the same prompt reuses the file and raises no card"
    assert books.used(me) == used, "a reused file costs nothing"
    assert (pipeline.VIDEOS / two / "inbox" / "pic.png").read_bytes() == PNG


def test_downloads_cleanup_audit():
    admin = signed_in(ADMIN)
    owner_client, _ = person(admin, "Gul Noor")
    slug = owned_video(owner_client, "Finished")
    job = pipeline.VIDEOS / slug
    (job / "out").mkdir()
    (job / "out" / f"{slug}_9x16.mp4").write_bytes(b"video")
    r = owner_client.get(f"/files/{slug}/{slug}_9x16.mp4?download=1")
    day = time.strftime("%Y-%m-%d")
    assert r.data == b"video" and f"{day}_Gul_Noor_{slug}_9x16.mp4" in r.headers["Content-Disposition"], r.headers["Content-Disposition"]
    r.close()
    play = owner_client.get(f"/files/{slug}/{slug}_9x16.mp4")
    assert "attachment" not in play.headers.get("Content-Disposition", ""), "playing in the page still works"
    play.close()

    pipeline.set_status(job, state="done")
    assert web.old_videos() == [], "with no rule, nothing is ever old"
    admin.post("/api/settings", json={"keep_days": 1})
    assert slug not in web.old_videos(), "a new video is kept"
    old = time.time() - 3 * books.DAY
    os.utime(job / "status.json", (old, old))
    listed = admin.get("/api/dashboard").json["cleanup"]
    assert slug in [c["slug"] for c in listed] and job.exists(), "old videos are listed, never deleted by themselves"
    assert owner_client.post("/api/cleanup", json={"videos": [slug]}).status_code == 403
    assert admin.post("/api/cleanup", json={"videos": ["other"]}).json["deleted"] == 0
    assert admin.post("/api/cleanup", json={"videos": [slug]}).json["deleted"] == 1 and not job.exists()
    admin.post("/api/settings", json={"keep_days": 0})

    text = json.dumps(team.sql("SELECT * FROM audit"))
    for action in ("created a video", "finished a card", "handed card", "deleted an old video", "added Gul Noor"):
        assert action in text, action
    assert ADMIN not in text
    assert not [a for x in owner_client.get("/api/plugins").json for a in x["accounts"]["list"]], "only the admin sees the account list"


def test_quiet_hours():
    team.sql("DELETE FROM queue")
    hour = time.localtime().tm_hour
    work.add("ollama-job", "write", {"writer": "ollama_writer"})
    work.add("claude-job", "write", {"writer": "claude_writer"})
    books.save_settings(dict(ollama_from=(hour + 2) % 24, ollama_to=(hour + 3) % 24))
    assert not books.ollama_hour()
    assert work.claim("write")["job"] == "claude-job", "only Ollama waits for its hours"
    assert work.claim("write") is None
    books.save_settings(dict(ollama_from=hour, ollama_to=(hour + 1) % 24 or 24))
    assert books.ollama_hour() and work.claim("write")["job"] == "ollama-job"
    books.save_settings(dict(ollama_from=(hour - 1) % 24, ollama_to=(hour - 2) % 24))
    assert books.ollama_hour(), "hours can wrap past midnight"
    books.save_settings(dict(ollama_from=0, ollama_to=24))
    team.sql("DELETE FROM queue")


if __name__ == "__main__":
    test_import_old_list()
    test_inbox_credits_and_hand_over()
    test_start_image()
    test_library()
    test_downloads_cleanup_audit()
    test_quiet_hours()
    shutil.rmtree(TMP, ignore_errors=True)
    print("ALL BOOKS TESTS PASSED")
