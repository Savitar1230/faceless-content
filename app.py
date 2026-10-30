"""The desktop app: open http://127.0.0.1:5895 . Plugins and accounts, new videos, approval, job cards, outputs.
Videos run one at a time (a low-spec PC has no RAM for two).
"""
import queue
import re
import shutil
import threading

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

import pipeline as p
from plugins import registry

app = Flask(__name__)
jobs = queue.Queue()


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


@app.route("/")
def home():
    return render_template("index.html")


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
        cards = [p.read(c) for c in sorted((job / "cards").glob("*.json"))]
        out.append(dict(slug=spec["slug"], title=spec.get("title", ""), format=spec.get("format"), approved=spec.get("approved"), blocks=len(spec.get("blocks", [])),
                        status=p.read(job / "status.json", {}), cards=cards,
                        outputs=[f.name for f in sorted((job / "out").glob("*"))] if (job / "out").exists() else []))
    return jsonify(out)


@app.route("/api/videos", methods=["POST"])
def new_video():
    b = request.json
    slug = re.sub(r"[^a-z0-9]+", "-", b["topic"].lower()).strip("-")[:40].strip("-")
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
    if request.method == "POST": p.write(path, request.json)
    return jsonify(p.read(path))


@app.route("/api/videos/<slug>/approve", methods=["POST"])
def approve(slug):
    s = p.read(job_dir(slug) / "spec.json")
    s["approved"] = True
    p.write(job_dir(slug) / "spec.json", s)
    return run(slug)


@app.route("/api/videos/<slug>/run", methods=["POST"])
def run(slug):
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
    p.VIDEOS.mkdir(exist_ok=True)
    for st in p.VIDEOS.glob("*/status.json"):  # work that was running when the app closed will not resume by itself
        if p.read(st, {}).get("state") in ("running", "queued", "writing"):
            p.set_status(st.parent, state="blocked", stage="stopped", message="The app closed while this was working. Press Run again.")
    app.run(host="127.0.0.1", port=5895, threaded=True)
