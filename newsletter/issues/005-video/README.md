# Nordic Crypto issue #5 — newsreel

Presenter: fictional anchor **Anders Fjell** (`anchor-v1.jpg`: grey-haired man, navy suit, teal tie, teal/gold studio).
Opens with "Good morning, I'm Anders Fjell, and this is Nordic Crypto." and an Anders Fjell lower third.
Signs off with "I'm Anders Fjell. See you next week."
Title card: **Nordic Crypto #5**.

Voice for this cut: edge-tts `en-GB-ThomasNeural` at `+22%` for the whole read (one voice).
Anders is on camera from the reference still, lip-synced to the TTS voice: `lipsync.py` (Wav2Lip, CPU)
writes `build/anchor_<seg>.mp4` for every voice segment, and `render.py` uses those instead of the still.
Without them `render.py` falls back to the frozen still (push-in only, no mouth motion) — never ship that.

Brand: **Nordic Crypto**. Sign-off card: **The Nordic Crypto team**.
Other outlets' logos only on that story's `Source:` chip, unchanged, at most 10% of the frame width.
Never on `thumbnail.png`, the title card, the intro or the outro.

```bash
python3 -m pip install -r requirements.txt
python3 tts.py          # or anchor_clips.py when clips/ and anchor_clips.json exist
WAV2LIP=/path/to/Wav2Lip python3 lipsync.py   # after tts.py; see the workflow for the pinned checkout and weights
python3 timeline.py
python3 audio.py --style news --timeline build/timeline.json --mix build/mix.wav
bash render_all.sh
bash concat.sh build/timeline.json build build/mix.wav build/nordic-crypto-5-newsreel.mp4
python3 render.py thumb
```
