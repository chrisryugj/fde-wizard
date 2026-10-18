"""공무원증 앞면 텍스처(build/tex/card.png): ref/photo.jpg + params.PROFILE.
사진이 없으면 자리표시 실루엣으로 만든다. .venv/bin/python scripts/make_card.py"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from params import PROFILE  # noqa: E402

FONT = '/System/Library/Fonts/AppleSDGothicNeo.ttc'  # macOS. 다른 OS면 한글 TTF 경로로
W, H = 400, 560


def font(size, bold=True):
    try:
        return ImageFont.truetype(FONT, size, index=6 if bold else 2)
    except OSError:
        return ImageFont.load_default()


def centered(d, y, text, f, fill):
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill)


def placeholder(w, h):
    im = Image.new('RGB', (w, h), '#C9D3E6')
    d = ImageDraw.Draw(im)
    d.ellipse([w * 0.3, h * 0.16, w * 0.7, h * 0.52], fill='#8C9BB8')
    d.rounded_rectangle([w * 0.14, h * 0.58, w * 0.86, h * 1.1], radius=int(w * 0.3), fill='#8C9BB8')
    return im


card = Image.new('RGB', (W, H), '#FFFFFF')
d = ImageDraw.Draw(card)
d.rectangle([0, 0, W, 92], fill='#1E5BC6')
centered(d, 22, PROFILE['org'], font(44), '#FFFFFF')
src = os.path.join(ROOT, 'ref', 'photo.jpg')
use_photo = os.path.exists(src) and not os.environ.get('CARD_PLACEHOLDER')
if use_photo:
    photo = Image.open(src).convert('RGB')
    pw, ph = photo.size
    crop = photo.crop((int(pw * 0.16), int(ph * 0.04), int(pw * 0.84), int(ph * 0.70)))
    crop = ImageOps.fit(crop, (196, 246), method=Image.LANCZOS)
else:
    crop = placeholder(196, 246)
card.paste(crop, ((W - 196) // 2, 116))
d.rectangle([(W - 196) // 2 - 3, 113, (W + 196) // 2 + 2, 116 + 246 + 2], outline='#C9D3E6', width=3)
centered(d, 380, PROFILE['name'], font(58), '#14213D')
centered(d, 456, PROFILE['role'], font(27, bold=False), '#3A4A6B')
d.rectangle([0, H - 26, W, H], fill='#FFD23F')
out = os.environ.get('CARD_OUT') or os.path.join(ROOT, 'build', 'tex', 'card.png')
os.makedirs(os.path.dirname(out), exist_ok=True)
card.save(out)
print('card ok', '(사진)' if use_photo else '(자리표시)', out)
