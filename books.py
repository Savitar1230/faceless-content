"""Flow and Muse accounts, the credit ledger, the audit log and the admin's settings.
Flow and Muse show balances only on their own pages, so every number here is an estimate: cards done times a cost table.
An account is never picked by its balance: rule 5, no farming free credits.
"""
import json
import time

import team

DAY = 86400
WEEK = 7 * DAY
PROVIDERS = ("flow", "muse")
# flow_limit is 50 free credits a day, muse_limit is 10 videos a week. Image and voice costs are unknown until a real card runs.
DEFAULTS = dict(flow_image=1, muse_video=1, muse_voice=.2, flow_limit=50, muse_limit=10, keep_days=0, ollama_from=0, ollama_to=24)


def settings():
    s = dict(DEFAULTS)
    s.update({r["name"]: json.loads(r["value"]) for r in team.sql("SELECT name, value FROM settings")})
    return s


def save_settings(changes):
    for k, v in changes.items():
        if k in DEFAULTS: team.sql("INSERT OR REPLACE INTO settings (name, value) VALUES (?,?)", k, json.dumps(v))


def ollama_hour():
    """Ollama is slow and heavy, so the admin can keep it to quiet hours. 0 to 24 means any time."""
    s, h = settings(), time.localtime().tm_hour
    a, b = s["ollama_from"], s["ollama_to"]
    return a <= h < b if a <= b else h >= a or h < b


def today():
    t = time.localtime()
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))


def window(provider):
    """Flow's credits come back each day and Muse's meter is weekly."""
    return time.time() - WEEK if provider == "muse" else today()


def provider_of(plugin): return plugin.split("_")[0]  # flow_image is flow, muse_video and muse_voice are muse


def log(who, action, job="", account="", credits=None):
    """Who did what, to which video, with which account, at what cost. Never keys or passwords."""
    team.sql("INSERT INTO audit (at, who, action, job, account, credits) VALUES (?,?,?,?,?,?)", time.time(), who, action, job, account, credits)


# ---------------------------------------------------------------- accounts
def add_account(provider, label, person):
    """One person, one account per provider. Returns a plain problem, or None."""
    if not label: return "Give the account a name."
    if team.sql("SELECT 1 FROM accounts WHERE provider=? AND person=?", provider, person):
        return f"That person already has a {provider.title()} account."
    first = not team.sql("SELECT 1 FROM accounts WHERE provider=? AND is_default=1", provider)
    team.sql("INSERT INTO accounts (provider, label, person, is_default) VALUES (?,?,?,?)", provider, label, person, int(first))


def remove_account(provider, label):
    team.sql("DELETE FROM accounts WHERE provider=? AND label=?", provider, label)


def set_default(provider, label):
    team.sql("UPDATE accounts SET is_default = (label=?) WHERE provider=?", label, provider)


def account(aid):
    rows = team.sql("SELECT * FROM accounts WHERE id=?", aid)
    return rows[0] if rows else None


def accounts(provider=None):
    """Live accounts with their estimate. Only the owner's balance decides anything here, never a switch."""
    rows = team.sql("""SELECT a.*, p.name AS owner FROM accounts a JOIN people p ON p.id = a.person
                       WHERE p.status != 'removed' AND (? IS NULL OR a.provider=?) ORDER BY a.id""", provider, provider)
    return [dict(a, left=left(a), limit=settings()[f"{a['provider']}_limit"], used=used(a)) for a in rows]


def account_for(provider, owner):
    """The video owner's own account, else the default one. Never chosen by balance."""
    rows = team.sql("""SELECT a.* FROM accounts a JOIN people p ON p.id = a.person
                       WHERE a.provider=? AND p.status='active' AND (a.person=? OR a.is_default=1)
                       ORDER BY a.person=? DESC LIMIT 1""", provider, owner, owner)
    return rows[0] if rows else None


def import_old(path):
    """Accounts used to be names in a file. It is read once and left in place."""
    if team.sql("SELECT 1 FROM settings WHERE name='imported'") or not path.exists(): return
    admin = team.sql("SELECT id FROM people WHERE role='admin'")[0]["id"]
    for plugin, a in json.loads(path.read_text(encoding="utf-8")).items():
        for x in a["list"]:
            add_account(provider_of(plugin), f"{x['label']} {x.get('owner', '')}".strip(), admin)
    team.sql("INSERT INTO settings (name, value) VALUES ('imported', '1')")


# ---------------------------------------------------------------- ledger
def used(a):
    return team.sql("SELECT COALESCE(SUM(credits), 0) AS n FROM spend WHERE account=? AND at>=?", a["id"], window(a["provider"]))[0]["n"]


def left(a):
    """A balance the owner typed replaces the limit until the next reset."""
    start = window(a["provider"])
    base, since = (a["real_left"], a["real_at"]) if a["real_at"] and a["real_at"] >= start else (settings()[f"{a['provider']}_limit"], start)
    return base - team.sql("SELECT COALESCE(SUM(credits), 0) AS n FROM spend WHERE account=? AND at>=?", a["id"], since)[0]["n"]


def set_left(aid, amount): team.sql("UPDATE accounts SET real_left=?, real_at=? WHERE id=?", amount, time.time(), aid)


def held(card):
    """A card stops here when its account has too little left, and it stays stopped until the reset or a real balance."""
    a = account(card.get("account_id"))
    return bool(a) and left(a) < settings()[card["plugin"]]


def spend(job, card):
    """Counts a finished card once, even if its file is dropped again. Returns what it cost."""
    if not card.get("account_id"): return 0
    cost = settings()[card["plugin"]]
    team.sql("INSERT OR IGNORE INTO spend (account, job, card, credits, at) VALUES (?,?,?,?,?)", card["account_id"], job, card["id"], cost, time.time())
    return cost


def report():
    """The admin dashboard, apart from what lives in the video folders."""
    start = today()
    latest = team.sql("SELECT state, COUNT(*) AS n FROM queue WHERE id IN (SELECT MAX(id) FROM queue GROUP BY job) GROUP BY state")
    return dict(
        states={r["state"]: r["n"] for r in latest},
        jobs_today=team.sql("SELECT COUNT(*) AS n FROM jobs WHERE created>=?", start)[0]["n"],
        accounts=accounts(),
        people=team.sql("""SELECT p.name, p.role, p.status,
                                  (SELECT COUNT(*) FROM jobs j WHERE j.owner=p.id AND j.created>=?) AS jobs_today,
                                  (SELECT COALESCE(SUM(s.credits), 0) FROM spend s JOIN jobs j ON j.id=s.job WHERE j.owner=p.id AND s.at>=?) AS credits_today
                           FROM people p WHERE p.status != 'removed' ORDER BY p.id""", start, start),
        audit=team.sql("SELECT at, who, action, job, account, credits FROM audit ORDER BY id DESC LIMIT 50"),
        settings=settings())
