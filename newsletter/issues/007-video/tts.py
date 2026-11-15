import asyncio, json, os, re, subprocess, sys, edge_tts
from edge_tts import communicate as _comm
from edge_tts.constants import TRUSTED_CLIENT_TOKEN
# speech.platform.bing.com answers the synthesis socket with 403 (since October 2026).
# Microsoft Edge 155 uses this host, which still accepts the same edge-tts token and voice.
_comm.WSS_URL = ("wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
                 f"?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}")
sys.path.insert(0, '.'); import content as C
B = 'build/'
# Issue #6's sign-off failed the 1.0–2.0s mouth gate: edge-tts left a long pause
# between the two sentences, and that pause was the window. Join them closely.
SIGNOFF_GAP = 0.09
FF = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y']

def _dur(path):
    return float(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], text=True))

def _sentences(text):
    parts = [p.strip() for p in re.findall(r'[^.!?]+[.!?]+', text) if p.strip()]
    return parts or [text.strip()]

async def _mp3(text, path):
    last = None
    for _attempt in range(3):
        try:
            c = edge_tts.Communicate(text, C.VOICE, rate=C.RATE, boundary='SentenceBoundary')
            with open(path, 'wb') as f:
                async for ch in c.stream():
                    if ch['type'] == 'audio': f.write(ch['data'])
            if os.path.getsize(path) > 500: return
        except Exception as e:
            last = e
    raise SystemExit(f'tts failed for {text!r}: {last}')

def _trim(src, dst):
    # Drop the long head and tail edge-tts adds. Keep a breath, not a sentence pause.
    subprocess.run(FF + ['-i', src, '-af',
        'silenceremove=start_periods=1:start_silence=0.02:start_threshold=-36dB:'
        'stop_periods=-1:stop_silence=0.05:stop_threshold=-36dB',
        '-ar', '48000', '-ac', '1', dst], check=True)

async def tight(name, text, gap=SIGNOFF_GAP):
    """Two spoken sentences with a short join, so speech covers the 1.0–2.0s gate."""
    parts = _sentences(text)
    os.makedirs(B, exist_ok=True)
    wavs = []
    for i, part in enumerate(parts):
        mp3, wav = f'{B}{name}.{i}.mp3', f'{B}{name}.{i}.wav'
        await _mp3(part, mp3)
        _trim(mp3, wav)
        wavs.append(wav)
        os.remove(mp3)
    bounds, at = [], 0.0
    for i, (part, wav) in enumerate(zip(parts, wavs)):
        d = _dur(wav)
        bounds.append((round(at, 4), round(at + d, 4), part))
        at += d + (gap if i < len(wavs) - 1 else 0)
    cmd = FF + [x for w in wavs for x in ('-i', w)]
    if len(wavs) == 1:
        cmd += [B + name + '.mp3']
    else:
        chain = []
        for i in range(len(wavs) - 1):
            chain.append(f'[{i}:a]apad=pad_dur={gap}[a{i}]')
        ins = ''.join(f'[a{i}]' for i in range(len(wavs) - 1)) + f'[{len(wavs) - 1}:a]'
        chain.append(f'{ins}concat=n={len(wavs)}:v=0:a=1[a]')
        cmd += ['-filter_complex', ';'.join(chain), '-map', '[a]', '-ar', '48000', '-c:a', 'libmp3lame', '-q:a', '2', B + name + '.mp3']
    subprocess.run(cmd, check=True)
    for w in wavs: os.remove(w)
    json.dump(bounds, open(B + name + '.json', 'w'))
    print(name, len(bounds), 'tight', flush=True)

async def main():
    names = sys.argv[1:] or list(C.VO)
    os.makedirs(B, exist_ok=True)
    for n in names:
        t = C.VO[n]
        if n == 'signoff' and len(_sentences(t)) > 1:
            await tight(n, t)
            continue
        for attempt in range(3):
            try:
                c = edge_tts.Communicate(t, C.VOICE, rate=C.RATE, boundary="SentenceBoundary"); bounds = []
                with open(B + n + '.mp3', 'wb') as f:
                    async for ch in c.stream():
                        if ch['type'] == 'audio': f.write(ch['data'])
                        elif ch['type'].endswith('Boundary'): bounds.append((ch['offset']/1e7, (ch['offset']+ch['duration'])/1e7, ch['text']))
                json.dump(bounds, open(B + n + '.json', 'w')); print(n, len(bounds), flush=True); break
            except Exception as e: print('retry', n, e)
        else:
            raise SystemExit('tts failed: ' + n)
asyncio.run(main())
