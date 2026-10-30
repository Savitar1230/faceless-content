from ..card import CardPlugin


class MuseVoicePlugin(CardPlugin):
    def prompt(self, inputs):
        return (f"Voiceover only. Voice: {inputs['voice']}.\nRead exactly these words, nothing added, no music:\n\n{inputs['line']}\n\n"
                "Keep the same voice, pace and energy as every other line of this video.")
