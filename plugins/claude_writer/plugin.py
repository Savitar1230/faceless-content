import shutil
import subprocess

from ..base import Plugin


class ClaudeWriterPlugin(Plugin):
    def run(self, inputs):
        exe = shutil.which("claude")
        if not exe: return {"ok": False, "error": "Claude Code is not installed on this PC"}
        # no tools: it only writes text, and a prompt from a teammate must never reach files on this PC
        p = subprocess.run([exe, "-p", "--tools", "", "--output-format", "text"], input=inputs["prompt"], capture_output=True,
                           text=True, encoding="utf-8", timeout=600)
        if p.returncode: return {"ok": False, "error": p.stderr[-300:]}
        return {"ok": True, "text": p.stdout}
