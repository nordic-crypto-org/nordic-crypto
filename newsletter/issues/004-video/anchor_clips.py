"""Anchor-on-camera voice: build per-segment voice and picture from the talking clips of Anders Fjell.

Replaces tts.py for this cut. anchor_clips.json lists, per VO segment, the image-to-video clips
(generated from anchor-v1.jpg, verified with speech-to-text against the script), where the speech
ends in each, and sentence timings for the subtitles. Clips live in $CLIPS (default clips/).
Writes build/<seg>.mp3 + build/<seg>.json (as tts.py did) and build/anchor_<seg>.mp4
(1920x1080, 25 fps, silent, LEAD seconds of the still first frame in front so picture and voice
start together at the timeline's voice offset). Clips inside one segment join with a short crossfade.
"""
import json, os, subprocess, sys
sys.path.insert(0, '.'); import content as C
B = 'build/'; CL = os.environ.get('CLIPS', 'clips/'); M = json.load(open('anchor_clips.json'))
X = M['xfade']; LEAD = 0.20 + 0.0  # must match timeline.LEAD
FF = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y']
os.makedirs(B, exist_ok=True)
def dur(f): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]))
for seg, clips in M['clips'].items():
    assert seg in C.VO, seg
    assert ' '.join(c['text'] for c in clips) == C.VO[seg], f'{seg}: clip text differs from content.VO'
    ins, vf, af, bounds = [], [], [], []; off = 0.0
    for i, c in enumerate(clips):
        f = CL + c['file']; ins += ['-i', f]; last = i == len(clips) - 1
        # picture: keep the idle footage after the last line (the timeline tail), cut at the line end otherwise
        vend = min(dur(f), c['end'] + 1.6) if last else c['end']
        vf.append(f"[{i}:v]trim=0:{vend},setpts=PTS-STARTPTS,fps=25,scale=1920:1080:flags=lanczos,setsar=1,format=yuv420p[v{i}]")
        af.append(f"[{i}:a]atrim=0:{c['end']},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=mono,afade=t=out:st={c['end'] - 0.06}:d=0.06[a{i}]")
        bounds += [[off + a, off + z, t] for a, z, t in c['bounds']]
        off += c['end'] - X
    g = vf + af; vl, al = '[v0]', '[a0]'; acc = clips[0]['end']
    for i in range(1, len(clips)):
        g.append(f"{vl}[v{i}]xfade=transition=fade:duration={X}:offset={acc - X}[vx{i}]")
        g.append(f"{al}[a{i}]acrossfade=d={X}:c1=tri:c2=tri[ax{i}]"); vl, al = f'[vx{i}]', f'[ax{i}]'
        acc += clips[i]['end'] - X
    g.append(f"{vl}tpad=start_duration={LEAD}:start_mode=clone[vo]")
    subprocess.run(FF + ins + ['-filter_complex', ';'.join(g), '-map', '[vo]', '-an', '-c:v', 'libx264', '-preset', 'veryfast',
                               '-crf', '16', '-pix_fmt', 'yuv420p', B + f'anchor_{seg}.mp4',
                               '-map', al, '-c:a', 'libmp3lame', '-b:a', '192k', B + seg + '.mp3'], check=True)
    json.dump(bounds, open(B + seg + '.json', 'w'))
    print(seg, len(clips), 'clips', round(acc, 2), 's', flush=True)
