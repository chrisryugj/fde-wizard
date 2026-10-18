"""영상 A·B 음악(120BPM, 1박=15프레임) + 효과음 큐 → audio/out/A.wav, audio/out/B.wav
python score.py A|B"""
import json
import os
import sys
import subprocess
import numpy as np
from scipy.signal import fftconvolve

import synth as S

SR, FPS, BEAT = 44100, 30, 0.5
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IR = '/Library/Audio/Impulse Responses/Apple/02 Medium Spaces/03 Plate Reverbs/1.3s_Soft Plate.SDIR'
os.makedirs(os.path.join(ROOT, 'tmp'), exist_ok=True)

CHORDS = {'C': (48, [60, 64, 67]), 'F': (41, [60, 65, 69]), 'Am': (45, [60, 64, 69]), 'G': (43, [59, 62, 67]),
          'Dm': (38, [57, 62, 65]), 'E7': (40, [56, 62, 64]), 'Em': (40, [59, 64, 67])}
MAJOR = ['C', 'F', 'Am', 'G']
MINOR = ['Am', 'F', 'Dm', 'E7']
# 4마디(16박) 귀여운 멜로디: (박, 음, 길이(박))
MELODY = [(0, 76, 1), (1, 79, .5), (1.5, 81, .5), (2, 79, 1), (3, 76, 1),
          (4, 77, 1), (5, 81, .5), (5.5, 84, .5), (6, 83, 2),
          (8, 81, 1), (9, 84, .5), (9.5, 83, .5), (10, 81, 1), (11, 79, 1),
          (12, 77, .5), (12.5, 79, .5), (13, 81, .5), (13.5, 83, .5), (14, 84, 2)]
SNEAKY = [(0, 69, .5), (1, 72, .5), (1.5, 71, .5), (2, 69, .5), (3, 68, 1),
          (4, 69, .5), (5, 72, .5), (5.5, 74, .5), (6, 72, .5), (7, 71, 1)]
PENTA = [72, 74, 76, 79, 81, 84, 86, 88, 91, 93]


QUIET = []  # 나레이션이 나오는 구간(초) — 멜로디를 낮추고 종소리는 뺀다


def quiet(at):
    return any(a <= at <= b for a, b in QUIET)


class Bus:
    def __init__(self, sec):
        self.x = np.zeros((int(sec * SR) + SR * 4, 2), np.float32)

    def add(self, snd, at, gain=1.0, pan=0.0):
        if snd.ndim == 1:
            snd = S.st(snd, pan)
        i = int(at * SR)
        if i < 0:
            snd, i = snd[-i:], 0
        n = min(len(snd), len(self.x) - i)
        if n > 0:
            self.x[i:i + n] += snd[:n] * gain


def fs(f):
    return f / FPS


def song(mus, segs, total_frames):
    """segs: [(시작f, 끝f, 진행, 악기층, 멜로디, 종소리)] — 박마다 악기를 깐다."""
    for (f0, f1, prog, layers, mel, bells) in segs:
        nb = int(round((f1 - f0) / 15))
        for k in range(nb):
            tb = fs(f0) + k * BEAT
            ch = prog[(k // 4) % len(prog)]
            root, voicing = CHORDS[ch]
            q = k % 4
            v = 1.0
            if 'kick' in layers and q in (0, 2):
                mus.add(S.kick(0.9), tb, 0.85)
            if 'kick4' in layers:
                mus.add(S.kick(0.75), tb, 0.7)
            if 'clap' in layers and q in (1, 3):
                mus.add(S.clap(0.5), tb, 0.5, 0.1)
            if 'hat' in layers:
                mus.add(S.hat(0.12), tb, 0.45, -0.3)
                mus.add(S.hat(0.2), tb + BEAT / 2, 0.45, -0.3)
            if 'shaker' in layers:
                for j in range(4):
                    mus.add(S.shaker(0.09), tb + j * BEAT / 4, 0.35, 0.4)
            if 'bass' in layers and q in (0, 2):
                mus.add(S.pluck_bass(root if q == 0 else root + 7, 0.42, 0.55), tb, 0.9)
            if 'bass4' in layers:
                mus.add(S.pluck_bass(root + (0, 7, 12, 7)[q], 0.3, 0.5), tb, 0.85)
            if 'comp' in layers:
                for m in voicing:
                    mus.add(S.pno(m, 56, 0.1, 0.22), tb + BEAT / 2, 0.5)
            if 'arp' in layers:
                notes = [m + 12 for m in voicing] + [voicing[0] + 24]
                for j in range(4):
                    mus.add(S.blip(notes[j], 0.16), tb + j * BEAT / 4, 0.6, (-0.5, 0.5)[j % 2])
            if 'pad' in layers and q == 0:
                mus.add(S.st(S.pad([n + 12 for n in voicing], 4 * BEAT, 0.07)), tb, 1.0)
        if mel:
            phrase = MELODY if mel == 'main' else SNEAKY
            span = 16 if mel == 'main' else 8
            t0 = fs(f0)
            for rep in range(int(np.ceil((f1 - f0) / 15 / span))):
                for (b, m, d) in phrase:
                    at = t0 + (rep * span + b) * BEAT
                    if at >= fs(f1) - 0.05:
                        continue
                    q = quiet(at)
                    mus.add(S.pno(m, 64 if q else 82, d * BEAT * 0.85, 0.5), at, 0.3 if q else 0.75)
                    if bells and not q:
                        mus.add(S.bell(m + 12, 1.0, 0.22), at, 0.7, 0.2)


def final_hit(mus, sfx, f, key='C'):
    t = fs(f)
    sfx.add(S.kick(1.0), t, 1.0)
    sfx.add(S.boom(0.5), t, 0.6)
    root, voicing = CHORDS[key]
    for m in [root, root + 12] + voicing + [voicing[-1] + 12]:
        mus.add(S.pno(m, 92, 1.8, 1.4), t, 0.6)
    sfx.add(S.arp([72, 76, 79, 84, 88, 91], 0.05, 0.35), t + 0.05, 0.8)
    sfx.add(S.sparkle(1.4, 30, 0.22, seed=f), t, 0.8)
    mus.add(S.st(S.pad([n + 12 for n in voicing], 3.5, 0.09)), t, 1.0)


# ---------------------------------------------------------------- 영상 A
def cues_a(mus, sfx):
    G = 'kick clap hat bass comp'.split()
    song(mus, [
        (0, 90, MAJOR, G + ['shaker'], 'main', True),
        (90, 225, MAJOR, ['kick', 'hat', 'bass', 'comp'], None, False),
        (225, 375, MAJOR, G, 'main', False),
        (375, 585, MAJOR, G + ['shaker'], 'main', True),
        (585, 825, MAJOR, G + ['shaker', 'pad'], 'main', True),
    ], 945)
    final_hit(mus, sfx, 825)
    for b, m, d in [(1, 79, 1), (2, 76, 1), (3, 72, 3)]:
        mus.add(S.pno(m, 70, d * BEAT, 1.2), fs(825) + 0.6 + b * BEAT, 0.6)
    # 콜드오픈
    sfx.add(S.whoosh(0.3, 0.45), fs(8), 1.0)
    sfx.add(S.boom(0.8), fs(15), 1.0)
    sfx.add(S.sparkle(1.4, 34, 0.25, seed=1), fs(15), 0.9)
    sfx.add(S.hum(1.6, 0.1, 43), fs(14), 0.7)
    sfx.add(S.chime(91, 0.4), fs(71), 0.8)
    sfx.add(S.sparkle(1.0, 26, 0.22, seed=2), fs(71), 0.8)
    # 컷
    for f in (89, 134, 824):
        sfx.add(S.whoosh(0.35, 0.35), fs(f) - 0.1, 0.9)
    # 사진 + 코드
    sfx.add(S.pop(0.8, 0.5), fs(91), 0.8)
    for f in range(96, 131, 2):
        sfx.add(S.click(0.12), fs(f), 0.5, ((f * 7) % 9 - 4) / 6)
    sfx.add(S.scan(0.95, 0.18), fs(102), 0.9)
    # 부품 조립: 올라가는 팝
    asm = [4, 8, 12, 16, 18, 21, 25, 28, 30, 32, 34, 38, 41, 42, 44, 45, 47, 48, 50, 52, 55, 59, 63]
    for i, f in enumerate(asm):
        sfx.add(S.pop(0.75 + 0.035 * i, 0.5), fs(135 + f - 1), 0.8, ((i % 5) - 2) / 4)
    sfx.add(S.whoosh(0.2, 0.3, up=False), fs(135 + 65), 0.8)
    sfx.add(S.thud(0.7), fs(135 + 71), 0.9)
    sfx.add(S.pop(1.6, 0.5), fs(135 + 71), 0.8)
    sfx.add(S.sparkle(0.6, 20, 0.18, seed=4), fs(135 + 72), 0.7)
    # 턴테이블 와이프
    sfx.add(S.whoosh(0.45, 0.35), fs(252), 0.8)
    sfx.add(S.whoosh(0.45, 0.35), fs(282), 0.8)
    sfx.add(S.sparkle(0.6, 18, 0.15, seed=5), fs(292), 0.7)
    # 뼈 등장: 올라가는 디지털 블립
    for i in range(12):
        sfx.add(S.blip(72 + [0, 4, 7, 12][i % 4] + 12 * (i // 8), 0.18), fs(318 + i * 3), 0.7, (i % 3 - 1) / 2)
    sfx.add(S.chime(96, 0.3), fs(352), 0.7)
    # 리그 테스트: 걸음, 인사
    for f in (414, 424, 434, 444, 454):
        sfx.add(S.thud(0.25), fs(f), 0.6)
    sfx.add(S.whoosh(0.3, 0.25, up=False), fs(463), 0.7)
    # 포즈 원클릭
    for f in (500, 514, 528, 542, 556, 570):
        sfx.add(S.click(0.45), fs(f), 0.9, 0.5)
        sfx.add(S.pop(1.3, 0.35), fs(f) + 0.02, 0.7)
    # 손인사 반짝
    sfx.add(S.sparkle(1.0, 22, 0.2, seed=6), fs(600), 0.8)
    # 인사 + 모자
    sfx.add(S.whoosh(0.3, 0.25, up=False), fs(659), 0.7)
    sfx.add(S.wobble(0.35, 0.25, 900, 380), fs(666), 0.8)
    sfx.add(S.boing(0.45), fs(675), 0.9)
    sfx.add(S.sparkle(0.6, 22, 0.2, seed=7), fs(679), 0.8)
    sfx.add(S.pop(1.1, 0.4), fs(688), 0.7)
    # 주문 → 곰돌이
    sfx.add(S.whoosh(0.3, 0.45), fs(728), 1.0)
    sfx.add(S.boom(0.8), fs(735), 1.0)
    sfx.add(S.sparkle(1.4, 34, 0.25, seed=8), fs(735), 0.9)
    sfx.add(S.hum(1.5, 0.1, 43), fs(734), 0.7)
    for f in range(771, 782, 2):
        sfx.add(S.click(0.25), fs(f), 0.6, 0.3)
    sfx.add(S.poof(0.6), fs(781), 1.0)
    sfx.add(S.pop(1.5, 0.5), fs(783), 0.9)
    sfx.add(S.arp([84, 88, 91, 96], 0.05, 0.3), fs(784), 0.8)
    sfx.add(S.sparkle(0.8, 26, 0.2, seed=9), fs(789), 0.8)
    sfx.add(S.chime(96, 0.3), fs(794), 0.7)
    for f in (833, 838, 843):
        sfx.add(S.pop(1.2, 0.3), fs(f), 0.6)


# ---------------------------------------------------------------- 영상 B
def cues_b(mus, sfx):
    G = 'kick clap hat bass comp'.split()
    mus.add(S.st(S.pad([57, 64, 69, 72], 1.5, 0.08)), 0.0, 1.0)
    mus.add(S.st(S.pad([53, 60, 65, 69], 1.5, 0.08)), 1.5, 1.0)
    song(mus, [
        (45, 90, MAJOR, ['kick', 'hat', 'bass'], None, False),
        (90, 165, MINOR, ['kick', 'clap', 'hat', 'bass4', 'comp'], None, False),
        (165, 330, MAJOR, G + ['shaker'], 'main', True),
        (330, 480, MINOR, ['kick', 'clap', 'bass4', 'comp'], 'sneaky', False),
        (480, 570, MAJOR, G, 'main', True),
        (570, 810, MAJOR, G + ['arp'], 'main', False),
        (810, 1080, MAJOR, G + ['shaker', 'pad'], 'main', True),
    ], 1170)
    final_hit(mus, sfx, 1080)
    for b, m, d in [(1, 79, 1), (2, 76, 1), (3, 72, 3)]:
        mus.add(S.pno(m, 70, d * BEAT, 1.2), fs(1080) + 0.6 + b * BEAT, 0.6)
    # 출동
    sfx.add(S.whoosh(1.3, 0.25, up=False), 0.0, 0.8)
    sfx.add(S.sparkle(1.3, 14, 0.15, seed=11), 0.0, 0.7)
    sfx.add(S.riser(0.7, 0.25), fs(18), 0.8)
    sfx.add(S.boom(0.8), fs(39), 1.0)
    sfx.add(S.poof(0.6), fs(39), 0.9)
    sfx.add(S.sparkle(1.2, 30, 0.22, seed=12), fs(39), 0.8)
    sfx.add(S.thud(0.5), fs(45), 0.8)
    sfx.add(S.whoosh(0.3, 0.25, up=False), fs(55), 0.7)
    # 서류 산더미 → 데이터
    for i, f in enumerate((97, 100, 103, 106, 109)):
        sfx.add(S.thud(0.55), fs(f), 0.8, (i - 2) / 3)
        sfx.add(S.pop(0.7 + 0.05 * i, 0.35), fs(f), 0.6)
    sfx.add(S.boing(0.35), fs(113), 0.8)
    sfx.add(S.whoosh(0.3, 0.45), fs(155), 1.0)
    sfx.add(S.boom(0.7), fs(161), 0.9)
    sfx.add(S.sparkle(1.2, 30, 0.22, seed=13), fs(161), 0.8)
    sfx.add(S.hum(4.2, 0.07, 55), fs(160), 0.7)
    for k in range(24):
        ts = 80 + k * 4
        sfx.add(S.whoosh(0.18, 0.1), fs(90 + ts - 1), 0.5, 0.4)
        sfx.add(S.blip(PENTA[k % len(PENTA)], 0.14), fs(90 + ts + 17), 0.7, -0.4)
    sfx.add(S.arp([72, 76, 79, 84, 88], 0.05, 0.35), fs(281), 0.8)
    sfx.add(S.sparkle(1.0, 26, 0.2, seed=14), fs(285), 0.8)
    # 환각 유령 vs 법령 원문
    sfx.add(S.poof(0.5), fs(339), 0.8, -0.4)
    sfx.add(S.wobble(0.9, 0.22), fs(349), 0.8, -0.4)
    sfx.add(S.wobble(0.7, 0.18, 600, 420), fs(372), 0.7, -0.4)
    sfx.add(S.whoosh(0.3, 0.4), fs(395), 0.9)
    sfx.add(S.boom(0.55), fs(401), 0.8)
    sfx.add(S.poof(0.55), fs(405), 0.9, 0.4)
    sfx.add(S.thud(0.5), fs(429), 0.8, 0.4)
    sfx.add(S.whoosh(0.4, 0.25), fs(417), 0.7, 0.4)
    sfx.add(S.sparkle(1.0, 22, 0.18, seed=15), fs(430), 0.8)
    sfx.add(S.scan(0.3, 0.2), fs(453), 0.9)
    sfx.add(S.buzz(0.4), fs(476), 1.0, -0.3)
    sfx.add(S.thud(0.7), fs(477), 0.9, -0.3)
    sfx.add(S.wobble(0.5, 0.2, 380, 900), fs(500), 0.7, -0.4)
    sfx.add(S.poof(0.55), fs(509), 0.9, -0.4)
    sfx.add(S.arp([72, 76, 79, 84, 88, 91], 0.05, 0.4), fs(512), 0.9)
    sfx.add(S.pop(1.1, 0.35), fs(524), 0.6)
    # 동네를 데이터로
    rng = np.random.default_rng(3)
    for i in range(22):
        f = int(589 + rng.uniform(0, 24))
        sfx.add(S.pop(rng.uniform(0.6, 1.3), 0.22), fs(f), 0.6, rng.uniform(-0.7, 0.7))
    sfx.add(S.thud(0.8), fs(635), 1.0)
    sfx.add(S.whoosh(0.8, 0.3), fs(635), 0.8)
    sfx.add(S.sparkle(0.8, 20, 0.18, seed=16), fs(636), 0.7)
    for i in range(14):
        sfx.add(S.bell(PENTA[i % len(PENTA)], 0.8, 0.28), fs(643 + i * 4), 0.8, ((i % 5) - 2) / 3)
    sfx.add(S.whoosh(0.5, 0.3), fs(708), 0.8)
    for i in range(10):
        sfx.add(S.blip(76 + 2 * i, 0.15), fs(725 + i * 3), 0.6)
    # 오픈소스로 나누면
    sfx.add(S.riser(0.5, 0.2), fs(818), 0.8)
    sfx.add(S.sparkle(0.6, 20, 0.2, seed=17), fs(833), 0.8)
    for i in range(8):
        sfx.add(S.whoosh(0.35, 0.18), fs(841 + i * 9), 0.6, ((i % 3) - 1) / 2)
        sfx.add(S.chime(PENTA[i + 1], 0.42), fs(863 + i * 9), 0.9, ((i % 3) - 1) / 2)
        sfx.add(S.sparkle(0.5, 18, 0.16, seed=20 + i), fs(863 + i * 9), 0.6)
    # 마무리
    for f in range(1035, 1042, 2):
        sfx.add(S.click(0.25), fs(f), 0.6, 0.3)
    sfx.add(S.poof(0.6), fs(1045), 1.0)
    sfx.add(S.pop(1.5, 0.5), fs(1047), 0.9)
    sfx.add(S.arp([84, 88, 91, 96], 0.05, 0.3), fs(1048), 0.8)
    sfx.add(S.whoosh(0.3, 0.25, up=False), fs(1081), 0.6)


def narration(cues_json, sec):
    """나레이션 wav(48k 모노)를 시작 초에 놓은 트랙과 말하는 구간 목록."""
    from scipy.io import wavfile
    from scipy.signal import resample_poly
    cues = json.load(open(cues_json))
    nar = Bus(sec)
    for c in cues:
        sr, x = wavfile.read(os.path.join(os.path.dirname(cues_json), f"{c['i']:02d}.wav"))
        x = resample_poly(x.astype(np.float32) / 32768, SR, sr).astype(np.float32)
        nar.add(x, c['start'], 1.0)
    return nar, [(c['start'] - 0.15, c['start'] + c['dur'] + 0.1) for c in cues]


def duck_curve(n, windows, attack=0.12, release=0.35):
    t = np.arange(n) / SR
    g = np.zeros(n, np.float32)
    for a, b in windows:
        up = np.clip((t - (a - attack)) / attack, 0, 1)
        down = np.clip(((b + release) - t) / release, 0, 1)
        g = np.maximum(g, np.minimum(up, down))
    return g


def lufs(x):
    """통합 라우드니스(ffmpeg ebur128)."""
    from scipy.io import wavfile
    tmp = os.path.join(ROOT, 'tmp', '_lufs.wav')
    wavfile.write(tmp, SR, np.clip(x, -1, 1).astype(np.float32))
    r = subprocess.run(['ffmpeg', '-nostats', '-i', tmp, '-af', 'ebur128=framelog=quiet', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    return float(r.split('Integrated loudness:')[1].split('I:')[1].split('LUFS')[0])


def master(mus, sfx, out, total_frames, nar=None):
    ir, _ = read_ir()
    wet = np.stack([fftconvolve(mus.x[:, c] + 0.6 * sfx.x[:, c], ir[:, c % ir.shape[1]])[:len(mus.x)] for c in (0, 1)], 1)
    n = int(total_frames / FPS * SR)
    m = n + int(0.2 * SR)
    fade = int(0.8 * SR)
    if nar is not None:  # 마지막 말이 페이드에 먹히지 않게
        fade = int(min(0.8, max(0.3, m / SR - max(e for _, e in nar[1]))) * SR)
    if nar is None:
        mix = (0.62 * mus.x + 0.95 * sfx.x + 0.16 * wet)[:m]
        mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
        # 선형 이득 + 소프트 리미터(동적 정규화 대신)
        rms = np.sqrt(np.mean(mix ** 2))
        mix *= 0.075 / max(rms, 1e-6)
        mix = np.tanh(mix * 1.1) / np.tanh(1.1)
        mix *= 0.93 / max(np.abs(mix).max(), 1e-6)
    else:
        track, windows = nar
        bed_m = (0.62 * mus.x + 0.16 * wet)[:m]
        bed_s = (0.95 * sfx.x)[:m]
        g = duck_curve(m, windows)[:, None]
        # 배경은 덕킹 전 -20 LUFS, 나레이션은 -15.5 LUFS 로 맞춘 뒤, 말하는 동안 음악 -6dB·효과음 -3.7dB
        kb = 10 ** ((-20 - lufs(bed_m + bed_s)) / 20)
        voice = track.x[:m]
        kv = 10 ** ((-15.5 - lufs(voice)) / 20)
        bed = (bed_m * (1 - 0.5 * g) + bed_s * (1 - 0.35 * g)) * kb
        bed = np.tanh(bed * 1.6) / 1.6  # 배경만 부드럽게 눌러 쾅 소리가 말을 덮지 않게
        mix = bed + voice * kv
        mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
        pk = np.abs(mix).max()
        if pk > 0.89:
            mix *= 0.89 / pk
        print(f'배경 {lufs(bed):.1f} LUFS · 나레이션 {lufs(voice * kv):.1f} LUFS · 합 {lufs(mix):.1f} LUFS · 피크 {20 * np.log10(np.abs(mix).max()):.1f} dBFS')
    from scipy.io import wavfile
    os.makedirs(os.path.dirname(out), exist_ok=True)
    wavfile.write(out, SR, (mix * 32767).astype(np.int16))
    print('wrote', out, f'{len(mix) / SR:.2f}s')


def read_ir():
    tmp = os.path.join(ROOT, 'tmp', 'ir.wav')
    if not os.path.exists(IR):  # Logic 잔향 샘플이 없으면 짧게 줄어드는 잡음으로 대신
        n = int(1.3 * SR)
        x = np.random.default_rng(1).standard_normal((n, 2)) * np.exp(-np.arange(n) / SR / 0.32)[:, None]
        return (x / np.abs(x).max() * 0.25).astype(np.float32), SR
    if not os.path.exists(tmp):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', IR, '-ar', str(SR), tmp], check=True)
    from scipy.io import wavfile
    sr, x = wavfile.read(tmp)
    x = x.astype(np.float32)
    x /= np.abs(x).max()
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    return x * 0.25, sr


if __name__ == '__main__':
    v = sys.argv[1]
    total = 960 if v == 'A' else 1170
    mus, sfx = Bus(total / FPS), Bus(total / FPS)
    nar = None
    cues_json = os.path.join(ROOT, 'audio', 'out', f'narr{v}', 'cues.json')
    if os.path.exists(cues_json):  # 내레이션이 없으면(narr.py 안 돌림) 음악만
        nar = narration(cues_json, total / FPS)
        QUIET[:] = nar[1]
    (cues_a if v == 'A' else cues_b)(mus, sfx)
    master(mus, sfx, os.path.join(ROOT, 'audio', 'out', f'{v}.wav'), total, nar)
