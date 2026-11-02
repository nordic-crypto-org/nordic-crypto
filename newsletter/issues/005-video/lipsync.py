"""Lip-sync Anders Fjell to the TTS voice (Wav2Lip, CPU).

Run after tts.py. For every build/<seg>.mp3 writes build/anchor_<seg>.mp4 (1920x1080, 25 fps, silent,
LEAD s of still first frame, as anchor_clips.py does), which render.py uses instead of the frozen still.
Needs WAV2LIP=<checkout of Rudrabha/Wav2Lip> with checkpoints/wav2lip_gan.pth and the s3fd detector in place.
"""
import glob, os, subprocess, sys
import cv2, numpy as np, torch
W2L = os.environ['WAV2LIP']; sys.path.insert(0, W2L)
import audio, face_detection, librosa
from hparams import hparams as hp
# librosa>=0.10 takes keyword arguments only
audio._build_mel_basis = lambda: librosa.filters.mel(sr=hp.sample_rate, n_fft=hp.n_fft, n_mels=hp.num_mels, fmin=hp.fmin, fmax=hp.fmax)
from models import Wav2Lip
import content as C

B, FPS, W, H = 'build/', 25, 1920, 1080
LEAD = 0.20  # must match timeline.LEAD
MEL_STEP = 16
torch.set_num_threads(int(os.environ.get('LIPSYNC_THREADS', os.cpu_count())))

frame = cv2.resize(cv2.imread(C.ANCHOR_IMG), (W, H), interpolation=cv2.INTER_LANCZOS4)
det = face_detection.FaceAlignment(face_detection.LandmarksType._2D, flip_input=False, device='cpu')
r = det.get_detections_for_batch(np.array([frame]))[0]
if r is None: sys.exit('lipsync: no face found in ' + C.ANCHOR_IMG)
x1, y1, x2, y2 = max(0, r[0]), max(0, r[1]), min(W, r[2]), min(H, r[3] + 10)  # Wav2Lip default pads (0,10,0,0)
face = cv2.resize(frame[y1:y2, x1:x2], (96, 96))
masked = face.copy(); masked[48:] = 0
fin = np.concatenate([masked, face], axis=2)[None].astype(np.float32) / 255.

model = Wav2Lip()
sd = torch.load(os.path.join(W2L, 'checkpoints/wav2lip_gan.pth'), map_location='cpu')['state_dict']
model.load_state_dict({k.replace('module.', ''): v for k, v in sd.items()}); model.eval()

segs = sys.argv[1:] or sorted(os.path.basename(p)[:-4] for p in glob.glob(B + '*.mp3'))
for seg in segs:
    wav = B + seg + '.lipsync.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', B + seg + '.mp3', '-ac', '1', '-ar', '16000', wav], check=True)
    mel = audio.melspectrogram(audio.load_wav(wav, 16000)); os.remove(wav)
    n = int(mel.shape[1] / (80. / FPS)); chunks = []
    for i in range(n):
        s = int(i * 80. / FPS)
        chunks.append(mel[:, s:s + MEL_STEP] if s + MEL_STEP <= mel.shape[1] else mel[:, -MEL_STEP:])
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                           B + f'anchor_{seg}.mp4'], stdin=subprocess.PIPE)
    for _ in range(round(LEAD * FPS)): ff.stdin.write(frame.tobytes())
    with torch.no_grad():
        for i in range(0, n, 64):
            m = torch.from_numpy(np.stack(chunks[i:i + 64])[:, None].astype(np.float32))
            img = torch.from_numpy(np.repeat(fin, len(m), 0)).permute(0, 3, 1, 2)
            out = (model(m, img).permute(0, 2, 3, 1).numpy() * 255.).astype(np.uint8)
            for o in out:
                f = frame.copy(); f[y1:y2, x1:x2] = cv2.resize(o, (x2 - x1, y2 - y1)); ff.stdin.write(f.tobytes())
    ff.stdin.close(); ff.wait()
    if ff.returncode: sys.exit(f'lipsync: ffmpeg failed for {seg}')
    print(seg, n, 'frames', flush=True)
