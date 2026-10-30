"""Finds and loads plugins: every plugins/<folder>/manifest.json + plugin.py."""
import importlib
import json
from pathlib import Path

from .base import Plugin, log

HERE = Path(__file__).parent
KINDS = ("video", "image", "music", "text", "social", "voice", "render")
PLUGINS = {}  # name -> Plugin instance


def load(has_key=lambda name: False):
    """Scan plugin folders. has_key(name) -> True if the user saved a key for it."""
    PLUGINS.clear()
    for manifest_path in sorted(HERE.glob("*/manifest.json")):
        folder = manifest_path.parent.name
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("kind") not in KINDS:
                raise ValueError(f"bad kind {manifest.get('kind')!r}")
            module = importlib.import_module(f"{__package__}.{folder}.plugin")
            cls = next(c for c in vars(module).values()
                       if isinstance(c, type) and issubclass(c, Plugin) and c.__module__ == module.__name__)
            plugin = cls(manifest)
            plugin.enabled = not manifest.get("needs_api_key") or has_key(plugin.name)
            PLUGINS[plugin.name] = plugin
        except Exception:
            log.exception("skipping plugin folder %s", folder)  # one bad plugin never stops the rest
    return PLUGINS


def list(kind=None):
    """All plugins (or one kind). Disabled ones are included; check .enabled."""
    return [p for p in PLUGINS.values() if kind is None or p.kind == kind]


def get(name):
    return PLUGINS.get(name)
