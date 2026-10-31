"""The desktop app: open http://127.0.0.1:5895 . Plugins and accounts, new videos, approval, job cards, outputs.
The queue and its limits live in work.py.
"""
import json
import re
import secrets
import shutil
import time
from pathlib import Path

from flask import Flask, g, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

import books
import pages
import pipeline as p
import spec as gate
import team
import work
from plugins import registry

app = Flask(__name__)
app.secret_key = team.secret()
app.config.update(SESSION_COOKIE_SAMESITE="Strict", MAX_CONTENT_LENGTH=500 * 1024 * 1024)  # 500 MB is far above any single clip
ADMIN_ONLY = ("/api/team", "/api/accounts", "/api/queue", "/api/settings", "/api/cleanup")
CARD_ROUTES = ("drop_file", "card_start")  # the person running a card can reach it without owning the video
MAX_BATCH = 100


def do(task):
    """Runs one task from the queue and says how it ended. The plain reason is in the video's status."""
    slug, job = task["job"], job_dir(task["job"])
    try:
        if task["line"] == "make": state = p.run(slug)["state"]
        else:
            p.write_spec(slug, **json.loads(task["args"]))
            state = p.read(job / "status.json")["state"]
    except Exception as e:
        p.set_status(job, state="failed", message=f"Writing the script failed: {e}")
        state = "failed"
    books.log("queue", f"{'made' if task['line'] == 'make' else 'wrote'}: {state}", slug)
    return state


def job_dir(slug):
    if not re.fullmatch(r"[a-z0-9-]+", slug): raise ValueError("bad video name")
    return p.VIDEOS / slug


def can_open(slug): return g.me["role"] != "teammate" or team.owner(slug) == g.me["id"]


def card_path(slug, cid): return job_dir(slug) / "cards" / f"{secure_filename(cid)}.json"


def my_card(slug, cid): return p.read(card_path(slug, cid), {}).get("person") == g.me["id"]


def can_use(x): return x and (g.me["role"] != "teammate" or x["person"] == g.me["id"])


@app.errorhandler(pages.Taken)
def topic_taken(e): return jsonify(error=str(e)), 409


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
    if request.path.startswith("/api/dashboard") and g.me["role"] == "teammate":
        return jsonify(error="Only the admin can do that."), 403
    args = request.view_args or {}
    if args.get("slug") and not can_open(args["slug"]) and not (request.endpoint in CARD_ROUTES and my_card(args["slug"], args["cid"])):
        return jsonify(error="Not found."), 404


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
    return jsonify(id=g.me["id"], name=g.me["name"], role=g.me["role"], queue_paused=work.ALL in work.paused())


@app.route("/api/queue/pause", methods=["POST"])
def pause_queue():
    on = bool(request.json.get("paused"))
    work.pause(on=on)
    books.log(g.me["name"], "paused the queue" if on else "resumed the queue")
    return jsonify(ok=True)


@app.route("/api/team", methods=["GET", "POST"])
def people():
    if request.method == "GET": return jsonify(team.people())
    b = request.json
    name = b.get("name", "").strip()
    if not name: return jsonify(error="Add a name first."), 400
    if not b.get("assistant"):
        books.log(g.me["name"], f"added {name} and made a key")
        return jsonify(key=team.new_key(team.add(name, flow=int(bool(b.get("flow"))), muse=int(bool(b.get("muse"))))))
    if any(x["role"] == "assistant" for x in team.people()):
        return jsonify(error="The assistant already has a key. Use New key on its row."), 409
    books.log(g.me["name"], "made the assistant key")
    return jsonify(key=team.new_key(team.add(name, "assistant", 1, 1), None))


@app.route("/api/team/<int:pid>", methods=["POST"])
def person(pid):
    """Ticks, pause, remove, new key and revoke key for anyone except the admin."""
    who = team.editable(pid)
    if not who: return jsonify(error="Not found."), 404
    b = request.json
    if b.get("status") not in (None, "active", "paused", "removed"): return jsonify(error="Unknown status."), 400
    if b.get("revoke"):
        team.revoke(pid)
        books.log(g.me["name"], f"revoked the key of {who['name']}")
    team.change(pid, b.get("flow"), b.get("muse"), b.get("status"))
    if b.get("status"): books.log(g.me["name"], f"set {who['name']} to {b['status']}")
    if b.get("status") == "removed":
        for job in work.drop_owner(pid):
            p.set_status(p.VIDEOS / job, state="failed", stage="stopped", message="Stopped because the owner was removed.")
    if b.get("new_key"):
        books.log(g.me["name"], f"made a new key for {who['name']}")
        return jsonify(key=team.new_key(pid, None if who["role"] == "assistant" else team.KEY_DAYS))
    return jsonify(ok=True)


def plugin_accounts(x):
    """Only the admin sees the account list. Flow has one list; Muse's video and voice share one."""
    if "card_ext" not in x.manifest or g.me["role"] != "admin": return dict(list=[], active=None)
    rows = books.accounts(books.provider_of(x.name))
    return dict(list=[dict(label=a["label"], owner=a["owner"]) for a in rows], active=next((a["label"] for a in rows if a["is_default"]), None))


@app.route("/api/plugins")
def plugins():
    return jsonify([dict(name=x.name, title=x.manifest["title"], kind=x.kind, description=x.manifest["description"],
                         free=x.manifest.get("free_tier"), card="card_ext" in x.manifest, site=x.manifest.get("site"), accounts=plugin_accounts(x))
                    for x in registry.list()])


@app.route("/api/accounts/<plugin>", methods=["POST"])
def accounts(plugin):
    """Holds a name and an owner only. No passwords: each person signs in to Flow or Muse in their own browser."""
    if not registry.get(plugin): return jsonify(error="unknown plugin"), 404
    provider, b = books.provider_of(plugin), request.json
    if b.get("remove"): books.remove_account(provider, b["remove"])
    elif b.get("active"): books.set_default(provider, b["active"])
    else:
        problem = books.add_account(provider, b.get("label", "").strip(), int(b.get("person") or g.me["id"]))
        if problem: return jsonify(error=problem), 400
    return jsonify(ok=True)


def video_title(slug): return p.read(p.VIDEOS / slug / "spec.json", {}).get("title", slug)


def open_cards():
    """Every card still waiting for a file, with whether its account can pay for it."""
    out = []
    for f in sorted(p.VIDEOS.glob("*/cards/*.json")):
        slug = f.parent.parent.name
        c = p.read(f)
        out.append(dict(c, slug=slug, video=video_title(slug), held=books.held(c)))
    return out


@app.route("/api/cards")
def cards():
    """A person's inbox: the cards for their own account, with their account beside it. The admin sees every card."""
    mine = [c for c in open_cards() if g.me["role"] == "admin" or c.get("person") == g.me["id"]]
    for c in mine:
        if c["held"]: c["prompt"] = ""  # an account with nothing left must not be spent by mistake
    helpers = [dict(id=a["id"], label=a["label"], owner=a["owner"], provider=a["provider"], left=a["left"]) for a in books.accounts() if a["helps"]]
    return jsonify(cards=mine, mine=[a for a in books.accounts() if a["person"] == g.me["id"]], helpers=helpers if g.me["role"] == "admin" else [])


@app.route("/api/mine/<provider>", methods=["POST"])
def my_account(provider):
    """A person's own account: its name, the balance they can see in Flow or Muse, and whether they take handed cards."""
    if provider not in books.PROVIDERS: return jsonify(error="Unknown provider."), 404
    b = request.json
    a = next((x for x in books.accounts(provider) if x["person"] == g.me["id"]), None)
    if "label" in b:
        label = b["label"].strip()
        if a and label: team.sql("UPDATE accounts SET label=? WHERE id=?", label, a["id"])
        else:
            problem = books.add_account(provider, label, g.me["id"])
            if problem: return jsonify(error=problem), 400
        return jsonify(ok=True)
    if not a: return jsonify(error="Add your account first."), 400
    if "helps" in b: team.sql("UPDATE accounts SET helps=? WHERE id=?", int(bool(b["helps"])), a["id"])
    if "left" in b:
        try: amount = float(b["left"])
        except (TypeError, ValueError): return jsonify(error="Type the balance as a number."), 400
        if amount < 0: return jsonify(error="Type the balance as a number."), 400
        books.set_left(a["id"], amount)
        books.log(g.me["name"], "typed the real balance", account=a["label"], credits=amount)
    return jsonify(ok=True)


def old_videos():
    """Finished videos past the admin's keep rule. An empty rule means nothing is ever old."""
    days = books.settings()["keep_days"]
    if not days: return []
    cut = time.time() - days * books.DAY
    return [f.parent.name for f in p.VIDEOS.glob("*/status.json") if p.read(f, {}).get("state") == "done" and f.stat().st_mtime < cut]


@app.route("/api/dashboard")
def dashboard():
    cards_open = open_cards()
    r = books.report()
    r["warnings"] = [f"{a['provider'].title()} account {a['label']} has nothing left (estimate). Its cards wait until it resets or {a['owner']} types the real balance."
                     for a in r["accounts"] if a["left"] <= 0]
    no_account = sum(1 for c in cards_open if not c.get("account_id"))
    if no_account: r["warnings"].append(f"{no_account} cards have no account. Add one under Plugins & accounts, then press Run again.")
    if pages.unused() < pages.LOW_TOPICS: r["warnings"].append(f"Only {pages.unused()} unused topics left. Add new ones under Pages.")
    r["cards_open"], r["cards_held"] = len(cards_open), sum(c["held"] for c in cards_open)
    r["failed"] = [dict(slug=f.parent.name, title=video_title(f.parent.name), message=st.get("message", ""))
                   for f in p.VIDEOS.glob("*/status.json") if (st := p.read(f, {})).get("state") == "failed"]
    r["cleanup"] = [dict(slug=s, title=video_title(s)) for s in old_videos()]
    return jsonify(r)


@app.route("/api/settings", methods=["POST"])
def save_settings():
    try: changes = {k: float(v) for k, v in request.json.items()}
    except (TypeError, ValueError): return jsonify(error="Settings must be numbers."), 400
    if any(v < 0 for v in changes.values()): return jsonify(error="Settings cannot be below zero."), 400
    books.save_settings(changes)
    books.log(g.me["name"], "changed the settings")
    return jsonify(ok=True)


@app.route("/api/cleanup", methods=["POST"])
def cleanup():
    """Deletes what the admin was shown and pressed the button for. Nothing here runs by itself."""
    deleted = 0
    for slug in [s for s in request.json.get("videos", []) if s in old_videos()]:
        work.forget(slug)
        shutil.rmtree(job_dir(slug), ignore_errors=True)
        if not job_dir(slug).exists():  # Windows refuses a file someone is still watching, so only what really went is counted
            books.log(g.me["name"], "deleted an old video", slug)
            deleted += 1
    return jsonify(deleted=deleted)


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


def add_video(owner, topic, facts, sources, fmt, ratios, writer, page=None):
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40].strip("-")
    slug = f"{slug or 'video'}-{secrets.token_hex(2)}"
    pages.claim(topic, slug, page and page["id"])  # before anything else, so a used topic stops here
    team.new_job(slug, owner)
    p.write(job_dir(slug) / "spec.json", dict(slug=slug, title=topic, format=fmt, blocks=[]))
    p.set_status(job_dir(slug), state="queued", stage="in the queue", message="")
    args = dict(topic=topic, facts=facts, sources=sources, fmt=fmt, ratios=ratios, writer=writer)
    if page: args.update(identity=page["identity"], voice_cfg=dict(p.VOICE, voice=page["voice"]))
    work.add(slug, "write", args)
    books.log(g.me["name"], "created a video", slug)
    return slug


@app.route("/api/videos", methods=["POST"])
def new_video():
    b = request.json
    topic, facts, fmt, writer = b.get("topic", "").strip(), b.get("facts", "").strip(), b.get("format", "short"), b.get("writer", "ollama_writer")
    problem = video_problem(topic, facts, fmt, writer)
    if problem: return jsonify(error=problem), 400
    page = pages.page(b["page"]) if b.get("page") else None
    if b.get("page") and not can_use(page): return jsonify(error="Not found."), 404
    if page and not page["locked"]: return jsonify(error="Lock this page's identity first, under Pages."), 400
    return jsonify(slug=add_video(page["person"] if page else g.me["id"], topic, facts, b.get("sources", []), fmt, b.get("ratios", ["9x16"]), writer, page))


def batch_rows(text, base, fmt, writer):
    """Reads topic | facts | sources | owner, one video a line. Returns the rows, and a problem for each bad line."""
    rows, bad, seen = [], [], set()
    people = [x for x in team.people() if x["role"] != "assistant"]
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip(): continue
        topic, facts, sources, owner = ([c.strip() for c in line.split("|")] + ["", "", ""])[:4]
        facts = f"{base}\n{facts}".strip()
        problem, who = video_problem(topic, facts, fmt, writer), g.me["id"]
        if topic and (pages.used(topic) or pages.plain(topic) in seen): problem = "that topic has been used already"
        seen.add(pages.plain(topic))
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


@app.route("/api/pages", methods=["GET", "POST"])
def page_list():
    if request.method == "GET":
        return jsonify(pages=pages.listing(g.me["id"] if g.me["role"] == "teammate" else None), voices=pages.VOICES, unused=pages.unused())
    if g.me["role"] != "admin": return jsonify(error="Only the admin can do that."), 403
    b = request.json
    problem = pages.add(int(b.get("person") or g.me["id"]), b.get("name", "").strip())
    if problem: return jsonify(error=problem), 400
    books.log(g.me["name"], f"added page {b['name'].strip()}")
    return jsonify(ok=True)


@app.route("/api/pages/<int:pid>", methods=["POST"])
def save_page(pid):
    """The admin names a page. Its person chooses the identity and voice, then locks them. Only the admin can unlock."""
    x, b, admin = pages.page(pid), request.json, g.me["role"] == "admin"
    if not can_use(x) or g.me["role"] == "assistant": return jsonify(error="Not found."), 404
    if not admin and ("name" in b or b.get("locked") is False): return jsonify(error="Only the admin can do that."), 403
    problem = pages.save(x, b)
    if problem: return jsonify(error=problem), 400
    books.log(g.me["name"], f"changed page {x['name']}")
    return jsonify(ok=True)


@app.route("/api/pages/<int:pid>/suggest")
def suggest_topics(pid):
    if not can_use(pages.page(pid)): return jsonify(error="Not found."), 404
    return jsonify(pages.suggest(pid, request.args.get("skip", "").split(",")))


@app.route("/api/topics", methods=["POST"])
def add_topics():
    """The admin or the assistant adds to the bank. Teammates only pick from it."""
    if g.me["role"] == "teammate": return jsonify(error="Only the admin can do that."), 403
    added, skipped = pages.add_topics(request.json.get("rows", ""))
    books.log(g.me["name"], f"added {added} topics")
    return jsonify(added=added, skipped=skipped)


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
        if old.get("identity"): s.update(identity=old["identity"], voice=old["voice"])  # a page's voice is locked
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
        books.log(g.me["name"], "approved the script", slug)
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
    return to_queue(slug)


def to_queue(slug):
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
    if not any((job_dir(slug) / d).exists() for d in ("takes", "inbox", "out")): pages.release(slug)  # nothing was made, so the topic goes back
    work.forget(slug)
    shutil.rmtree(job_dir(slug), ignore_errors=True)
    return jsonify(ok=True)


@app.route("/api/videos/<slug>/card/<cid>", methods=["POST"])
def drop_file(slug, cid):
    """A person dropped the finished file for a job card; then the video carries on by itself."""
    job = job_dir(slug)
    f = request.files["file"]
    ext = secure_filename(f.filename).rsplit(".", 1)[-1].lower()
    card = p.read(card_path(slug, cid))
    if not card or ext not in card["ext"]: return jsonify(error=f"file must be one of {card and card['ext']}"), 400
    if books.held(card): return jsonify(error=f"{card['account']} has no credits left. If the real balance is higher, type it under Cards."), 409
    (job / "inbox").mkdir(exist_ok=True)
    f.save(job / "inbox" / f"{secure_filename(cid)}.{ext}")
    books.log(g.me["name"], "finished a card", slug, card.get("account") or "", books.spend(slug, card))
    left = [c for c in (job / "cards").glob("*.json") if not any((job / "inbox" / f"{c.stem}.{e}").exists() for e in p.read(c)["ext"])]
    if not left: return to_queue(slug)  # every card has its file, so the video carries on, whoever finished the last one
    return jsonify(ok=True)


@app.route("/api/videos/<slug>/card/<cid>/start")
def card_start(slug, cid):
    """The start image a Muse clip needs, for whoever runs the card from their own PC."""
    start = p.read(card_path(slug, cid), {}).get("start_image")
    if not start: return jsonify(error="Not found."), 404
    path = Path(start).resolve()
    if p.ROOT.resolve() not in path.parents and p.VIDEOS.resolve() not in path.parents: return jsonify(error="Not found."), 404
    return send_file(path, as_attachment=True)


@app.route("/api/videos/<slug>/card/<cid>/hand", methods=["POST"])
def hand(slug, cid):
    """The admin gives a card to a person who agreed to take them. It runs on that person's own account, in their own browser."""
    if g.me["role"] != "admin": return jsonify(error="Only the admin can do that."), 403
    card, a = p.read(card_path(slug, cid)), books.account(request.json.get("account"))
    ready = next((x for x in books.accounts() if a and x["id"] == a["id"] and x["helps"]), None)
    if not card or not ready or ready["provider"] != books.provider_of(card["plugin"]):
        return jsonify(error="That person has not agreed to take cards for this tool."), 400
    p.write(card_path(slug, cid), dict(card, account=a["label"], account_id=a["id"], person=a["person"], handed=True))
    books.log(g.me["name"], f"handed card {card['id']} to {ready['owner']}", slug, a["label"])
    return jsonify(ok=True)


@app.route("/files/<slug>/<path:name>")
def files(slug, name):
    if "download" not in request.args: return send_from_directory(job_dir(slug) / "out", name)
    info = team.job_info(slug) or dict(name="admin", created=(job_dir(slug) / "out" / name).stat().st_mtime)
    day = time.strftime("%Y-%m-%d", time.localtime(info["created"]))
    return send_from_directory(job_dir(slug) / "out", name, as_attachment=True, download_name=secure_filename(f"{day}_{info['name']}_{name}"))


def resume():
    """Queued work carries on after a restart. What was running does not resume by itself, and says so."""
    p.VIDEOS.mkdir(exist_ok=True)
    books.import_old(p.ACCOUNTS)
    pages.import_bank()
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
