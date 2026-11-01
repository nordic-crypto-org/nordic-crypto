#!/usr/bin/env python3
"""Newsreel intro: the "Signal" jingle, the bumper length and the intro hit agree. No network.
python3 tests/test_newsreel_jingle.py"""
import os, re, sys
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "newsletter", "issues", "002-video")
sys.path.insert(0, DIR)
import audio as A, content as C

def main():
    fails = []
    def check(cond, msg):
        if not cond: fails.append(msg)
    y = A.jingle()
    check(abs(len(y) / A.SR - C.BUMPER_LEN["bumper"]) < 1e-6, "bumper length is the jingle length")
    check(C.BUMPER_LEN["bumper"] == 4.0 and A.JINGLE_HIT == 1.0, "Signal: 4.0 s, hit at 1.0 s")
    hop = A.SR // 20; e = np.sqrt((y[:len(y) // hop * hop].reshape(-1, hop) ** 2).mean(1))   # 50 ms RMS
    loud = int(np.argmax(e)) / 20
    check(A.JINGLE_HIT <= loud <= A.JINGLE_HIT + 0.1, f"loudest 50 ms at {loud:.2f} s, not on the hit")
    check(float(np.abs(y).max()) < 1.3, "jingle level")
    src = open(os.path.join(DIR, "render.py"), encoding="utf-8").read()
    check("HIT = A.JINGLE_HIT" in src, "render.py times the intro from the jingle hit")
    check(not re.search(r"crest", src), "no old crest in the renderer")
    if fails:
        print("FAIL:", *fails, sep="\n  "); sys.exit(1)
    print("ok")

if __name__ == "__main__":
    main()
