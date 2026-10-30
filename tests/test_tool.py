"""Fast self-checks (no render). Run: .venv/Scripts/python.exe tests/test_tool.py"""
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
import pipeline, scenes
import spec as gate
from plugins import registry

good = json.loads((Path(__file__).parents[1] / "examples/calf.json").read_text(encoding="utf-8"))
assert gate.check(good) == [], gate.check(good)


def fails_with(text, change):
    s = copy.deepcopy(good)
    change(s)
    assert any(text in p for p in gate.check(s)), (text, gate.check(s))


fails_with("hook is", lambda s: s["blocks"][0].update(line="Today we are going to talk about how calves drink milk on a farm near you and why it matters a great deal."))
fails_with("number 99", lambda s: s["blocks"][1].update(line=s["blocks"][1]["line"].replace("first stomach", "99 stomachs")))
fails_with("words, want", lambda s: s["blocks"][2].update(line="Too short."))
fails_with("filler", lambda s: s["blocks"][2].update(line=s["blocks"][2]["line"] + " Basically."))
fails_with("add up", lambda s: s["blocks"][1]["scenes"].pop())
fails_with("long video needs at least", lambda s: s.update(format="long"))
fails_with("unknown picture", lambda s: s["blocks"][0]["scenes"][0].update(pic="nope"))
fails_with("pic must be", lambda s: s["blocks"][0]["scenes"][0].update(pic={"file": "x"}))
fails_with("needs a line", lambda s: s["blocks"][1].pop("line"))
print("script gate ok")

# plugins: card classes load with their own rules, and a card waits, then returns the dropped file
loaded = registry.load()
assert set(loaded) >= {"ollama_writer", "claude_writer", "kokoro_voice", "muse_voice", "flow_image", "muse_video", "hyperframes_render"}
assert "no text" in loaded["flow_image"].rules
with tempfile.TemporaryDirectory() as d:
    r = loaded["flow_image"].safe_run({"id": "a", "prompt": "a calf", "job_dir": d, "ratio": "9x16", "account": "Hasna flow"})
    assert r.get("waiting") and not r["ok"]
    card = json.loads((Path(d) / "cards/a.json").read_text(encoding="utf-8"))
    assert card["account"] == "Hasna flow" and "no text" in card["prompt"]
    (Path(d) / "inbox/a.png").write_bytes(b"x")
    r = loaded["flow_image"].safe_run({"id": "a", "prompt": "a calf", "job_dir": d})
    assert r["ok"] and not (Path(d) / "cards/a.json").exists()
print("plugins and job cards ok")

# all 3 ratios build a page, and every caption sits inside that ratio's frame
for ratio, (w, h) in scenes.SIZES.items():
    style = dict(json.loads((Path(__file__).parents[1] / "styles/news.json").read_text(encoding="utf-8")), head="h.ttf", body="b.ttf")
    media = {"real": ("video", "real.mp4", True), "drawn": ("image", "d.png", False), "belly": ("image", "b.png", False)}
    html = scenes.Page(good, ratio, style).build(media, [dict(w="hi", s=.2, e=.5)])
    assert f'data-duration="40"' in html and f'data-width="{w}"' in html
    L = scenes.LAYOUT[ratio]
    assert L["cap"] + 90 < h
    fx, fy, fh = L["fork"]
    assert fy + fh <= L["cap"], f"{ratio}: diagram runs into the captions"
    assert fx >= L["text"][0] + L["text"][2] - 40 or fy >= L["text"][1] + 120, f"{ratio}: diagram runs into the headline"
    assert fx + fh * scenes.VIEW[2] / scenes.VIEW[3] <= w, f"{ratio}: diagram off the frame"
g = scenes.caption_groups([dict(w=w, s=s, e=s) for w, s in [("low", 1), ("bucket.", 2), ("A", 3), ("calf", 9), ("has", 11), ("a", 12), ("switch", 13), ("now", 14)]])
assert [[x["w"] for x in c] for c in g] == [["low", "bucket."], ["A", "calf"], ["has", "a", "switch"], ["now"]], g
print("pages build for all ratios")
print("ALL CHECKS PASSED")
