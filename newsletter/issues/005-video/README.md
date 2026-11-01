# Nordic Crypto issue #5 — newsreel

Presenter: fictional anchor **Anders Fjell** (`anchor-v1.jpg`: grey-haired man, navy suit, teal tie, teal/gold studio).
Opens with "Good morning, I'm Anders Fjell, and this is Nordic Crypto." and an Anders Fjell lower third.
Signs off with "I'm Anders Fjell. See you next week."
Title card: **Nordic Crypto #5**.

Voice for this cut: edge-tts `en-GB-ThomasNeural` at `+22%` for the whole read (one voice).
Anders stays on camera from the reference still, with a slow push-in, under the overlays.
`anchor_clips.py` is the on-camera lip-sync path from issue #4 v2. This issue has no verified
talking clips, so the render uses the still rather than mixing a generated voice with TTS.

Brand: **Nordic Crypto**. Sign-off card: **The Nordic Crypto team**.
Other outlets' logos only on that story's `Source:` chip, unchanged, at most 10% of the frame width.
Never on `thumbnail.png`, the title card, the intro or the outro.

```bash
python3 -m pip install -r requirements.txt
python3 tts.py          # or anchor_clips.py when clips/ and anchor_clips.json exist
python3 timeline.py
python3 audio.py --style news --timeline build/timeline.json --mix build/mix.wav
bash render_all.sh
bash concat.sh build/timeline.json build build/mix.wav build/nordic-crypto-5-newsreel.mp4
python3 render.py thumb
```
