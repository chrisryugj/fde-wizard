"""예고글 이미지 3장(4:5) — 지금 렌더 중인 실제 프레임과 실제 로그로 만든다.
.venv/bin/python scripts/teaser.py"""
import os
import re
import glob
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'out', 'teaser')
W, H = 1080, 1350
MONO = os.path.join(ROOT, 'build', 'tex', 'JetBrainsMono-500.ttf')


def mono_font(size):
    try:
        return ImageFont.truetype(MONO, size)
    except OSError:
        return ImageFont.load_default()
KO = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
BG, FG, DIM, ACC = (12, 15, 22), (226, 232, 244), (120, 132, 156), (255, 210, 63)


def latest(shot_dir):
    fs = sorted(glob.glob(os.path.join(shot_dir, '*.png')))
    return fs[-1] if fs else None


def frame_no(path):
    return int(re.findall(r'(\d+)\.png$', path)[0])


def fit(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def lanes():
    """4갈래 렌더: 각 갈래 최신 프레임 2×2 + 아래에 실제 로그."""
    shots = [('B', 'b02_docs', 'beauty', 240), ('B', 'b04_map', 'beauty', 240),
             ('A', 'a06_rigtest', 'clay', 120), ('B', 'b01_intro', 'beauty', 90)]
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    mono = mono_font(22)
    mono_s = mono_font(19)
    ko_b = ImageFont.truetype(KO, 34, index=6)
    d.text((44, 40), 'blender -b rig.blend -P shot.py', font=mono, fill=DIM)
    d.text((44, 78), '렌더 4갈래 동시 진행 중', font=ko_b, fill=FG)
    gx, gy, gw, gh, gap = 44, 140, (W - 88 - 16) // 2, 0, 16
    gh = int(gw * 9 / 16)
    logs = []
    for i, (v, s, p, total) in enumerate(shots):
        f = latest(os.path.join(ROOT, 'renders', v, s, p))
        x, y = gx + (i % 2) * (gw + gap), gy + (i // 2) * (gh + 56)
        if f:
            im.paste(fit(Image.open(f).convert('RGB'), gw, gh), (x, y))
            n = frame_no(f)
            d.text((x, y + gh + 10), f'{s}/{p}', font=mono_s, fill=FG)
            label = f'{n:>3}/{total}'
            d.text((x + gw - d.textlength(label, font=mono_s), y + gh + 10), label, font=mono_s, fill=ACC)
            bar_y = y + gh + 40
            d.rectangle([x, bar_y, x + gw, bar_y + 4], fill=(40, 46, 60))
            d.rectangle([x, bar_y, x + int(gw * n / total), bar_y + 4], fill=ACC)
            log = os.path.join(ROOT, 'renders', v, s + '.log')
            saved = [l for l in open(log, encoding='utf-8', errors='ignore') if 'Saved:' in l][-3:]
            for l in saved:
                t = l.split()[0]
                path = l.split("Saved: '")[1].split("renders/")[1].rstrip("'\n")
                logs.append(f'{t}  render  | Saved: {path}')
    ty = gy + 2 * (gh + 56) + 24
    d.rounded_rectangle([44, ty, W - 44, H - 48], radius=18, fill=(20, 24, 33))
    yy = ty + 26
    for l in logs:
        d.text((70, yy), l[:58], font=mono_s, fill=DIM if 'clay' in l else FG)
        yy += 34
    d.text((70, yy + 14), 'EEVEE · 1920×1080 · 64 samples · 프레임당 약 7초', font=ImageFont.truetype(KO, 22, index=2), fill=DIM)
    im.save(os.path.join(OUT, '1_render_lanes.jpg'), quality=93)


def clay_bones():
    c = Image.open(os.path.join(ROOT, 'renders', 'A', 'a05_rig', 'clay', '0044.png')).convert('RGBA')
    b = Image.open(os.path.join(ROOT, 'renders', 'A', 'a05_rig', 'bones', '0044.png')).convert('RGBA')
    c.alpha_composite(b)
    c = c.convert('RGB')
    crop = c.crop((960 - 432, 0, 960 + 432, 1080))
    im = fit(crop, W, H)
    im.save(os.path.join(OUT, '2_clay_bones.jpg'), quality=93)


def color_tease():
    f = os.path.join(ROOT, 'renders', 'B', 'b06_outro', 'beauty', '0112.png')
    im = Image.open(f).convert('RGB')
    cx = 1450
    crop = im.crop((cx - 432, 0, cx + 432, 1080))
    fit(crop, W, H).save(os.path.join(OUT, '3_color.jpg'), quality=93)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    lanes()
    clay_bones()
    color_tease()
    print('teaser ok', sorted(os.listdir(OUT)))
