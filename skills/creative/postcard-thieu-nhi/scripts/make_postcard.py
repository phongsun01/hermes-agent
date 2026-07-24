#!/opt/hermes/.venv/bin/python3
"""Create a children's story postcard - Sóc Nâu & Thỏ Trắng"""
from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT = "/opt/data/scripts/postcard_socnau.png"

# Dimensions
W, H = 1080, 1350  # portrait - good for Zalo

# Colors
BG_TOP = (255, 220, 180)   # warm peach
BG_BOT = (180, 120, 60)    # brown
TEXT_COLOR = (50, 30, 10)
TITLE_COLOR = (120, 60, 20)
ACCENT = (220, 120, 50)

img = Image.new("RGB", (W, H), BG_TOP)
draw = ImageDraw.Draw(img)

# Gradient background
for y in range(H):
    r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * y / H)
    g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * y / H)
    b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * y / H)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# Decorative frame
margin = 30
for i in range(3):
    draw.rectangle(
        [margin + i*8, margin + i*8, W - margin - i*8, H - margin - i*8],
        outline=(255 - i*20, 220 - i*20, 160 - i*20),
        width=3
    )

# Title
title = "🐿️ Câu chuyện của Sóc Nâu 🐿️"
subtitle = "Bài học về sự sẻ chia"

# Try to load a nice font
font_dir = "/usr/share/fonts/truetype"
regular_font = None
bold_font = None

for root, dirs, files in os.walk(font_dir):
    for f in files:
        path = os.path.join(root, f)
        if "LiberationSans-Bold.ttf" in path and bold_font is None:
            bold_font = path
        if "LiberationSans-Regular.ttf" in path and regular_font is None:
            regular_font = path
        if "FreeSans.ttf" in path and regular_font is None:
            regular_font = path

try:
    font_title = ImageFont.truetype(bold_font or regular_font, 52)
    font_subtitle = ImageFont.truetype(regular_font, 36)
    font_story = ImageFont.truetype(regular_font, 32)
    font_sign = ImageFont.truetype(regular_font or bold_font, 30)
except Exception:
    font_title = ImageFont.load_default()
    font_subtitle = font_title
    font_story = font_title
    font_sign = font_title

# Center title
bbox = draw.textbbox((0, 0), title, font=font_title)
tw = bbox[2] - bbox[0]
draw.text(((W - tw)//2, 60), title, fill=TITLE_COLOR, font=font_title)

# Center subtitle
bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
tw = bbox[2] - bbox[0]
draw.text(((W - tw)//2, 130), subtitle, fill=ACCENT, font=font_subtitle)

# Decorative line under title
draw.rectangle([200, 175, W-200, 180], fill=ACCENT)
draw.rectangle([300, 172, W-300, 183], fill=(255, 200, 150))

# Story text
story_lines = [
    "Có một chú Sóc Nâu rất thích ăn hạt dẻ.",
    "Nhưng mỗi lần nhặt được hạt dẻ,",
    "bạn ấy giấu đi, không chia cho ai.",
    "",
    "Một hôm, Sóc Nâu bị trượt chân",
    "rơi xuống khe đá.",
    "Bạn ấy kêu cứu mãi mà chẳng ai đến giúp",
    "— vì hồi trước bạn ấy chẳng bao giờ",
    "giúp ai cả.",
    "",
    "Cuối cùng, một chú Thỏ Trắng nhỏ bé",
    "đã kéo Sóc Nâu lên.",
    "Sóc Nâu xấu hổ nói: 'Cảm ơn bạn!'",
    "",
    "Từ hôm đó, Sóc Nâu học được rằng",
    "lời cảm ơn và sự sẻ chia",
    "làm cuộc sống ấm áp hơn rất nhiều ❤️",
]

y_start = 230
line_height = 48
y = y_start

# Background box for story
box_pad = 25
draw.rounded_rectangle(
    [margin + 20, y_start - 15, W - margin - 20, y_start + len(story_lines) * line_height + 15],
    radius=20,
    fill=(255, 255, 240, 180)  # warm white
)

for line in story_lines:
    bbox = draw.textbbox((0, 0), line, font=font_story)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    draw.text((x, y), line, fill=TEXT_COLOR, font=font_story)
    y += line_height

# Footer
footer_y = y + 60
draw.rectangle([300, footer_y, W-300, footer_y+5], fill=ACCENT)

footer_text = "💛 Bài học dành cho Bi Bống và Bi Béo 💛"
bbox = draw.textbbox((0, 0), footer_text, font=font_sign)
tw = bbox[2] - bbox[0]
draw.text(((W - tw)//2, footer_y + 20), footer_text, fill=TITLE_COLOR, font=font_sign)

# Bottom decoration - simple acorns/leaves
for i, (x, leaf_color) in enumerate([
    (100, (180, 100, 30)), (W-100, (180, 100, 30)),
    (200, (200, 140, 50)), (W-200, (200, 140, 50)),
]):
    draw.ellipse([x-10, H-100, x+10, H-80], fill=leaf_color)
    draw.polygon([(x, H-110), (x-8, H-95), (x+8, H-95)], fill=leaf_color)

# Save
img.save(OUTPUT, "PNG")
print(f"Saved to {OUTPUT}")
