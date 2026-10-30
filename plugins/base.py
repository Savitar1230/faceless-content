"""The one interface every LOV Bot plugin follows. See vision/PLUGIN_SPEC.md."""
import logging

log = logging.getLogger("lov.plugins")


class Plugin:
    def __init__(self, manifest):
        self.manifest = manifest
        self.name = manifest["name"]
        self.kind = manifest["kind"]
        self.enabled = True  # registry turns this off when a needed key is missing

    def run(self, inputs):
        """Take a dict, return a dict with "ok": True/False. Each plugin writes this."""
        raise NotImplementedError

    def safe_run(self, inputs):
        """What Rumi calls: never crashes the bot, always returns a dict."""
        if not self.enabled:
            return {"ok": False, "error": f"{self.name} is off (needs an API key)"}
        try:
            return self.run(inputs)
        except Exception as e:
            log.exception("plugin %s failed", self.name)
            return {"ok": False, "error": str(e)}
