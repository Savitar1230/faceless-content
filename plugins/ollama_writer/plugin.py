import json
import urllib.request

from ..base import Plugin


class OllamaWriterPlugin(Plugin):
    def run(self, inputs):
        # the limits stop JSON mode from generating forever, which once froze the whole queue
        body = {"model": self.manifest["model"], "prompt": inputs["prompt"], "stream": False,
                "options": {"num_predict": 6000, "num_ctx": 8192}}
        if inputs.get("json"): body["format"] = "json"
        req = urllib.request.Request("http://127.0.0.1:11434/api/generate", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:  # CPU models are slow, a script can take minutes
            return {"ok": True, "text": json.load(r)["response"]}
