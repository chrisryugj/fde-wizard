"""악기·효과음 합성(numpy). 모두 44.1kHz 스테레오 float32."""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from piano import Piano, CAF  # noqa: E402  Logic 스타인웨이 샘플러(macOS + Logic/GarageBand 샘플)

SR = 44100
RNG = np.random.default_rng(7)
_piano = None


def piano():
    global _piano
    if _piano is None:
        _piano = Piano() if os.path.exists(CAF) else False  # 샘플이 없으면 합성 피아노로
    return _piano


def t(sec):
    return np.arange(int(sec * SR)) / SR


def st(mono, pan=0.0):
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    return np.stack([mono * l, mono * r], 1).astype(np.float32)


def env_ad(n, a=0.005, d=0.3):
    x = np.arange(n) / SR
    e = np.minimum(1, x / max(a, 1e-4)) * np.exp(-np.maximum(0, x - a) / d)
    return e


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # 짧은 소리에만 쓴다
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def onepole_lp(x, cutoff):
    """벡터화 1극 저역통과(scipy)."""
    from scipy.signal import lfilter
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x).astype(np.float32)


def bandpass(x, lo, hi):
    from scipy.signal import butter, sosfilt
    sos = butter(2, [lo, hi], btype='band', fs=SR, output='sos')
    return sosfilt(sos, x).astype(np.float32)


def highpass(x, f):
    from scipy.signal import butter, sosfilt
    sos = butter(2, f, btype='high', fs=SR, output='sos')
    return sosfilt(sos, x).astype(np.float32)


# ---------------------------------------------------------------- 악기
def bell(midi, dur=1.2, vel=0.5, ratio=3.5, index=2.2):
    """FM 종소리(첼레스타/글로켄 느낌)."""
    f = hz(midi)
    x = t(dur)
    m = np.sin(2 * np.pi * f * ratio * x) * index * np.exp(-x / 0.25)
    y = np.sin(2 * np.pi * f * x + m) * np.exp(-x / (dur * 0.35))
    y += 0.25 * np.sin(2 * np.pi * f * 2 * x) * np.exp(-x / 0.15)
    a = np.minimum(1, x / 0.002)
    return (y * a * vel).astype(np.float32)


def pluck_bass(midi, dur=0.45, vel=0.6):
    f = hz(midi)
    x = t(dur + 0.1)
    y = np.sin(2 * np.pi * f * x) + 0.35 * np.sin(2 * np.pi * 2 * f * x) * np.exp(-x / 0.08)
    y += 0.15 * np.sign(np.sin(2 * np.pi * f * x)) * np.exp(-x / 0.03)
    e = env_ad(len(x), 0.004, 0.22)
    e[int(dur * SR):] *= np.exp(-np.arange(len(x) - int(dur * SR)) / SR / 0.03)
    return (y * e * vel).astype(np.float32)


def pno(midi, vel=70, dur=0.25, release=0.5):
    if piano():
        return piano().note(int(midi), int(np.clip(vel, 1, 127)), dur, release)
    # 대체: 배음 몇 개를 겹친 단순 피아노
    f, x = hz(midi), t(dur + release)
    y = sum(a * np.sin(2 * np.pi * f * k * x) * np.exp(-x / (0.9 / k)) for k, a in ((1, 1.0), (2, 0.45), (3, 0.2), (4, 0.1)))
    e = np.minimum(1, x / 0.004) * np.where(x < dur, 1.0, np.exp(-(x - dur) / (release / 4)))
    return st((y * e * 0.25 * vel / 100).astype(np.float32))


def kick(vel=0.9):
    x = t(0.35)
    f = 50 + 110 * np.exp(-x / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-x / 0.16)
    y += 0.3 * RNG.standard_normal(len(x)) * np.exp(-x / 0.004)
    return (y * vel).astype(np.float32)


def clap(vel=0.5):
    x = t(0.3)
    n = RNG.standard_normal(len(x))
    e = np.zeros(len(x))
    for d in (0.0, 0.008, 0.017, 0.026):
        e += np.where(x >= d, np.exp(-(x - d) / (0.012 if d < 0.026 else 0.11)), 0)
    y = bandpass(n * e, 900, 4800)
    return (y * vel * 0.9).astype(np.float32)


def hat(vel=0.25, open_=False):
    x = t(0.25 if open_ else 0.07)
    y = highpass(RNG.standard_normal(len(x)), 7000) * np.exp(-x / (0.08 if open_ else 0.018))
    return (y * vel).astype(np.float32)


def shaker(vel=0.12):
    x = t(0.09)
    y = bandpass(RNG.standard_normal(len(x)), 5000, 11000) * np.sin(np.pi * np.minimum(1, x / 0.09))
    return (y * vel).astype(np.float32)


def pad(midis, dur, vel=0.12, bright=0.3):
    """부드러운 패드(가산합성 + 느린 떨림)."""
    x = t(dur)
    y = np.zeros(len(x))
    for m in midis:
        f = hz(m) * 1.0052  # 피아노 샘플 튜닝(+9센트)
        for k, a in ((1, 1.0), (2, 0.35 * bright), (3, 0.18 * bright)):
            y += a * np.sin(2 * np.pi * f * k * x + 0.3 * np.sin(2 * np.pi * 0.2 * x))
    e = np.minimum(1, x / 0.4) * np.minimum(1, (dur - x) / 0.5)
    return (y / max(1, len(midis)) * e * vel).astype(np.float32)


# ---------------------------------------------------------------- 효과음
def pop(pitch=1.0, vel=0.6):
    x = t(0.12)
    f = (700 + 900 * np.exp(-x / 0.02)) * pitch
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x / 0.035)
    y += 0.25 * RNG.standard_normal(len(x)) * np.exp(-x / 0.002)
    return (y * vel).astype(np.float32)


def click(vel=0.5):
    x = t(0.04)
    y = np.sin(2 * np.pi * 2400 * x) * np.exp(-x / 0.006) + 0.5 * RNG.standard_normal(len(x)) * np.exp(-x / 0.0015)
    return (y * vel).astype(np.float32)


def whoosh(dur=0.45, vel=0.5, up=True):
    x = t(dur)
    n = RNG.standard_normal(len(x))
    e = np.sin(np.pi * np.clip(x / dur, 0, 1)) ** 1.5
    lo = bandpass(n, 300, 1600)
    hi = bandpass(n, 1600, 6000)
    mixf = x / dur if up else 1 - x / dur
    y = lo * (1 - mixf) + hi * mixf
    return (y * e * vel).astype(np.float32)


def boom(vel=0.8):
    """마법 폭발: 낮은 하강음 + 잡음 + 반짝 상음."""
    x = t(1.6)
    f = 40 + 90 * np.exp(-x / 0.12)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x / 0.45)
    y += 0.35 * onepole_lp(RNG.standard_normal(len(x)), 1800) * np.exp(-x / 0.18)
    for k, m in enumerate((96, 100, 103, 108, 112)):
        y += 0.10 * np.sin(2 * np.pi * hz(m) * x) * np.exp(-np.maximum(0, x - 0.03 * k) / 0.5) * (x > 0.03 * k)
    return (y * vel).astype(np.float32)


def sparkle(dur=1.0, density=26, vel=0.25, seed=3, lo=88, hi=108):
    rng = np.random.default_rng(seed)
    out = np.zeros((int(dur * SR) + SR, 2), np.float32)
    scale = [0, 2, 4, 7, 9]
    for _ in range(int(density * dur)):
        at = rng.uniform(0, dur)
        oct_ = rng.integers(lo // 12, hi // 12 + 1)
        m = int(oct_ * 12 + rng.choice(scale))
        m = int(np.clip(m, lo, hi))
        b = bell(m, dur=0.6, vel=rng.uniform(0.3, 1.0) * vel, ratio=2.0, index=1.0)
        i = int(at * SR)
        out[i:i + len(b)] += st(b, rng.uniform(-0.8, 0.8))
    return out


def chime(midi=84, vel=0.5):
    return bell(midi, dur=1.6, vel=vel)


def arp(midis, step=0.06, vel=0.4, dur=1.4):
    out = np.zeros(int((step * len(midis) + dur) * SR), np.float32)
    for i, m in enumerate(midis):
        b = bell(m, dur=dur, vel=vel)
        s = int(i * step * SR)
        out[s:s + len(b)] += b
    return out


def thud(vel=0.6):
    x = t(0.3)
    f = 60 + 60 * np.exp(-x / 0.03)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x / 0.09) + 0.2 * onepole_lp(RNG.standard_normal(len(x)), 800) * np.exp(-x / 0.03)
    return (y * vel).astype(np.float32)


def poof(vel=0.5):
    x = t(0.5)
    n = onepole_lp(RNG.standard_normal(len(x)), 2500)
    y = n * (np.minimum(1, x / 0.01) * np.exp(-x / 0.12))
    y += 0.3 * np.sin(2 * np.pi * (300 + 500 * np.exp(-x / 0.05)) * x) * np.exp(-x / 0.08)
    return (y * vel).astype(np.float32)


def boing(vel=0.4):
    x = t(0.5)
    f = 220 * (1 + 0.6 * np.exp(-x / 0.15) * np.sin(2 * np.pi * 14 * x)) * (1 + x)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x / 0.2)
    return (y * vel).astype(np.float32)


def buzz(vel=0.35):
    x = t(0.4)
    y = np.sign(np.sin(2 * np.pi * 150 * x)) * 0.5 + np.sign(np.sin(2 * np.pi * 157 * x)) * 0.5
    y = onepole_lp(y.astype(np.float32), 2200) * np.minimum(1, x / 0.005) * np.minimum(1, (0.4 - x) / 0.05)
    return (y * vel).astype(np.float32)


def wobble(dur=0.9, vel=0.3, f0=520, f1=330):
    """유령 웃음: 떨리며 내려가는 사인(테레민)."""
    x = t(dur)
    f = (f0 + (f1 - f0) * x / dur) * (1 + 0.04 * np.sin(2 * np.pi * 7 * x))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * x / dur) ** 0.7
    return (y * vel).astype(np.float32)


def scan(dur=0.9, vel=0.2):
    x = t(dur)
    f = 600 + 1800 * x / dur
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sin(2 * np.pi * 18 * x)) * np.sin(np.pi * x / dur)
    return (y * vel).astype(np.float32)


def hum(dur=1.5, vel=0.15, midi=48):
    x = t(dur)
    y = np.sin(2 * np.pi * hz(midi) * x) + 0.5 * np.sin(2 * np.pi * hz(midi + 7) * x)
    y *= (0.7 + 0.3 * np.sin(2 * np.pi * 3 * x)) * np.minimum(1, x / 0.2) * np.minimum(1, (dur - x) / 0.3)
    return (y * vel).astype(np.float32)


def blip(midi=84, vel=0.25):
    x = t(0.12)
    y = np.sign(np.sin(2 * np.pi * hz(midi) * x)) * np.exp(-x / 0.03)
    return onepole_lp(y.astype(np.float32), 5000) * vel


def riser(dur=1.0, vel=0.3):
    x = t(dur)
    n = RNG.standard_normal(len(x))
    y = bandpass(n, 2000, 9000) * (x / dur) ** 2
    y += 0.3 * np.sin(2 * np.pi * np.cumsum(300 + 1200 * (x / dur) ** 2) / SR) * (x / dur) ** 2
    return (y * vel).astype(np.float32)
