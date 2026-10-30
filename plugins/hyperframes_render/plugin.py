import shutil
import subprocess
from pathlib import Path

from ..base import Plugin

ROOT = Path(__file__).parents[2]


class HyperframesRenderPlugin(Plugin):
    def run(self, inputs):
        npx = shutil.which("npx")
        if not npx: return {"ok": False, "error": "Node.js is not installed"}
        p = subprocess.run([npx, "hyperframes", "render", inputs["dir"], "-o", inputs["out"], "--strict", "--quiet"],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode or not Path(inputs["out"]).exists():
            return {"ok": False, "error": (p.stdout + p.stderr)[-600:]}
        return {"ok": True, "path": inputs["out"]}
