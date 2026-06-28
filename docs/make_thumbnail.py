"""Generate the Kaggle writeup card thumbnail (1200x630 PNG).

Run:  python docs/make_thumbnail.py   ->  docs/thumbnail.png
Pure-Pillow so it works on Windows without extra native libs.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
OUT = Path(__file__).resolve().parent / "thumbnail.png"
FONTS = Path("C:/Windows/Fonts")


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


# --- canvas with a vertical gradient background ---------------------------
img = Image.new("RGB", (W, H), "#0B1220")
draw = ImageDraw.Draw(img)
top, bot = (11, 18, 32), (19, 28, 46)
for y in range(H):
    t = y / H
    draw.line([(0, y), (W, y)],
              fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))

ACCENT = "#5B8DEF"
GREEN = "#34D399"
CARD = "#1E293B"
MUTE = "#94A3B8"

f_title = font("segoeuib.ttf", 76)
f_sub = font("segoeui.ttf", 30)
f_box = font("segoeuib.ttf", 26)
f_boxsub = font("segoeui.ttf", 19)
f_chip = font("segoeuib.ttf", 22)

# --- accent bar + title ---------------------------------------------------
draw.rounded_rectangle([70, 78, 86, 150], radius=8, fill=ACCENT)
draw.text((110, 70), "Pipeline Co-Pilot", font=f_title, fill="#FFFFFF")
draw.text((112, 162),
          "A multi-agent sales assistant  ·  Google ADK + custom MCP server",
          font=f_sub, fill=MUTE)

# --- mini architecture diagram: Coordinator -> Analyst / Writer -----------
def box(x, y, w, h, title, sub, color):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=CARD,
                           outline=color, width=3)
    draw.text((x + 22, y + 18), title, font=f_box, fill="#FFFFFF")
    draw.text((x + 22, y + 50), sub, font=f_boxsub, fill=MUTE)

def arrow(x1, y, x2):
    draw.line([(x1, y), (x2 - 12, y)], fill=ACCENT, width=4)
    draw.polygon([(x2, y), (x2 - 14, y - 8), (x2 - 14, y + 8)], fill=ACCENT)

box(110, 268, 300, 96, "Coordinator", "routes the request", ACCENT)
arrow(410, 316, 470)
box(470, 244, 300, 82, "Pipeline Analyst", "ranks at-risk deals", GREEN)
box(470, 338, 300, 82, "Outreach Writer", "drafts grounded email", GREEN)

# both specialists call the shared CRM MCP server
box(810, 296, 300, 82, "CRM MCP server", "get_deals · log_activity", MUTE)
arrow(770, 332, 808)

# --- key-concept chips ----------------------------------------------------
chips = ["Multi-agent", "Custom MCP", "Deployable", "Secure"]
x = 110
for c in chips:
    w = draw.textlength(c, font=f_chip) + 44
    draw.rounded_rectangle([x, 500, x + w, 552], radius=26, fill="#13233D",
                           outline=ACCENT, width=2)
    draw.text((x + 22, 512), c, font=f_chip, fill="#DBEAFE")
    x += w + 20

draw.text((110, 575), "Flags at-risk deals by dollar value · drafts follow-ups · auth-gated writes · PII-safe logs",
          font=f_boxsub, fill=MUTE)

img.save(OUT, "PNG")
print(f"wrote {OUT}  ({OUT.stat().st_size // 1024} KB)")
