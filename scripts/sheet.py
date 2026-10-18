"""이미지 여러 장을 가로로 붙여 한 장으로. python sheet.py out.png h img1 img2 ..."""
import sys
from PIL import Image
out, h = sys.argv[1], int(sys.argv[2])
ims = []
for f in sys.argv[3:]:
    im = Image.open(f).convert('RGB')
    ims.append(im.resize((int(h * im.width / im.height), h)))
sheet = Image.new('RGB', (sum(i.width for i in ims), h), 'white')
x = 0
for im in ims:
    sheet.paste(im, (x, 0))
    x += im.width
sheet.save(out)
