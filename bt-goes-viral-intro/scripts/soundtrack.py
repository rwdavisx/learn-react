"""Synthesize the 'BT Goes Viral' intro soundtrack (48 kHz stereo WAV).

Timeline (s): 0.3 ECG beep | 0.3-2.8 heartbeat + drone + riser | 2.8 impact, beat drops,
2.8-8.8 driving beat under the clip (Am-F-G-E) | 8.8 logo impact + braam | 10.8 final hit | 12.8 end.
"""
import sys, wave
import numpy as np
from scipy import signal

SR = 48000
DUR = 12.8
N = int(SR * DUR)
BEAT = 0.5          # 120 BPM
GRID0 = 0.3         # beat grid offset so impacts land on beats
T_DROP, T_LOGO, T_SUB, T_END = 2.8, 8.8, 10.8, 12.8
rng = np.random.default_rng(7)

mix = {k: np.zeros((N, 2)) for k in ("drums", "bass", "synth", "fx", "voice")}


def t_arr(d):
    return np.arange(int(d * SR)) / SR


def place(bus, t0, x, gain=1.0, pan=0.0):
    """Add mono/stereo x into bus at time t0 with constant-power pan."""
    if x.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        x = np.stack([x * l, x * r], 1) * np.sqrt(2)
    i0 = int(round(t0 * SR))
    if i0 < 0:
        x, i0 = x[-i0:], 0
    i1 = min(N, i0 + len(x))
    if i1 > i0:
        mix[bus][i0:i1] += x[: i1 - i0] * gain


def tv_lp(x, fc):
    """Two-pass one-pole lowpass with a per-sample cutoff array."""
    a = np.exp(-2 * np.pi * np.asarray(fc) / SR)
    for _ in range(2):
        y = np.empty_like(x); z = 0.0
        for i in range(len(x)):
            z = (1 - a[i]) * x[i] + a[i] * z
            y[i] = z
        x = y
    return x


def lp(x, fc, order=2):
    if not np.isscalar(fc):
        return tv_lp(x, fc)
    b, a = signal.butter(order, min(fc, SR / 2 - 100) / (SR / 2), "low")
    return signal.lfilter(b, a, x, axis=0)


def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "high")
    return signal.lfilter(b, a, x, axis=0)


def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    return signal.lfilter(b, a, x, axis=0)


def saw(f, t, detune=0.0):
    ph = np.cumsum(np.full_like(t, f * (1 + detune)) / SR) if np.isscalar(f) else np.cumsum(f / SR)
    return 2 * (ph % 1.0) - 1


def sweep_lp(x, f0, f1, curve=2.0):
    """Time-varying one-pole lowpass (cutoff glides f0 -> f1)."""
    n = len(x)
    fc = f0 + (f1 - f0) * np.linspace(0, 1, n) ** curve
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    z = 0.0
    for i in range(n):
        z = (1 - a[i]) * x[i] + a[i] * z
        y[i] = z
    return y


def reverb_ir(dur=1.8, decay=0.55, seed=1):
    r = np.random.default_rng(seed)
    t = t_arr(dur)
    ir = r.standard_normal((len(t), 2)) * np.exp(-t / decay)[:, None]
    ir = lp(ir, 6000)
    ir[:240] *= np.linspace(0, 1, 240)[:, None]
    return ir / np.sqrt((ir ** 2).sum(0))


def reverb(x, wet=0.25, **kw):
    ir = reverb_ir(**kw)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    out = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x * (1 - wet) + out * wet * 1.3


# ---------------------------------------------------------------- instruments
def kick(dur=0.45, f_hi=150, f_lo=45, punch=1.0):
    t = t_arr(dur)
    f = f_lo + (f_hi - f_lo) * np.exp(-t * 32)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
    click = hp(rng.standard_normal(len(t)), 2500) * np.exp(-t * 400) * 0.35 * punch
    return np.tanh((body + click) * 1.6) * 0.9


def heartbeat(gain=1.0):
    t = t_arr(0.42)
    def thump(level):
        f = 38 + 50 * np.exp(-t * 25)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11) * level
    lub = thump(1.0)
    dub = np.concatenate([np.zeros(int(0.17 * SR)), thump(0.7)])[: len(t)]
    return lp(np.tanh((lub + dub) * 1.4), 900) * gain


def hat(dur=0.05, open_=False):
    t = t_arr(0.22 if open_ else dur)
    x = hp(rng.standard_normal(len(t)), 7000, 4)
    return x * np.exp(-t * (16 if open_ else 75)) * 0.5


def snare(dur=0.3):
    t = t_arr(dur)
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 28)
    noise = bp(rng.standard_normal(len(t)), 1200, 7500) * np.exp(-t * 14)
    return np.tanh(tone * 0.7 + noise * 1.1) * 0.7


def bass_note(f, dur):
    t = t_arr(dur)
    x = 0.6 * saw(f, t) + 0.4 * saw(f, t, 0.006) + 0.6 * np.sin(2 * np.pi * f / 2 * t)
    env = np.minimum(1, t / 0.004) * np.exp(-t * 4.5)
    return lp(np.tanh(x * 1.5), 520 + 900 * np.exp(-t * 18)) * env


def pad(freqs, dur, attack=0.6, release=0.8, cutoff=1400):
    t = t_arr(dur)
    x = np.zeros((len(t), 2))
    for f in freqs:
        for k, det in enumerate((-0.009, -0.003, 0.004, 0.010)):
            v = saw(f, t, det) + 0.0 * rng.random()
            x[:, k % 2] += v
    x = lp(x, cutoff, 2) / (len(freqs) * 2)
    env = np.minimum(1, t / attack) * np.clip((dur - t) / release, 0, 1)
    return x * env[:, None]


def impact(size=1.0):
    t = t_arr(2.6)
    f = 26 + 60 * np.exp(-t * 6)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    crack = lp(rng.standard_normal(len(t)), 3500) * np.exp(-t * 9) * 0.8
    tom = np.sin(2 * np.pi * np.cumsum(90 + 120 * np.exp(-t * 18)) / SR) * np.exp(-t * 7) * 0.7
    x = np.tanh((sub * 1.2 + crack + tom) * 1.8 * size)
    return reverb(x, wet=0.35, dur=2.4, decay=0.8)


def riser(dur):
    t = t_arr(dur)
    n = rng.standard_normal(len(t))
    noise = hp(tv_lp(n, 250 + 7000 * (t / dur) ** 2.5), 150)
    f = 180 * (8 ** (t / dur) )
    tone = 0.5 * saw(f, t) + 0.5 * saw(f * 1.5, t)
    tone = sweep_lp(tone, 400, 5000, 2.0)
    env = (t / dur) ** 2.2
    return (noise * 1.2 + tone * 0.45) * env


def whoosh(dur=0.55, up=True):
    t = t_arr(dur)
    n = rng.standard_normal(len(t))
    fc = np.linspace(500, 5000, len(t)) if up else np.linspace(5000, 500, len(t))
    fc = 400 + 4600 * np.sin(np.pi * t / dur) ** 2
    x = tv_lp(n, fc)
    env = np.sin(np.pi * t / dur) ** 3
    x = hp(x * env, 350) * 0.8
    pans = np.linspace(-0.9, 0.9, len(t))
    return np.stack([x * np.cos((pans + 1) * np.pi / 4), x * np.sin((pans + 1) * np.pi / 4)], 1) * 1.4


def beep(f=1000, dur=0.14):
    t = t_arr(dur)
    env = np.minimum(1, t / 0.005) * np.clip((dur - t) / 0.02, 0, 1)
    return (np.sin(2 * np.pi * f * t) + 0.15 * np.sin(2 * np.pi * 2 * f * t)) * env * 0.5


def tick():
    t = t_arr(0.012)
    return bp(rng.standard_normal(len(t)), 2000, 9000) * np.exp(-t * 500) * 0.6


def glitch(dur=0.22):
    t = t_arr(dur)
    seg = int(0.018 * SR)
    x = np.zeros(len(t))
    for i in range(0, len(t), seg):
        f = rng.choice([220, 330, 880, 1320, 2640, 160])
        tt = t[i : i + seg] - t[i]
        sq = np.sign(np.sin(2 * np.pi * f * tt))
        x[i : i + seg] = sq * (rng.random() > 0.25)
    x = np.round(x * 4) / 4
    return x * np.exp(-t * 6) * 0.25


def braam(freqs, dur, attack=0.05):
    """Gritty brass-like swell: detuned saw stack, filter opens then closes, saturated."""
    t = t_arr(dur)
    x = np.zeros(len(t))
    for f in freqs:
        for det in (-0.012, -0.004, 0.005, 0.013):
            x += saw(f, t, det)
    x /= len(freqs) * 4
    x = tv_lp(x, 160 + 2400 * np.exp(-t * 1.8) * np.minimum(1, t / 0.08))
    x = np.tanh(x * 4.0) * 0.8
    env = np.minimum(1, t / attack) * np.exp(-t * 0.8) * np.clip((dur - t) / 0.5, 0, 1)
    return reverb(x * env, wet=0.3, dur=2.5, decay=0.9)


def tom(f=95, dur=0.6):
    t = t_arr(dur)
    ff = f * (1 + 0.6 * np.exp(-t * 20))
    body = np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t * 6)
    skin = lp(rng.standard_normal(len(t)), 1500) * np.exp(-t * 30) * 0.4
    return np.tanh((body + skin) * 1.5) * 0.8


_stab_cache = {}


def stab(f, dur=0.14):
    """Short dark saw stab for the 16th-note ostinato."""
    if (f, dur) not in _stab_cache:
        t = t_arr(dur)
        x = 0.5 * saw(f, t) + 0.5 * saw(f, t, 0.007)
        env = np.minimum(1, t / 0.003) * np.exp(-t * 22)
        _stab_cache[(f, dur)] = lp(x * env, 900) * 0.6
    return _stab_cache[(f, dur)]


# ---------------------------------------------------------------- arrangement
NOTE = {"A1": 55.0, "E1": 41.2, "F1": 43.65, "G1": 49.0, "A2": 110.0, "F2": 87.31, "G2": 98.0, "E2": 82.41,
        "C3": 130.81, "D3": 146.83, "E3": 164.81, "G#3": 207.65, "A3": 220.0, "B3": 246.94, "C4": 261.63,
        "F3": 174.61, "G3": 196.0, "E4": 329.63, "D4": 293.66}

# --- Opener: ECG beep + heartbeat + low drone + riser, toms building into the drop
place("fx", 0.30, reverb(beep(1000), 0.3, dur=1.0, decay=0.3), 0.5)
for i, tb in enumerate(np.arange(GRID0, T_DROP - 0.01, BEAT)):
    place("drums", tb, heartbeat(0.6 + 0.4 * i / 5), 1.0)
place("synth", 0.15, pad([NOTE["A1"], NOTE["E2"], NOTE["A2"]], T_DROP - 0.15 + 0.4,
                          attack=1.2, release=0.4, cutoff=500), 1.4)
place("fx", 0.42, whoosh(0.5), 0.2)
place("fx", 1.52, whoosh(0.5), 0.2)
place("fx", T_DROP - 1.5, riser(1.5), 0.5)
for k, tt in enumerate(np.concatenate([np.arange(1.8, 2.3, 0.25), np.arange(2.3, 2.8, 0.125)])):
    place("drums", tt, tom(110 if k % 2 else 82), 0.25 + 0.5 * (tt - 1.8), pan=(-0.3 if k % 2 else 0.3))

# --- Drop: impact + braam, then a driving beat under the clip
place("fx", T_DROP, impact(1.0), 0.55)
place("synth", T_DROP, braam([NOTE["A1"], NOTE["E2"], NOTE["A2"]], 1.6), 0.55)
place("fx", T_DROP, glitch(0.2), 0.4, pan=0.3)
CHORDS = [  # (start, dur, bass root, pad tones)
    (2.8, 2.0, "A2", ["A2", "E3", "A3", "C4"]),
    (4.8, 2.0, "F2", ["F2", "C3", "F3", "A3"]),
    (6.8, 1.0, "G2", ["G2", "D3", "G3", "B3"]),
    (7.8, 1.0, "E2", ["E2", "B3", "E3", "G#3"]),
    (8.8, 2.0, "A2", ["A2", "E3", "A3", "C4"]),
]
for start, dur, root, padn in CHORDS:
    end = start + dur
    for k, tt in enumerate(np.arange(start, end - 1e-6, 0.25)):   # driving 8th-note bass
        place("bass", tt, bass_note(NOTE[root], 0.24), 0.55 if k % 2 == 0 else 0.42)
    pattern = [1, 1, 2, 1, 1, 2, 1, 2]                              # low root/octave ostinato
    for k, tt in enumerate(np.arange(start, end - 1e-6, 0.125)):
        place("synth", tt, stab(NOTE[root] * pattern[k % 8]), 0.32, pan=(-0.25 if k % 2 else 0.25))
    place("synth", start, pad([NOTE[n] for n in padn], dur + 0.3, attack=0.15, release=0.3, cutoff=1000), 0.3)

for tb in np.arange(T_DROP, T_SUB - 1e-6, BEAT):           # kick on every beat
    place("drums", tb, kick(), 0.9)
for tb in np.arange(T_DROP + BEAT, T_SUB - 1e-6, 2 * BEAT):  # backbeat
    place("drums", tb, reverb(snare(), 0.25, dur=0.9, decay=0.3), 0.55)
for k, tt in enumerate(np.arange(T_DROP, T_SUB - 1e-6, 0.25)):  # 8th hats, kept low
    place("drums", tt, hat(), 0.16 if k % 2 else 0.1, pan=0.25)
# tom fill + riser into the logo
for k, tt in enumerate(np.arange(8.3, 8.8, 0.125)):
    place("drums", tt, tom([120, 100, 85, 70][k % 4]), 0.5 + 0.4 * (tt - 8.3), pan=(-0.3 if k % 2 else 0.3))
place("fx", 8.0, riser(0.8), 0.4)
place("fx", 8.55, whoosh(0.3), 0.18)

# HUD typewriter ticks (match the text timings in render.py)
for t0, nchar, dt in ((3.0, 18, 0.014), (3.7, 14, 0.018), (4.5, 25, 0.018), (5.3, 39, 0.018), (6.1, 16, 0.018)):
    for c in range(nchar):
        place("fx", t0 + c * dt, tick(), 0.12, pan=0.5)

# --- Logo: big impact + long braam, final hit as the subscribe button lands, ring out
place("fx", T_LOGO, impact(1.15), 0.6)
place("synth", T_LOGO, braam([NOTE["A1"], NOTE["E2"], NOTE["A2"], NOTE["C3"]], T_END - T_LOGO), 0.7)
place("fx", T_LOGO, glitch(0.15), 0.3, pan=-0.3)
place("synth", T_LOGO, pad([NOTE["A2"], NOTE["E3"], NOTE["A3"], NOTE["C4"]], T_END - T_LOGO,
                            attack=0.3, release=2.6, cutoff=1100), 0.4)
place("drums", T_SUB, kick(f_hi=120, f_lo=40), 0.9)
place("fx", T_SUB, impact(0.7), 0.3)
place("drums", T_SUB, tom(70, 1.0), 0.6)

# --- Voice: original clip audio, placed under the drop
w = wave.open(sys.argv[1])
assert w.getframerate() == SR and w.getnchannels() == 2
v = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2).astype(np.float64) / 32768
v = v[: int((T_LOGO - T_DROP) * SR)]
v[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
place("voice", T_DROP, hp(v, 90), 1.0)

# ---------------------------------------------------------------- mix bus
# sidechain-style pump on bass/synth from the kick
pump = np.ones(N)
for tb in np.arange(T_DROP, T_SUB - 1e-6, BEAT):
    i0 = int(tb * SR)
    tt = t_arr(0.35)
    seg = 1 - 0.65 * np.exp(-tt * 14)
    i1 = min(N, i0 + len(tt))
    pump[i0:i1] = np.minimum(pump[i0:i1], seg[: i1 - i0])
# duck music a little under the voice
venv = np.abs(mix["voice"]).mean(1)
venv = signal.lfilter([1 - np.exp(-1 / (0.08 * SR))], [1, -np.exp(-1 / (0.08 * SR))], venv)
duck = 1 - 0.45 * np.clip(venv / (venv.max() + 1e-9) * 2.0, 0, 1)

out = (mix["drums"] * 0.95
       + mix["bass"] * pump[:, None] * 0.9 * duck[:, None]
       + mix["synth"] * pump[:, None] * 0.8 * duck[:, None]
       + mix["fx"] * 0.9
       + mix["voice"] * 1.4)
# gentle fade-out at the very end
fo = int(0.5 * SR)
out[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
out = np.tanh(out * 1.1) / np.tanh(1.1)       # soft clip glue
out /= np.abs(out).max() / 0.89
for k, v in mix.items():
    seg = lambda a, b: np.sqrt((v[int(a*SR):int(b*SR)] ** 2).mean())
    print(f"{k:6s} peak {np.abs(v).max():.2f}  rms open {seg(0,2.8):.3f} clip {seg(2.8,8.8):.3f} logo {seg(8.8,12.8):.3f}")
pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16)
o = wave.open(sys.argv[2], "wb")
o.setnchannels(2); o.setsampwidth(2); o.setframerate(SR)
o.writeframes(pcm.tobytes())
o.close()
print("wrote", sys.argv[2], f"{len(out) / SR:.2f}s")
