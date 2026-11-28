# Nordic Crypto issue #6 — newsreel

Presenter: fictional anchor **Anders Fjell** (`anchor-v1.jpg`: grey-haired man, navy suit, teal tie, teal/gold studio).
Opens with "Good morning, I'm Anders Fjell, and this is Nordic Crypto." and an Anders Fjell lower third.
Signs off with "I'm Anders Fjell. See you next week."
Title card: **Nordic Crypto #6**.

Voice for this cut: edge-tts `en-GB-ThomasNeural` at `+22%` for the whole read (one voice).
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
bash concat.sh build/timeline.json build build/mix.wav build/nordic-crypto-6-newsreel.mp4
python3 render.py thumb
```

## Vertical cut for Instagram Reels

Same timeline, narration and mix as the landscape file; 1080×1920, 30 fps, H.264/AAC, laid out for portrait
(centred logo, stacked headlines and story cards, ticker above the Reels caption area).
The "this week" card uses `TONIGHT_LABEL` (`THIS WEEK` on this issue).

```bash
VERTICAL=1 SEGDIR=build/vertical/ bash render_all.sh
bash concat.sh build/timeline.json build/vertical build/mix.wav build/nordic-crypto-6-newsreel-vertical.mp4
VERTICAL=1 python3 render.py thumb   # thumbnail-vertical.png
```

Upload it onto the existing release `newsletter-006-newsreel-1`. Do not replace `nordic-crypto-6-newsreel.mp4`.
Record the file as `video_vertical`:

```bash
gh release upload newsletter-006-newsreel-1 build/nordic-crypto-6-newsreel-vertical.mp4
python3 video_meta.py 006 video_vertical build/nordic-crypto-6-newsreel-vertical.mp4 \
  https://github.com/nordic-crypto-org/nordic-crypto/releases/download/newsletter-006-newsreel-1/nordic-crypto-6-newsreel-vertical.mp4
```

`video_meta.py` checks H.264, 1080×1920, 30 fps and at most 15 minutes, then writes duration, size and sha256.
Copy `thumbnail-vertical.png` into `newsletter/published/006/`. It is the Instagram Reel cover.

`.github/workflows/newsreel-vertical.yml` is portrait-only `workflow_dispatch`. It renders this cut and uploads
`nordic-crypto-N-newsreel-vertical.mp4` to the existing release. It does not render the landscape file and it does not post.
