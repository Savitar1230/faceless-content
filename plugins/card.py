"""Job cards: for tools with no API. The app writes the prompt, a person (or Muse in chat) runs it
and drops the file in. No auto-clicking: Google's and Meta's terms ban automated access."""
import json
from pathlib import Path

from .base import Plugin


class CardPlugin(Plugin):
    rules = ""  # fixed rules added to every prompt, so the generator cannot drift

    def prompt(self, inputs):
        return inputs["prompt"] + self.rules

    def run(self, inputs):
        job = Path(inputs["job_dir"])
        (job / "cards").mkdir(exist_ok=True)
        (job / "inbox").mkdir(exist_ok=True)
        card_path = job / "cards" / f"{inputs['id']}.json"
        for ext in self.manifest["card_ext"]:
            done = job / "inbox" / f"{inputs['id']}.{ext}"
            if done.exists():
                card_path.unlink(missing_ok=True)
                return {"ok": True, "path": str(done)}
        card = {"id": inputs["id"], "plugin": self.name, "title": self.manifest["title"], "prompt": self.prompt(inputs),
                "ratio": inputs.get("ratio"), "start_image": inputs.get("start_image"), "account": inputs.get("account"),
                "try": inputs.get("try", 1), "ext": self.manifest["card_ext"]}
        card_path.write_text(json.dumps(card, indent=1), encoding="utf-8")
        return {"ok": False, "waiting": True, "error": f"waiting for {inputs['id']}"}
