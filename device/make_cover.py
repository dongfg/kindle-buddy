"""Deterministic black-and-white library cover, rendered with device fonts."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

im = Image.new('L', (600, 800), 255)
d = ImageDraw.Draw(im)
d.rectangle((28, 28, 571, 771), outline=0, width=3)
# Calendar page with two binding rings.
d.rounded_rectangle((112, 220, 488, 570), radius=24, outline=0, width=8)
d.line((116, 305, 484, 305), fill=0, width=7)
for x in (197, 403):
    d.rounded_rectangle((x-8, 193, x+8, 251), radius=8, fill=0)
for y in (354, 418, 482):
    for x in (165, 233, 301):
        d.rounded_rectangle((x, y, x+22, y+22), radius=3, fill=0)
# Clock overlaps the lower-right calendar corner.
d.ellipse((324, 392, 516, 584), fill=255, outline=0, width=8)
cx, cy = 420, 488
d.line((cx, cy, cx, cy-58), fill=0, width=8)
d.line((cx, cy, cx+44, cy+26), fill=0, width=8)
d.ellipse((cx-6, cy-6, cx+6, cy+6), fill=0)
for x0, y0, x1, y1 in ((420,409,420,423),(420,553,420,567),(341,488,355,488),(485,488,499,488)):
    d.line((x0,y0,x1,y1), fill=0, width=5)
face = ImageFont.truetype('/usr/java/lib/fonts/Amazon-Ember-Medium.ttf', 44)
text = 'Kindle Buddy'
b = d.textbbox((0,0), text, font=face)
d.text(((600-b[2]-b[0])/2, 660-b[1]), text, font=face, fill=0)
im.convert('1').save(str(Path(__file__).parent/'cover.png'))
