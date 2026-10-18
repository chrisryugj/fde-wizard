"""엔드카드 썸네일 3장(모델·리그·애니메이션)을 렌더 결과에서 잘라 comp/thumbs/ 에 저장.
.venv/bin/python scripts/thumbs.py   (assemble.sh A 가 먼저 부른다)"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, 'renders', 'A')
OUT = os.path.join(ROOT, 'comp', 'thumbs')
BOX = (330, 40, 1610, 960)  # 1080p 프레임에서 모자 끝~발이 들어오는 390:280 영역


def save(im, name, box=BOX):
    im.convert('RGB').crop(box).resize((390, 280), Image.LANCZOS).save(os.path.join(OUT, name), quality=92)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    save(Image.open(os.path.join(R, 'a04_turntable', 'clay', '0001.png')), 'model.jpg')
    clay = Image.open(os.path.join(R, 'a05_rig', 'clay', '0054.png')).convert('RGBA')
    clay.alpha_composite(Image.open(os.path.join(R, 'a05_rig', 'bones', '0054.png')).convert('RGBA'))
    save(clay, 'rig.jpg')
    save(Image.open(os.path.join(R, 'a10_cast', 'beauty', '0092.png')), 'anim.jpg', (440, 40, 1720, 960))  # 곰돌이까지
    print('thumbs ok')
