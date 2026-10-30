from ..card import CardPlugin


class MuseVideoPlugin(CardPlugin):
    rules = ("\n\nFixed rules: start from the attached image and keep its look. One continuous shot, no cuts. One action only, "
             "everything else stays still. Motion starts on frame 1. No text, letters, numbers, logos or captions. "
             "No new objects. Same colours and clothing throughout. No speech and no music.")
