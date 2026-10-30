# Rumi Longform

A script goes in, a finished editorial video comes out, in 9:16, 16:9 and 3:4. Runs on your own PC.

## Start it

Double-click `run.bat`, or run `.venv\Scripts\python.exe app.py`, then open http://127.0.0.1:5895

First-time setup needs Python, Node.js and FFmpeg on the PC:

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
npm install
```

Put `kokoro-v1.0.onnx` and `voices-v1.0.bin` in `models/` (from the kokoro-onnx releases on GitHub).
For the free local writer, start Ollama and run `ollama pull qwen2.5:7b`.

## Team

The first start prints your admin key in the black window. Copy it, it is shown once. If you lose it, run `.venv/Scripts/python.exe team.py` on this PC for a new one.

The **Team** tab adds people and makes keys. A key is a login for this app only: it never signs anyone in to Flow or Muse, and only its hash is stored. Teammates see their own videos. The admin sees everything. The assistant key works as `Authorization: Bearer <key>`, and it cannot make keys, remove people or approve scripts.

## Queue and batches

Work is saved in `data/app.db`, so a restart loses nothing. Queued videos carry on, and a video that was running shows "Stopped by a restart" with a Run again button. Nothing retries by itself.

Two lines run side by side: writing, and making (voice, captions, render). Each takes one video at a time. Change the numbers in `LIMITS` in `work.py` only after timing them on the host PC.

Statuses are queued, running, waiting (for a person), done and failed. Each video can be paused, and the admin can pause the whole queue. Work already running finishes.

**New video** also has templates, which save the format, writer, sizes and facts for the whole team, and a box for many videos: one per line as `topic | facts | source links | owner`. If any line is bad, nothing is queued. A person still approves each script, or presses **Approve all ready**.

## How a video is made

1. **New video:** give a topic and facts. The writer plugin drafts the script and storyboard.
2. **Edit script**, then **Approve and make**.
3. The script check runs: hook length, word counts, plain words, and every number must be in your facts.
4. Voice, pictures, captions, render per size, final check. Each step is a plugin in `plugins/`.
5. Flow and Muse have no API, so they use **job cards**: copy the prompt, run it there, drop the file back in. The app checks each clip. A bad clip gets one retry with a fixed prompt, then the still image is used and the video is flagged.

Accounts in the app are names only. Sign in to Flow and Muse in your browser. The app holds no passwords and never switches accounts by itself.

## Cards and credits

A card goes to the video owner's own account, or else the default account, and appears under **Cards** for the person who owns that account. Each person has one account per tool. Anyone who wants to help ticks **I can take handed cards**, and the admin can then hand them a card to run on their own account.

Credits are an **estimate**: finished cards times the cost table on the **Dashboard**, because Flow and Muse show balances only on their own pages. Check the Flow image and Muse voice costs after a real card, because the defaults are guesses. When an account runs out its cards wait, with the prompt hidden. The owner can type the real balance under **Cards**. The app never moves a card to another account by itself.

A generated file that passes is kept in `library/`, so the same prompt never costs credits twice.

The Dashboard also has the audit log, the keep rule for finished videos, and the hours Ollama may run. Old videos are listed for you to delete, never deleted by themselves.

## Files

`app.py` the app · `team.py` people and keys · `work.py` the queue · `books.py` accounts, credits and the audit log · `pipeline.py` the stages · `spec.py` script check · `scenes.py` layouts for 3 sizes ·
`checks.py` clip and final checks · `plugins/` one folder per tool · `examples/calf.json` a full example ·
`spike/` the faster skia engine, kept as a backup for slow PCs.

Tests: run `tests/test_tool.py`, `tests/test_team.py`, `tests/test_queue.py` and `tests/test_books.py` with `.venv/Scripts/python.exe`
