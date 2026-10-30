"""The desktop app: open http://127.0.0.1:5895 . Plugins and accounts, new videos, approval, job cards, outputs.
Videos run one at a time (a low-spec PC has no RAM for two).
"""
import queue
import re
import secrets
import shutil
import threading

from flask import Flask, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

import pipeline as p
import spec as gate
import team
from plugins import registry

app = Flask(__name__)
app.secret_key = team.secret()
app.config.update(SESSION_COOKIE_SAMESITE="Strict", MAX_CONTENT_LENGTH=500 * 1024 * 1024)  # 500 MB is far above any single clip
jobs = queue.Queue()
ADMIN_ONLY = ("/api/team", "/api/accounts")


def worker():
    while True:
        task = jobs.get()
        try:
            task()
        except Exception:  # one bad job must not stop the queue
            app.logger.exception("job failed")
        jobs.task_done()


threading.Thread(target=worker, daemon=True).start()


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
    return jsonify(name=g.me["name"], role=g.me["role"])


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
    out = []
    for d in sorted(p.VIDEOS.glob("*/spec.json")):
        job, spec = d.parent, p.read(d)
        if not can_open(job.name): continue
        cards = [p.read(c) for c in sorted((job / "cards").glob("*.json"))]
        out.append(dict(slug=job.name, title=spec.get("title", ""), format=spec.get("format"), approved=spec.get("approved"), blocks=len(spec.get("blocks", [])),
                        status=p.read(job / "status.json", {}), cards=cards,
                        outputs=[f.name for f in sorted((job / "out").glob("*"))] if (job / "out").exists() else []))
    return jsonify(out)


@app.route("/api/videos", methods=["POST"])
def new_video():
    b = request.json
    if b.get("writer") == "claude_writer" and g.me["role"] != "admin":  # it runs on the admin's own Claude plan
        return jsonify(error="Only the admin can use the Claude writer."), 403
    slug = re.sub(r"[^a-z0-9]+", "-", b["topic"].lower()).strip("-")[:40].strip("-")
    slug = f"{slug or 'video'}-{secrets.token_hex(2)}"  # two people can pick the same topic
    team.new_job(slug, g.me["id"])
    p.write(job_dir(slug) / "spec.json", dict(slug=slug, title=b["topic"], format=b.get("format", "short"), blocks=[]))
    p.set_status(job_dir(slug), state="writing", stage="writing the script", message="")
    def task():
        try:
            p.write_spec(slug, b["topic"], b["facts"], b.get("sources", []), b.get("format", "short"), b.get("ratios", ["9x16"]), b.get("writer", "ollama_writer"))
        except Exception as e:
            p.set_status(job_dir(slug), state="blocked", message=str(e))
    jobs.put(task)
    return jsonify(slug=slug)


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


@app.route("/api/videos/<slug>/run", methods=["POST"])
def run(slug):
    missing = missing_access(slug)
    if missing: return jsonify(error=f"You do not have {missing} access. Ask the admin."), 403
    p.set_status(job_dir(slug), state="queued", stage="in the queue", message="")
    jobs.put(lambda: p.run(slug))
    return jsonify(ok=True)


@app.route("/api/videos/<slug>/delete", methods=["POST"])
def delete(slug):
    if p.read(job_dir(slug) / "status.json", {}).get("state") in ("running", "queued", "writing"):
        return jsonify(error="This video is still working"), 409
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


if __name__ == "__main__":
    first = team.setup()
    if first: print(f"\nFirst run. This is your admin key. Copy it now, it will not be shown again:\n\n{first}\n", flush=True)
    p.VIDEOS.mkdir(exist_ok=True)
    for st in p.VIDEOS.glob("*/status.json"):  # work that was running when the app closed will not resume by itself
        if p.read(st, {}).get("state") in ("running", "queued", "writing"):
            p.set_status(st.parent, state="blocked", stage="stopped", message="The app closed while this was working. Press Run again.")
    app.run(host="127.0.0.1", port=5895, threaded=True)
