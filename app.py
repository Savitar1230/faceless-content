"""The desktop app: open http://127.0.0.1:5895 . Plugins and accounts, new videos, approval, job cards, outputs.
The queue and its limits live in work.py.
"""
import json
import re
import secrets
import shutil
import time

from flask import Flask, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

import pipeline as p
import spec as gate
import team
import work
from plugins import registry

app = Flask(__name__)
app.secret_key = team.secret()
app.config.update(SESSION_COOKIE_SAMESITE="Strict", MAX_CONTENT_LENGTH=500 * 1024 * 1024)  # 500 MB is far above any single clip
ADMIN_ONLY = ("/api/team", "/api/accounts", "/api/queue")
MAX_BATCH = 100


def do(task):
    """Runs one task from the queue and says how it ended. The plain reason is in the video's status."""
    slug, job = task["job"], job_dir(task["job"])
    try:
        if task["line"] == "make": return p.run(slug)["state"]
        p.write_spec(slug, **json.loads(task["args"]))
        return p.read(job / "status.json")["state"]
    except Exception as e:
        p.set_status(job, state="failed", message=f"Writing the script failed: {e}")
        return "failed"


def job_dir(slug):
    if not re.fullmatch(r"[a-z0-9-]+", slug): raise ValueError("bad video name")
    return p.VIDEOS / slug


def can_open(slug): return g.me["role"] != "teammate" or team.owner(slug) == g.me["id"]


@app.before_request
def check_login():
    """Runs before every route, so a new route is protected without anyone remembering to."""
    if request.endpoint == "login": return
    bearer = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    g.me = team.who(team.login(bearer) if bearer else session.get("key"))
    if not g.me:
        if request.path.startswith(("/api/", "/files/")): return jsonify(error="Please sign in."), 401
        return redirect(url_for("login"))
    if request.path.startswith(ADMIN_ONLY) and g.me["role"] != "admin":
        return jsonify(error="Only the admin can do that."), 403
    slug = (request.view_args or {}).get("slug")
    if slug and not can_open(slug): return jsonify(error="Not found."), 404


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        h = team.login(request.form.get("key", "").strip())
        if h:
            session["key"], session.permanent = h, True
            return redirect("/")
        error = "That key did not work."
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/me")
def me():
    return jsonify(name=g.me["name"], role=g.me["role"], queue_paused=work.ALL in work.paused())


@app.route("/api/queue/pause", methods=["POST"])
def pause_queue():
    work.pause(on=bool(request.json.get("paused")))
    return jsonify(ok=True)


@app.route("/api/team", methods=["GET", "POST"])
def people():
    if request.method == "GET": return jsonify(team.people())
    b = request.json
    name = b.get("name", "").strip()
    if not name: return jsonify(error="Add a name first."), 400
    if not b.get("assistant"):
        return jsonify(key=team.new_key(team.add(name, flow=int(bool(b.get("flow"))), muse=int(bool(b.get("muse"))))))
    if any(x["role"] == "assistant" for x in team.people()):
        return jsonify(error="The assistant already has a key. Use New key on its row."), 409
    return jsonify(key=team.new_key(team.add(name, "assistant", 1, 1), None))


@app.route("/api/team/<int:pid>", methods=["POST"])
def person(pid):
    """Ticks, pause, remove, new key and revoke key for anyone except the admin."""
    who = team.editable(pid)
    if not who: return jsonify(error="Not found."), 404
    b = request.json
    if b.get("status") not in (None, "active", "paused", "removed"): return jsonify(error="Unknown status."), 400
    if b.get("revoke"): team.revoke(pid)
    team.change(pid, b.get("flow"), b.get("muse"), b.get("status"))
    if b.get("status") == "removed":
        for job in work.drop_owner(pid):
            p.set_status(p.VIDEOS / job, state="failed", stage="stopped", message="Stopped because the owner was removed.")
    if b.get("new_key"): return jsonify(key=team.new_key(pid, None if who["role"] == "assistant" else team.KEY_DAYS))
    return jsonify(ok=True)


@app.route("/api/plugins")
def plugins():
    accounts = p.read(p.ACCOUNTS, {})
    return jsonify([dict(name=x.name, title=x.manifest["title"], kind=x.kind, description=x.manifest["description"],
                         free=x.manifest.get("free_tier"), card="card_ext" in x.manifest, site=x.manifest.get("site"), accounts=accounts.get(x.name, {"list": [], "active": None}))
                    for x in registry.list()])


@app.route("/api/accounts/<plugin>", methods=["POST"])
def accounts(plugin):
    """Holds a name and an owner only. No passwords: each person signs in to Flow or Muse in their own browser."""
    if not registry.get(plugin): return jsonify(error="unknown plugin"), 404
    data = p.read(p.ACCOUNTS, {})
    a = data.setdefault(plugin, {"list": [], "active": None})
    body = request.json
    if body.get("remove"):
        a["list"] = [x for x in a["list"] if x["label"] != body["remove"]]
        if a["active"] == body["remove"]: a["active"] = None
    elif body.get("active"):
        a["active"] = body["active"]
    else:
        a["list"].append({"label": body["label"].strip(), "owner": body.get("owner", "").strip()})
        a["active"] = a["active"] or body["label"].strip()
    p.write(p.ACCOUNTS, data)
    return jsonify(a)


@app.route("/api/videos")
def videos():
    out, held = [], work.paused()
    for d in sorted(p.VIDEOS.glob("*/spec.json")):
        job, spec = d.parent, p.read(d)
        if not can_open(job.name): continue
        cards = [p.read(c) for c in sorted((job / "cards").glob("*.json"))]
        out.append(dict(slug=job.name, title=spec.get("title", ""), format=spec.get("format"), approved=spec.get("approved"), blocks=len(spec.get("blocks", [])), paused=job.name in held,
                        status=p.read(job / "status.json", {}), cards=cards,
                        outputs=[f.name for f in sorted((job / "out").glob("*"))] if (job / "out").exists() else []))
    return jsonify(out)


def video_problem(topic, facts, fmt, writer):
    if not topic or not facts: return "Add a topic and the facts."
    if fmt not in ("short", "long"): return "Format must be short or long."
    if writer == "claude_writer" and g.me["role"] != "admin": return "Only the admin can use the Claude writer."  # it runs on the admin's own Claude plan


def add_video(owner, topic, facts, sources, fmt, ratios, writer):
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40].strip("-")
    slug = f"{slug or 'video'}-{secrets.token_hex(2)}"  # two people can pick the same topic
    team.new_job(slug, owner)
    p.write(job_dir(slug) / "spec.json", dict(slug=slug, title=topic, format=fmt, blocks=[]))
    p.set_status(job_dir(slug), state="queued", stage="in the queue", message="")
    work.add(slug, "write", dict(topic=topic, facts=facts, sources=sources, fmt=fmt, ratios=ratios, writer=writer))
    return slug


@app.route("/api/videos", methods=["POST"])
def new_video():
    b = request.json
    topic, facts, fmt, writer = b.get("topic", "").strip(), b.get("facts", "").strip(), b.get("format", "short"), b.get("writer", "ollama_writer")
    problem = video_problem(topic, facts, fmt, writer)
    if problem: return jsonify(error=problem), 400
    return jsonify(slug=add_video(g.me["id"], topic, facts, b.get("sources", []), fmt, b.get("ratios", ["9x16"]), writer))


def batch_rows(text, base, fmt, writer):
    """Reads topic | facts | sources | owner, one video a line. Returns the rows, and a problem for each bad line."""
    rows, bad = [], []
    people = [x for x in team.people() if x["role"] != "assistant"]
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip(): continue
        topic, facts, sources, owner = ([c.strip() for c in line.split("|")] + ["", "", ""])[:4]
        facts = f"{base}\n{facts}".strip()
        problem, who = video_problem(topic, facts, fmt, writer), g.me["id"]
        if owner and g.me["role"] != "admin": problem = "only the admin can set an owner"
        elif owner:
            match = [x["id"] for x in people if x["name"].lower() == owner.lower()]
            if len(match) != 1: problem = f"no single person called {owner}"
            else: who = match[0]
        if problem: bad.append(f"Line {n}: {problem}")
        rows.append(dict(owner=who, topic=topic, facts=facts, sources=sources.split()))
    return rows, bad


@app.route("/api/batch", methods=["POST"])
def batch():
    """One line, one video, each tracked on its own. Nothing is queued unless every line is good."""
    b = request.json
    fmt, writer = b.get("format", "short"), b.get("writer", "ollama_writer")
    rows, bad = batch_rows(b.get("rows", ""), b.get("facts", "").strip(), fmt, writer)
    if not rows: bad.append("Add at least one line.")
    if len(rows) > MAX_BATCH: bad.append(f"A batch can hold {MAX_BATCH} videos, this has {len(rows)}.")
    if bad: return jsonify(error="\n".join(bad)), 400
    return jsonify(slugs=[add_video(fmt=fmt, ratios=b.get("ratios", ["9x16"]), writer=writer, **r) for r in rows])


@app.route("/api/templates", methods=["GET", "POST"])
def templates():
    """Saved settings the whole team can reuse."""
    if request.method == "GET": return jsonify(team.sql("SELECT id, name, owner, format, ratios, writer, facts FROM templates ORDER BY name"))
    b = request.json
    name = b.get("name", "").strip()
    if not name: return jsonify(error="Give the template a name."), 400
    team.sql("INSERT INTO templates (name, owner, format, ratios, writer, facts, created) VALUES (?,?,?,?,?,?,?)", name, g.me["id"],
             b.get("format", "short"), ",".join(b.get("ratios", ["9x16"])), b.get("writer", "ollama_writer"), b.get("facts", ""), time.time())
    return jsonify(ok=True)


@app.route("/api/templates/<int:tid>/delete", methods=["POST"])
def delete_template(tid):
    team.sql("DELETE FROM templates WHERE id=? AND (owner=? OR ?)", tid, g.me["id"], g.me["role"] == "admin")
    return jsonify(ok=True)


@app.route("/api/videos/<slug>/spec", methods=["GET", "POST"])
def spec(slug):
    path = job_dir(slug) / "spec.json"
    if request.method == "POST":
        s, old = request.json, p.read(path, {})
        if not isinstance(s, dict): return jsonify(error="That is not a script."), 400
        # approval is a person's decision, so a saved file cannot set it, and a changed script needs it again
        same = all(s.get(k) == old.get(k) for k in ("blocks", "pictures", "facts"))
        s.update(slug=slug, approved=bool(old.get("approved")) and same)
        p.write(path, s)
    return jsonify(p.read(path))


def missing_access(slug):
    """Flow and Muse ticks decide who may queue work for those tools."""
    s = p.read(job_dir(slug) / "spec.json")
    if gate.shape(s): return None  # the script check stops this video anyway
    pics = s.get("pictures", {}).values()
    uses = dict(flow=any("image" in x for x in pics), muse=any("video" in x for x in pics) or s.get("voice", {}).get("plugin") == "muse_voice")
    return next((name.title() for name, used in uses.items() if used and not g.me[name]), None)


@app.route("/api/videos/<slug>/approve", methods=["POST"])
def approve(slug):
    if g.me["role"] == "assistant": return jsonify(error="A person has to approve a script."), 403
    s = p.read(job_dir(slug) / "spec.json")
    if not missing_access(slug):
        s["approved"] = True
        p.write(job_dir(slug) / "spec.json", s)
    return run(slug)


@app.route("/api/approve-all", methods=["POST"])
def approve_all():
    """Approves every written script this person can see that passes the script check. A person still has to press it."""
    if g.me["role"] == "assistant": return jsonify(error="A person has to approve a script."), 403
    count = 0
    for d in p.VIDEOS.glob("*/spec.json"):
        slug, s = d.parent.name, p.read(d)
        if can_open(slug) and s.get("blocks") and not s.get("approved") and not gate.check(s) and not missing_access(slug) and not work.live(slug):
            approve(slug)
            count += 1
    return jsonify(approved=count)


@app.route("/api/videos/<slug>/run", methods=["POST"])
def run(slug):
    missing = missing_access(slug)
    if missing: return jsonify(error=f"You do not have {missing} access. Ask the admin."), 403
    if work.live(slug): return jsonify(ok=True)  # already in the queue, so a second click changes nothing
    p.set_status(job_dir(slug), state="queued", stage="in the queue", message="")
    args = work.write_args(slug)
    if args and not p.read(job_dir(slug) / "spec.json").get("blocks"): work.add(slug, "write", args)  # the script never got written
    else: work.add(slug, "make")
    return jsonify(ok=True)


@app.route("/api/videos/<slug>/pause", methods=["POST"])
def pause_video(slug):
    work.pause(slug, bool(request.json.get("paused")))
    return jsonify(ok=True)


@app.route("/api/videos/<slug>/delete", methods=["POST"])
def delete(slug):
    if p.read(job_dir(slug) / "status.json", {}).get("state") == "running":
        return jsonify(error="This video is still working"), 409
    work.forget(slug)
    shutil.rmtree(job_dir(slug), ignore_errors=True)
    return jsonify(ok=True)


@app.route("/api/videos/<slug>/card/<cid>", methods=["POST"])
def drop_file(slug, cid):
    """A person dropped the finished file for a job card; then the video carries on by itself."""
    job = job_dir(slug)
    f = request.files["file"]
    ext = secure_filename(f.filename).rsplit(".", 1)[-1].lower()
    card = p.read(job / "cards" / f"{secure_filename(cid)}.json")
    if not card or ext not in card["ext"]: return jsonify(error=f"file must be one of {card and card['ext']}"), 400
    (job / "inbox").mkdir(exist_ok=True)
    f.save(job / "inbox" / f"{secure_filename(cid)}.{ext}")
    left = [c for c in (job / "cards").glob("*.json") if not any((job / "inbox" / f"{c.stem}.{e}").exists() for e in p.read(c)["ext"])]
    if not left: return run(slug)  # every card has its file, so the video carries on
    return jsonify(ok=True)


@app.route("/files/<slug>/<path:name>")
def files(slug, name):
    return send_from_directory(job_dir(slug) / "out", name)


def resume():
    """Queued work carries on after a restart. What was running does not resume by itself, and says so."""
    p.VIDEOS.mkdir(exist_ok=True)
    work.recover()
    for st in p.VIDEOS.glob("*/status.json"):
        if p.read(st, {}).get("state") in ("running", "queued", "writing") and not work.live(st.parent.name):
            p.set_status(st.parent, state="failed", stage="stopped", message="Stopped by a restart. Press Run again.")
    work.start(do)


if __name__ == "__main__":
    first = team.setup()
    if first: print(f"\nFirst run. This is your admin key. Copy it now, it will not be shown again:\n\n{first}\n", flush=True)
    resume()
    app.run(host="127.0.0.1", port=5895, threaded=True)
