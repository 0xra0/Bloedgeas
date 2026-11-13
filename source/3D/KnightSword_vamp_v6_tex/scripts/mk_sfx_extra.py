"""Bleed sting + low-HP heartbeat loop from REDkit's original W3 WAVs -> audio/src/*.wav (48 kHz mono 16-bit).

  python3 -I mk_sfx_extra.py

- bloedgeas_bleed{,_b}: Dettlaff's blood-construct "start" swell, cut to 0.9 s, with a short blood squirt on top
  at +40 ms. Plays once when the sword opens a bleed.
- bloedgeas_heartbeat: one tree_heart thump as "lub" and the same thump 3 st up and quieter as "dub" 0.26 s later,
  low-passed, one beat per 0.75 s (80 bpm). The tails that spill past the loop end are wrapped to its start, so
  the loop has no seam when Wwise repeats it.
"""
import os, subprocess, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "audio", "src")
ORIG = "/mnt/ssd/Games/The Witcher 3 REDkit/assets/w3_audio/Originals/SFX"
SR = 48000


def load(rel):
    w = wave.open(os.path.join(ORIG, rel))
    assert w.getsampwidth() == 2 and w.getnchannels() == 1, rel
    a = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768
    if w.getframerate() != SR:          # linear resample is fine for these low, dull sources
        n = int(len(a) * SR / w.getframerate())
        a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a)
    return a


def pitch(a, semitones):
    r = 2 ** (semitones / 12)
    return np.interp(np.arange(0, len(a) - 1, r), np.arange(len(a)), a)


def lowpass(a, hz):
    k = np.exp(-2 * np.pi * hz / SR)    # one-pole, run twice
    for _ in range(2):
        y, p = np.empty_like(a), 0.0
        for i, x in enumerate(a):
            p = (1 - k) * x + k * p
            y[i] = p
        a = y
    return a


def fade(a, sec):
    n = int(sec * SR)
    a[-n:] *= np.linspace(1, 0, n) ** 2
    return a


def lufs(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(r.rsplit("I:", 1)[1].split("LUFS")[0])


def write(name, a, target, measure_tiles=1):
    path = os.path.join(OUT, name + ".wav")
    for _ in range(2):                  # write, measure, apply gain, write again
        a = a / max(1e-9, np.abs(a).max()) * 0.89
        tmp = path + ".m.wav"
        save(tmp, np.tile(a, measure_tiles))
        g = 10 ** ((target - lufs(tmp)) / 20)
        os.remove(tmp)
        a = a * g
        if np.abs(a).max() <= 0.95:
            break
        a = np.tanh(a / 0.95) * 0.95    # soft-clip the peak rather than miss the loudness
    save(path, a)
    print(name, f"{len(a) / SR:.2f} s", f"{lufs(path):.1f} LUFS")


def save(path, a):
    w = wave.open(path, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(a, -1, 1) * 32767).astype("<i2").tobytes())


def place(buf, a, at, gain=1.0):
    i = int(at * SR)
    n = min(len(a), len(buf) - i)
    buf[i:i + n] += a[:n] * gain


def bleed(start, squirt):
    swell = fade(load(start)[:int(0.9 * SR)].copy(), 0.35)
    buf = np.zeros(len(swell))
    place(buf, swell, 0)
    place(buf, load(squirt), 0.04, 0.8)
    return buf


def heartbeat(period=0.75, dub_at=0.26):
    thump = lowpass(load("monsters/tree_heart/heartbeat_01.wav"), 450)
    n = int(period * SR)
    buf = np.zeros(n + len(thump) * 2)
    place(buf, thump, 0)
    place(buf, pitch(thump, 3), dub_at, 0.6)
    loop = buf[:n].copy()
    for k in range(1, len(buf) // n + 1):         # wrap the spill-over back to the loop start
        tail = buf[k * n:(k + 1) * n]
        loop[:len(tail)] += tail
    return loop


if __name__ == "__main__":
    BT = "monsters/ep2/Dettlaff_Monster/combat/bloodtrail/monster_dettlaff_monster_construct_bloodtrail_start_0"
    write("bloedgeas_bleed", bleed(BT + "1.wav", "fx/blood/blood_outflow_small_short_04.wav"), -17)
    write("bloedgeas_bleed_b", bleed(BT + "3.wav", "fx/blood/blood_outflow_small_short_02.wav"), -17)
    write("bloedgeas_heartbeat", heartbeat(), -22, measure_tiles=4)
