"""Original synthesized "Signal" jingle, stingers and music bed (numpy only), mixed under the edge-tts voice."""
import numpy as np, json, wave
SR = 48000; B = 'build/'
rng = np.random.default_rng(7)
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def env(n, a=0.01, d=0.2, s=0.6, r=0.2):
    t = np.arange(n) / SR; L = n / SR
    e = np.where(t < a, t / a, s + (1 - s) * np.exp(-(t - a) / max(d, 1e-3)))
    rel = np.clip((L - t) / r, 0, 1); return (e * rel).astype(np.float32)
def brass(m, dur, amp=0.3, bright=8):
    n = int(dur * SR); t = np.arange(n) / SR; f = mtof(m); y = np.zeros(n, np.float32)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t / 0.3, 0, 1)
    for k in range(1, bright + 1):
        for det in (-0.003, 0.003):
            y += np.sin(2 * np.pi * f * k * (1 + det) * vib * t + k) / (k ** 1.15)
    # brightness swell: higher harmonics grow with attack
    return (y * env(n, 0.03, 0.4, 0.55, 0.15) * amp / bright).astype(np.float32)
def timp(m, dur=1.2, amp=0.6):
    n = int(dur * SR); t = np.arange(n) / SR; f = mtof(m) * (1 + 0.15 * np.exp(-t * 30))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.5) + 0.3 * rng.standard_normal(n) * np.exp(-t * 40)
    return (y * amp).astype(np.float32)
def bandnoise(dur, f0, f1, amp=0.3):
    n = int(dur * SR); X = np.fft.rfft(rng.standard_normal(n)); fr = np.fft.rfftfreq(n, 1 / SR)
    # sweep realised by splitting into chunks with moving band
    y = np.zeros(n, np.float32); K = 24; L = n // K
    for i in range(K):
        fc = f0 * (f1 / f0) ** (i / (K - 1)); seg = rng.standard_normal(L + 400)
        S = np.fft.rfft(seg); ff = np.fft.rfftfreq(len(seg), 1 / SR); S *= np.exp(-((np.log(ff + 1) - np.log(fc)) ** 2) / 0.18)
        s = np.fft.irfft(S, len(seg))[:L + 400] * np.hanning(L + 400); y[i * L:i * L + L + 400][:len(s[:n - i * L])] += s[:n - i * L]
    y /= np.abs(y).max() + 1e-9; return (y * amp).astype(np.float32)
def cymbal(dur, amp=0.15, swell=False):
    n = int(dur * SR); t = np.arange(n) / SR; x = np.diff(rng.standard_normal(n + 1)).astype(np.float32)
    e = (t / dur) ** 2 if swell else np.exp(-t * 2.5); return x * e * amp
def put(buf, x, at):
    i = int(at * SR); j = min(len(buf), i + len(x)); buf[i:j] += x[:j - i]

# "Signal" bumper jingle (4.0 s): data blips and a riser into one wide A minor hit at JINGLE_HIT.
JINGLE_LEN, JINGLE_HIT = 4.0, 1.0
_srng = np.random.default_rng(11)
def _t(d): return np.arange(int(d * SR)) / SR
def _lp(x, fc):  # one-pole lowpass; fc scalar or per-sample
    fc = np.broadcast_to(fc, x.shape); a = np.exp(-2 * np.pi * fc / SR); y = np.zeros_like(x); s = 0.
    for i in range(len(x)): s = (1 - a[i]) * x[i] + a[i] * s; y[i] = s
    return y
def _saw(f, t, voices=5, det=.012):
    y = 0
    for k in range(voices):
        ff = f * (1 + det * (k - (voices - 1) / 2) / voices); y = y + 2 * ((ff * t + _srng.random()) % 1) - 1
    return y / voices
def _kick(amp=.9, d=.45):
    t = _t(d); f = 45 + 110 * np.exp(-t * 28)
    return (np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 7) * amp).astype(np.float32)
def _stab(notes, d, amp=.25, bright=6000, dec=6):
    t = _t(d); y = sum(_saw(mtof(m), t) for m in notes) / len(notes)
    y = _lp(y, 300 + bright * np.exp(-t * dec)); e = np.minimum(t / .004, 1) * np.exp(-t * 1.2) * np.clip((d - t) / .15, 0, 1)
    return (y * e * amp).astype(np.float32)
def _riser(d, f0=200, f1=9000, amp=.2):
    t = _t(d); fc = f0 * (f1 / f0) ** (t / d)
    return (_lp(_srng.standard_normal(len(t)), fc) * (t / d) ** 2 * amp * 3).astype(np.float32)
def _impact(amp=.8, d=2.0):
    t = _t(d); sub = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t * 12)) / SR) * np.exp(-t * 2.2)
    nz = _lp(_srng.standard_normal(len(t)), 1800) * np.exp(-t * 4) * 2
    return ((np.tanh(1.5 * sub) + nz * .5) * amp).astype(np.float32)
def jingle():
    y = np.zeros(int(JINGLE_LEN * SR), np.float32); hit = JINGLE_HIT
    for i, m in enumerate((86, 81, 86, 89, 86, 93)):
        t = _t(.07); put(y, (np.sin(2 * np.pi * mtof(m) * t) * np.exp(-t * 40) * .18).astype(np.float32), .08 + i * .11)
    put(y, _riser(.9, 150, 12000, .22), .1)
    put(y, _kick(.6, .2), hit - .22); put(y, _kick(.6, .2), hit - .11)
    put(y, _stab([45, 57, 60, 64, 69, 72], 3.0, .34, 5000, 2.2), hit)
    put(y, _impact(.95, 3.0), hit)
    t = _t(3.0); put(y, (_lp(np.diff(np.r_[0, _srng.standard_normal(len(t))]), 9000) * np.exp(-t * 1.5) * .12).astype(np.float32), hit)
    put(y, _stab([76, 81], .5, .14, 8000, 6), hit + .55)
    y = np.tanh(y / (np.abs(y).max() + 1e-9) * 1.3) / np.tanh(1.3)  # same soft clip as the approved reference
    return (y * 1.2).astype(np.float32)  # about the loudness of the old 5.5 s fanfare in the mix
def stinger():  # ~2.2 s section sting
    y = np.zeros(int(2.2 * SR), np.float32)
    put(y, bandnoise(0.5, 400, 7000, .18), 0.0)
    for m in (69, 74): put(y, brass(m, .2, .25), 0.45)
    for m in (62, 69, 74, 78): put(y, brass(m, 1.2, .16), 0.62)
    put(y, timp(38, 1.2, .6), 0.62); put(y, cymbal(1.2, .1), 0.62); return y
def endsting():
    y = np.zeros(int(4.0 * SR), np.float32)
    for m, b in ((74, 0), (69, .25), (74, .5)): put(y, brass(m, .3, .25), b)
    for m in (62, 66, 69, 74, 81): put(y, brass(m, 3.0, .18), 0.75)
    put(y, timp(38, 2.5, .7), .75); put(y, cymbal(3, .16), .75); return y

def bed_loop(bpm=116):  # 8 bars, D minor-ish pulse: Dm Bb F C
    beat = 60 / bpm; bar = 4 * beat; n = int(8 * bar * SR); y = np.zeros(n, np.float32)
    prog = [(50, (62, 65, 69)), (46, (58, 62, 65)), (41, (60, 65, 69)), (48, (60, 64, 67))] * 2
    for i, (bass, ch) in enumerate(prog):
        t0 = i * bar
        for k in range(8):  # eighth-note bass pulse
            nn = int(beat / 2 * SR * .9); tt = np.arange(nn) / SR; f = mtof(bass - 12)
            s = (np.sin(2 * np.pi * f * tt) + .35 * np.sin(4 * np.pi * f * tt) + .15 * np.sin(6 * np.pi * f * tt)) * np.exp(-tt * 9)
            put(y, (s * .22).astype(np.float32), t0 + k * beat / 2)
        for m in ch:  # soft pad
            nn = int(bar * SR); tt = np.arange(nn) / SR; f = mtof(m)
            s = sum(np.sin(2 * np.pi * f * h * (1 + d) * tt) / h ** 2 for h in (1, 2, 3) for d in (-.002, .002))
            put(y, (s * env(nn, .3, 1, .8, .4) * .035).astype(np.float32), t0)
        for k in range(16):  # ticking hats
            nn = int(.04 * SR); x = np.diff(rng.standard_normal(nn + 1)) * np.exp(-np.arange(nn) / SR * 120)
            put(y, (x * (.05 if k % 2 else .08)).astype(np.float32), t0 + k * beat / 4)
        put(y, timp(38, .5, .12), t0)  # soft downbeat
    return y

def chirp(dur=0.16, f0=620, f1=1480, amp=0.07):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 + (f1 - f0) * (t / dur)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return (y * amp).astype(np.float32)
def hot_stinger():  # short breaking-news stab, original intervals
    y = np.zeros(int(1.55 * SR), np.float32)
    put(y, bandnoise(0.28, 500, 9000, .22), 0.0)
    for m in (74, 81): put(y, brass(m, .16, .3, 9), 0.22)
    for m in (62, 69, 74, 81): put(y, brass(m, 1.05, .18, 8), 0.4)
    put(y, timp(38, 1.0, .55), 0.38); put(y, cymbal(1.0, .12), 0.38); return y
def super_jingle():  # ~8 s original fanfare. Not the Star Wars theme — a rising news button.
    y = np.zeros(int(8.0 * SR), np.float32)
    put(y, bandnoise(2.4, 140, 7800, .2), 0.0)
    put(y, cymbal(2.2, .07, True), 0.0)
    for t0, amp in ((0.45, .4), (1.05, .55), (1.65, .7)):
        put(y, timp(36, .7, amp), t0)
    motif = [(62, 1.85, .2, .3), (69, 2.12, .2, .32), (74, 2.4, .24, .34), (81, 2.72, .5, .38),
             (74, 3.45, .16, .26), (78, 3.7, .16, .28), (81, 3.95, .6, .36)]
    for m, t0, d, amp in motif:
        put(y, brass(m, d + .35, amp, 10), t0)
        put(y, brass(m - 12, d + .25, amp * .4, 5), t0)
    put(y, chirp(), 4.55); put(y, chirp(0.14, 740, 1600, .06), 5.05)
    for m in (50, 62, 66, 69, 74, 78, 81):
        put(y, brass(m, 2.5, .15, 8), 5.55)
    put(y, timp(38, 2.2, .85), 5.55); put(y, cymbal(2.3, .2), 5.55)
    put(y, bandnoise(0.22, 250, 8000, .16), 5.5)
    return y
def endsting_big():
    y = np.zeros(int(4.5 * SR), np.float32)
    for m, b in ((81, 0), (74, .18), (69, .36), (81, .54)): put(y, brass(m, .28, .22, 8), b)
    for m in (50, 62, 66, 69, 74, 81): put(y, brass(m, 3.2, .16, 8), 0.85)
    put(y, timp(38, 2.6, .75), .85); put(y, cymbal(3.2, .18), .85); return y

def render_mix(timeline_path, mix_path, style):
    tl = json.load(open(timeline_path)); FPS = tl['fps']; total = tl['total_frames'] / FPS
    N = int(total * SR); voice = np.zeros(N, np.float32); fx = np.zeros(N, np.float32)
    for s in tl['segs']:
        st = s['start_f'] / FPS
        if s['voff'] is not None:
            with wave.open(B + s['name'] + '.wav') as w: v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
            put(voice, v * 1.0, st + s['voff'])
        if style == 'flash':
            if s['kind'] == 'bumper': put(fx, super_jingle(), st)
            elif s['kind'] == 'section': put(fx, hot_stinger(), st)
            elif s['kind'] == 'sponsor':
                put(fx, hot_stinger() * .55, st); put(fx, chirp(.12, 500, 1200, .05), st + .15)
        else:
            if s['kind'] == 'bumper': put(fx, jingle(), st)
            elif s['kind'] == 'section': put(fx, stinger(), st)
            elif s['kind'] == 'sponsor': put(fx, stinger() * .6, st)
    end = tl['segs'][-1]
    put(fx, (endsting_big() if style == 'flash' else endsting()), end['start_f'] / FPS + max(0.2, end['dur'] - (4.6 if style == 'flash' else 4.2)))
    loop = bed_loop(128 if style == 'flash' else 116); LL = len(loop); bstart = tl['segs'][1]['start_f'] / FPS - 0.3; b0 = int(bstart * SR)
    hop = 480; nh = N // hop; vv = np.abs(voice[:nh * hop]).reshape(-1, hop).max(1); act = (vv > 0.02).astype(np.float32)
    act = np.clip(np.convolve(act, np.ones(40, np.float32) / 40, 'same') * 3, 0, 1).astype(np.float32)
    bed_gain = 0.40 if style == 'flash' else 0.32
    duck = 0.24 if style == 'flash' else 0.17
    gh = np.concatenate([bed_gain - duck * act, np.float32([bed_gain])]).astype(np.float32)
    fs = int((total - (4.2 if style == 'flash' else 5.0)) * SR); peak = 0.0
    chunks = []; CH = SR * 5
    for a in range(0, N, CH):
        z = min(N, a + CH); idx = np.arange(a, z)
        g = gh[np.minimum(idx // hop, len(gh) - 1)]
        b = np.where(idx >= b0, loop[(idx - b0) % LL], 0).astype(np.float32)
        fin = np.clip((idx - b0) / SR, 0, 1).astype(np.float32); fade = np.clip(1 - (idx - fs) / max(1, (N - fs)), 0, 1).astype(np.float32)
        fx_gain = 0.62 if style == 'flash' else 0.55
        m = voice[a:z] * 0.95 + fx[a:z] * fx_gain + b * g * fin * fade
        peak = max(peak, float(np.abs(m).max())); chunks.append(m)
    scale = 0.93 / peak if peak > 0.93 else 1.0
    with wave.open(mix_path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        for m in chunks: w.writeframes((np.clip(m * scale, -0.99, 0.99) * 32767).astype(np.int16).tobytes())
    print('mix', style, total, 'peak', round(peak, 3), 'scale', round(scale, 3), '->', mix_path)

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--timeline', default=B + 'timeline.json')
    ap.add_argument('--mix', default=B + 'mix.wav')
    ap.add_argument('--style', choices=('news', 'flash'), default='news')
    a = ap.parse_args()
    render_mix(a.timeline, a.mix, a.style)
