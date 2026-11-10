"""Lip-sync Anders Fjell to the TTS voice. One step for every issue.

Run from the issue directory, after tts.py and before timeline.py:

    WAV2LIP=/path/to/Wav2Lip python3 /path/to/newsletter/anchor_lipsync.py

Writes build/anchor_<seg>.mp4 (1920x1080, 25 fps, silent) for every voice
segment whose kind is listed in content.ON_CAMERA, plus a sidecar
build/anchor_<seg>.lipsync.json. The first LEAD seconds are the still plate,
then the mouth follows the voice. LEAD matches the issue timeline.

The mouth is measured on the raw frames. If it does not move, the clip is
deleted and the process exits non-zero. render.py refuses a segment that has
no successful sidecar, so a still cannot ship in place of Anders.

    python3 /path/to/newsletter/anchor_lipsync.py --check-rendered

measures the same mouth on the rendered segment (build/v_<seg>.mp4), after
overlays, and exits non-zero if that mouth is still. Issues with no
ANCHOR_IMG are not Anders cuts; both commands exit 0.
"""
import glob, hashlib, json, os, subprocess, sys

LEAD = 0.20  # must match the issue timeline LEAD
FPS, W, H = 25, 1920, 1080
MEL_STEP = 16
MOUTH_STD_MIN = 2.0       # mean temporal std of the mouth crop. A verified read measured ~4.2 against ~0 on the studio.
MOUTH_STILL_RATIO = 3.0   # mouth must move at least this many times more than a background patch
WAV2LIP_REV = "bac9a81e63ecc153202353372e5724b83d9e6322"
WEIGHTS = {
    "checkpoints/wav2lip_gan.pth": "ca9ab7b7b812c0e80a6e70a5977c545a1e8a365a6c49d5e533023c034d7ac3d8",
    "face_detection/detection/sfd/s3fd.pth": "619a31681264d3f7f7fc7a16a42cbbe8b23f31a256f75a366e5a1bcd59b33543",
}
B = "build"


def assert_mouth_moves(mouth_std, still_std, where=""):
    """Fail the build when the mouth is as still as the background."""
    where = f" ({where})" if where else ""
    if mouth_std < MOUTH_STD_MIN or mouth_std < still_std * MOUTH_STILL_RATIO:
        raise SystemExit(
            f"lipsync: mouth did not move{where}: mouth std {mouth_std:.2f}, "
            f"still region {still_std:.2f}. Refusing to ship a still of Anders Fjell."
        )


def mean_temporal_std(crops):
    import numpy as np
    stack = np.stack([np.asarray(c, dtype=np.float32) for c in crops], 0)
    if stack.shape[0] < 2:
        return 0.0
    return float(stack.std(axis=0).mean())


def mouth_box(face):
    x1, y1, x2, y2 = face
    return (x1, y1 + int((y2 - y1) * 0.55), x2, y2)


def background_box(face, w=W, h=H, size=64):
    """A patch that does not overlap the face. Top-left is the studio, clear of Anders."""
    x1, y1, x2, y2 = [int(v) for v in face]
    for x, y in ((16, 16), (w - size - 16, 16), (16, h - size - 16)):
        if x + size <= x1 or x >= x2 or y + size <= y1 or y >= y2:
            return (x, y, x + size, y + size)
    raise SystemExit(f"lipsync: face box {face} covers every background patch")


def clip_paths(build, name):
    return (os.path.join(build, f"anchor_{name}.mp4"), os.path.join(build, f"anchor_{name}.lipsync.json"))


def require_clip(build, name):
    """Path of a lip-sync clip that passed the mouth check. Exits if it is missing or rejected."""
    mp4, meta = clip_paths(build, name)
    if not (os.path.isfile(mp4) and os.path.getsize(mp4) > 1000 and os.path.isfile(meta)):
        raise SystemExit(
            f"anchor: {name} has no lip-sync clip ({mp4}). "
            "Refusing the still. Run newsletter/anchor_lipsync.py after tts.py."
        )
    with open(meta, encoding="utf-8") as fh:
        info = json.load(fh)
    if not info.get("ok"):
        raise SystemExit(f"anchor: {name} lip-sync was rejected. Refusing the still.")
    return mp4


class Plate:
    """Sequential reader for one lip-sync clip. Holds the last frame through the tail."""

    def __init__(self, build, name, w, h, fps):
        path = require_clip(build, name)
        self.w, self.h = w, h
        self.p = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-threads", "1", "-i", path, "-vf",
             f"fps={fps},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=w * h * 3)
        self.i, self.im = -1, None

    def at(self, i):
        from PIL import Image
        while self.i < i and self.p:
            b = self.p.stdout.read(self.w * self.h * 3)
            if len(b) < self.w * self.h * 3:
                self.p.stdout.close()
                self.p.wait()
                self.p = None
                break
            self.im = Image.frombytes("RGB", (self.w, self.h), b)
            self.i += 1
        if self.im is None:
            raise SystemExit("anchor: lip-sync clip produced no frames")
        return self.im.copy()


def _load_content():
    sys.path.insert(0, os.getcwd())
    import content
    return content


def on_camera_names(content, only=()):
    if not getattr(content, "ANCHOR_IMG", None):
        return []
    if not getattr(content, "ON_CAMERA", None):
        raise SystemExit("lipsync: content.ON_CAMERA must list the kinds where Anders is on camera")
    kinds = set(content.ON_CAMERA)
    names = [name for name, kind, _extra in content.TIMELINE if kind in kinds]
    if only:
        unknown = [n for n in only if n not in names]
        if unknown:
            raise SystemExit("lipsync: not an on-camera segment: " + ", ".join(unknown))
        names = [n for n in names if n in only]
    if not names:
        raise SystemExit("lipsync: no on-camera voice segments")
    return names


def _check_weights(root):
    for rel, want in WEIGHTS.items():
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            raise SystemExit(f"lipsync: missing weight {path}")
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != want:
            raise SystemExit(f"lipsync: weight {rel} does not match the pinned sha256")


def _crop(frame, box):
    x1, y1, x2, y2 = box
    return frame[y1:y2, x1:x2].copy()


def sync(content, only=()):
    import cv2
    import librosa
    import numpy as np
    import torch
    w2l = os.environ.get("WAV2LIP")
    if not w2l:
        raise SystemExit("lipsync: WAV2LIP is not set. Refusing to render Anders without a mouth.")
    _check_weights(w2l)
    sys.path.insert(0, w2l)
    import audio
    import face_detection
    from hparams import hparams as hp
    # librosa>=0.10 takes keyword arguments only
    audio._build_mel_basis = lambda: librosa.filters.mel(
        sr=hp.sample_rate, n_fft=hp.n_fft, n_mels=hp.num_mels, fmin=hp.fmin, fmax=hp.fmax)
    from models import Wav2Lip

    img = content.ANCHOR_IMG
    if not os.path.isfile(img):
        raise SystemExit(f"lipsync: anchor image missing: {img}")
    os.makedirs(B, exist_ok=True)
    names = on_camera_names(content, only)
    missing = [n for n in names if not os.path.isfile(os.path.join(B, n + ".mp3"))]
    if missing:
        raise SystemExit("lipsync: missing voice after tts.py: " + ", ".join(missing))

    torch.set_num_threads(int(os.environ.get("LIPSYNC_THREADS", os.cpu_count() or 1)))
    plate = cv2.resize(cv2.imread(img), (W, H), interpolation=cv2.INTER_LANCZOS4)
    if plate is None:
        raise SystemExit(f"lipsync: could not read {img}")
    det = face_detection.FaceAlignment(face_detection.LandmarksType._2D, flip_input=False, device="cpu")
    found = det.get_detections_for_batch(np.array([plate]))[0]
    if found is None:
        raise SystemExit("lipsync: no face found in " + img)
    face = (max(0, int(found[0])), max(0, int(found[1])), min(W, int(found[2])), min(H, int(found[3]) + 10))
    mouth = mouth_box(face)
    still = background_box(face)
    x1, y1, x2, y2 = face
    face96 = cv2.resize(plate[y1:y2, x1:x2], (96, 96))
    masked = face96.copy()
    masked[48:] = 0
    fin = np.concatenate([masked, face96], axis=2)[None].astype(np.float32) / 255.0

    model = Wav2Lip()
    try:
        sd = torch.load(os.path.join(w2l, "checkpoints/wav2lip_gan.pth"), map_location="cpu", weights_only=False)
    except TypeError:
        sd = torch.load(os.path.join(w2l, "checkpoints/wav2lip_gan.pth"), map_location="cpu")
    model.load_state_dict({k.replace("module.", ""): v for k, v in sd["state_dict"].items()})
    model.eval()
    batch = int(os.environ.get("LIPSYNC_BATCH", "64"))

    for seg in names:
        mp4, meta = clip_paths(B, seg)
        if os.path.exists(meta):
            os.remove(meta)
        wav = os.path.join(B, seg + ".lipsync.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(B, seg + ".mp3"),
                        "-ac", "1", "-ar", "16000", wav], check=True)
        mel = audio.melspectrogram(audio.load_wav(wav, 16000))
        os.remove(wav)
        n = int(mel.shape[1] / (80.0 / FPS))
        if n < 8:
            raise SystemExit(f"lipsync: {seg} is too short to lip-sync ({n} frames)")
        chunks = []
        for i in range(n):
            s = int(i * 80.0 / FPS)
            chunks.append(mel[:, s:s + MEL_STEP] if s + MEL_STEP <= mel.shape[1] else mel[:, -MEL_STEP:])
        ff = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
             "-pix_fmt", "yuv420p", mp4], stdin=subprocess.PIPE)
        mouths, stills = [], []
        try:
            for _ in range(round(LEAD * FPS)):
                ff.stdin.write(plate.tobytes())
            with torch.no_grad():
                for i in range(0, n, batch):
                    m = torch.from_numpy(np.stack(chunks[i:i + batch])[:, None].astype(np.float32))
                    img_b = torch.from_numpy(np.repeat(fin, len(m), 0)).permute(0, 3, 1, 2)
                    out = (model(m, img_b).permute(0, 2, 3, 1).numpy() * 255.0).astype(np.uint8)
                    for o in out:
                        f = plate.copy()
                        f[y1:y2, x1:x2] = cv2.resize(o, (x2 - x1, y2 - y1))
                        ff.stdin.write(f.tobytes())
                        mouths.append(_crop(f, mouth))
                        stills.append(_crop(f, still))
            ff.stdin.close()
            rc = ff.wait()
            if rc:
                raise SystemExit(f"lipsync: ffmpeg failed for {seg} (exit {rc})")
            mouth_std, still_std = mean_temporal_std(mouths), mean_temporal_std(stills)
            assert_mouth_moves(mouth_std, still_std, seg)
        except BaseException:
            try:
                ff.stdin.close()
            except Exception:
                pass
            try:
                ff.kill()
            except Exception:
                pass
            ff.wait()
            if os.path.exists(mp4):
                os.remove(mp4)
            raise
        with open(meta, "w", encoding="utf-8") as fh:
            json.dump({
                "ok": True, "frames": n, "mouth_std": round(mouth_std, 3), "still_std": round(still_std, 3),
                "face": list(face), "mouth": list(mouth), "still": list(still),
            }, fh)
        print(f"{seg}: {n} frames, mouth std {mouth_std:.2f}, still region {still_std:.2f}", flush=True)
    return 0


def _video_size(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", path], text=True).strip()
    w, h = out.split(",")
    return int(w), int(h)


def read_frames(path, start, dur):
    import numpy as np
    w, h = _video_size(path)
    raw = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", path,
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    frame = w * h * 3
    n = len(raw) // frame
    if n < 2:
        raise SystemExit(f"lipsync: {path} has too few frames at {start:.2f}s")
    return [np.frombuffer(raw[i * frame:(i + 1) * frame], dtype=np.uint8).reshape(h, w, 3) for i in range(n)]


def measure_window(path, mouth, still, start=1.0, dur=1.0):
    frames = read_frames(path, start, dur)
    return mean_temporal_std([_crop(f, mouth) for f in frames]), mean_temporal_std([_crop(f, still) for f in frames])


def check_rendered(content, build=B):
    """Mouth motion on the pictures render.py actually wrote."""
    timeline = os.path.join(build, "timeline.json")
    if not os.path.isfile(timeline):
        raise SystemExit("lipsync: no timeline; cannot check the rendered mouth")
    with open(timeline, encoding="utf-8") as fh:
        rendered = {s["name"] for s in json.load(fh)["segs"]}
    names = [n for n in on_camera_names(content) if n in rendered]
    if not names:
        raise SystemExit("lipsync: the timeline has no on-camera Anders segment to check")
    for name in names:
        _mp4, meta = clip_paths(build, name)
        video = os.path.join(build, f"v_{name}.mp4")
        if not os.path.isfile(meta) or not os.path.isfile(video):
            raise SystemExit(f"lipsync: {name} was rendered without a checked lip-sync clip")
        with open(meta, encoding="utf-8") as fh:
            info = json.load(fh)
        mouth_std, still_std = measure_window(video, tuple(info["mouth"]), tuple(info["still"]))
        assert_mouth_moves(mouth_std, still_std, f"rendered {name}")
        print(f"rendered {name}: mouth std {mouth_std:.2f}, still region {still_std:.2f}", flush=True)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    check = "--check-rendered" in argv
    if check:
        argv.remove("--check-rendered")
    content = _load_content()
    if not getattr(content, "ANCHOR_IMG", None):
        print("lipsync: no Anders Fjell anchor in this issue")
        return 0
    if check:
        return check_rendered(content)
    return sync(content, argv)


if __name__ == "__main__":
    sys.exit(main())
