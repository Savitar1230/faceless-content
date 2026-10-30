from pathlib import Path

import soundfile as sf

from ..base import Plugin

ROOT = Path(__file__).parents[2]


class KokoroVoicePlugin(Plugin):
    tts = None  # the model takes seconds to load, so load it once

    def run(self, inputs):
        if KokoroVoicePlugin.tts is None:
            from kokoro_onnx import Kokoro
            KokoroVoicePlugin.tts = Kokoro(str(ROOT / "models/kokoro-v1.0.onnx"), str(ROOT / "models/voices-v1.0.bin"))
        x, sr = self.tts.create(inputs["line"], voice=inputs["voice"], speed=inputs.get("speed", 0.8), lang="en-us")
        sf.write(inputs["out"], x, sr)
        return {"ok": True, "path": inputs["out"]}
