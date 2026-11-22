# Nordic Crypto issue #8 — newsreel

Presenter: fictional anchor **Anders Fjell** (`anchor-v1.jpg`: grey-haired man, navy suit, teal tie, teal/gold studio).
Opens with "Good morning, I'm Anders Fjell, and this is Nordic Crypto." and an Anders Fjell lower third.
Signs off with "I'm Anders Fjell. See you next week."
Title card: **Nordic Crypto #8**.

Voice for this cut: edge-tts `nb-NO-FinnNeural` at `+22%` for the whole read (one voice).
The sign-off is two sentences with a short join, so the mouth is moving through the 1.0–2.0s check.
Anders is on camera for the open, the headlines, every story, the close and the sign-off.
`newsletter/anchor_lipsync.py` (Wav2Lip, CPU) writes `build/anchor_<seg>.mp4` for those
segments. `render.py` uses that clip. If the mouth does not move, or the clip is missing,
the build exits. The reference still is the face plate, not a shot that can ship.

Brand: **Nordic Crypto**. Sign-off card: **The Nordic Crypto team**.
Other outlets' logos only on that story's `Source:` chip, unchanged, at most 10% of the frame width.
Never on `thumbnail.png`, the title card, the intro or the outro.

```bash
python3 -m pip install -r requirements.txt
python3 tts.py
WAV2LIP=/path/to/Wav2Lip python3 ../../../newsletter/anchor_lipsync.py
python3 timeline.py
python3 audio.py --style news --timeline build/timeline.json --mix build/mix.wav
bash render_all.sh
bash concat.sh build/timeline.json build build/mix.wav build/nordic-crypto-8-newsreel.mp4
python3 render.py thumb
```
