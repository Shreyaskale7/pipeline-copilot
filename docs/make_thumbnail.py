"""Generate the Kaggle writeup card thumbnail (1200x630 PNG) — professional grade.

Techniques used for a polished result:
  * 2x supersampling (render at 2400x1260, downscale with LANCZOS) -> crisp edges.
  * Soft drop shadows + a subtle accent glow via Gaussian blur on RGBA layers.
  * A consistent 72px margin grid and symmetric tree-style connectors.

Run:  python docs/make_thumbnail.py   ->  docs/thumbnail.png
Pure-Pillow so it works on Windows without extra native libs.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Logical canvas; we render at S x and downscale for anti-aliasing.
W, H, S = 1200, 630, 2
OUT = Path(__file__).resolve().parent / "thumbnail.png"
FONTS = Path("C:/Windows/Fonts")

# --- palette ---------------------------------------------------------------
BG_TOP, BG_BOT = (11, 17, 30), (16, 27, 47)
ACCENT = (94, 141, 239)
GREEN = (52, 211, 153)
MUTED = (148, 163, 184)
CARD = (24, 35, 58)
WHITE = (244, 247, 252)
DIVIDER = (30, 41, 59)
CHIP_BG = (20, 34, 60)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), int(size * S))


F_TITLE = font("segoeuib.ttf", 58)
F_SUB = font("segoeui.ttf", 25)
F_TAG = font("segoeuib.ttf", 19)
F_BOX = font("segoeuib.ttf", 24)
F_BOXSUB = font("segoeui.ttf", 18)
F_CHIP = font("segoeuib.ttf", 21)
F_FOOT = font("segoeui.ttf", 18)


# --- scaled drawing helpers (work in logical coords, draw at S x) -----------
def sc(seq):
    return [v * S for v in seq]


def base_canvas():
    """Vertical gradient background as an RGBA image."""
    img = Image.new("RGB", (W * S, H * S), BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(H * S):
        t = y / (H * S)
        d.line([(0, y), (W * S, y)],
               fill=tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3)))
    return img.convert("RGBA")


def blurred_layer(draw_fn, blur):
    """Make a transparent layer, let draw_fn paint on it, then Gaussian-blur it."""
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    return layer.filter(ImageFilter.GaussianBlur(blur * S))


# Box specs: (x, y, w, h, title, subtitle, border_color)
BOXES = [
    (72, 250, 300, 110, "Coordinator", "routes the request", ACCENT),
    (470, 232, 300, 86, "Pipeline Analyst", "ranks at-risk deals", GREEN),
    (470, 350, 300, 86, "Outreach Writer", "drafts grounded email", GREEN),
    (836, 296, 292, 86, "CRM MCP server", "4 tools · risk + security", MUTED),
]


def main():
    img = base_canvas()

    # 1) subtle accent glow, top-right, for depth.
    img = Image.alpha_composite(img, blurred_layer(
        lambda d: d.ellipse(sc([720, -150, 1340, 360]), fill=(94, 141, 239, 60)), blur=70))

    # 2) soft drop shadows beneath every card.
    def shadows(d):
        for x, y, w, h, *_ in BOXES:
            d.rounded_rectangle(sc([x + 2, y + 12, x + w + 2, y + h + 14]),
                                radius=16 * S, fill=(0, 0, 0, 120))
    img = Image.alpha_composite(img, blurred_layer(shadows, blur=12))

    d = ImageDraw.Draw(img)

    def text(xy, s, fnt, fill):
        d.text((xy[0] * S, xy[1] * S), s, font=fnt, fill=fill)

    def textlen(s, fnt):
        return d.textlength(s, font=fnt) / S

    def rrect(box, r, **kw):
        d.rounded_rectangle(sc(box), radius=int(r * S), **kw)

    def hline(pts, w, fill):
        d.line([(p[0] * S, p[1] * S) for p in pts], width=int(w * S), fill=fill)

    def arrow(x1, y, x2, color=ACCENT):
        hline([(x1, y), (x2 - 9, y)], 3, color)
        head = [(x2, y), (x2 - 13, y - 8), (x2 - 13, y + 8)]
        d.polygon([(px * S, py * S) for px, py in head], fill=color)

    # --- logo mark: a 3-node graph = coordinator + two sub-agents ----------
    rrect([72, 64, 136, 128], 16, fill=ACCENT)
    nodes = [(104, 82), (88, 114), (120, 114)]
    for a in (nodes[1], nodes[2]):
        hline([nodes[0], a], 3, WHITE)
    hline([nodes[1], nodes[2]], 3, WHITE)
    for nx, ny in nodes:
        d.ellipse(sc([nx - 5, ny - 5, nx + 5, ny + 5]), fill=WHITE)

    # --- title + subtitle --------------------------------------------------
    text((160, 58), "Pipeline Co-Pilot", F_TITLE, WHITE)
    text((162, 130), "A multi-agent sales assistant  ·  Google ADK + custom MCP server",
         F_SUB, MUTED)

    # --- top-right capstone tag pill --------------------------------------
    tag = "Vibe Coding Capstone"
    tw = textlen(tag, F_TAG) + 40
    rrect([1128 - tw, 70, 1128, 110], 20, outline=ACCENT, width=2, fill=CHIP_BG)
    text((1128 - tw + 20, 80), tag, F_TAG, (219, 234, 254))

    # --- architecture cards ------------------------------------------------
    for x, y, w, h, title, sub, color in BOXES:
        rrect([x, y, x + w, y + h], 16, fill=CARD, outline=color, width=3)
        cy = y + h / 2
        text((x + 22, cy - 28), title, F_BOX, WHITE)
        text((x + 22, cy + 6), sub, F_BOXSUB, MUTED)

    # left tree connector: Coordinator -> Analyst / Writer
    hline([(372, 305), (432, 305)], 3, ACCENT)
    hline([(432, 275), (432, 393)], 3, ACCENT)
    arrow(432, 275, 470)
    arrow(432, 393, 470)
    # right tree connector: Analyst / Writer -> MCP server
    hline([(770, 275), (808, 275)], 3, ACCENT)
    hline([(770, 393), (808, 393)], 3, ACCENT)
    hline([(808, 275), (808, 393)], 3, ACCENT)
    arrow(808, 339, 836)

    # --- footer: divider, concept chips (centered), tagline ----------------
    hline([(72, 500), (1128, 500)], 1, DIVIDER)

    chips = ["Multi-agent", "Custom MCP", "Deployable", "Secure", "Eval-tested"]
    gap = 18
    widths = [textlen(c, F_CHIP) + 44 for c in chips]
    start = (W - (sum(widths) + gap * (len(chips) - 1))) / 2
    x = start
    for c, cw in zip(chips, widths):
        rrect([x, 522, x + cw, 568], 23, fill=CHIP_BG, outline=ACCENT, width=2)
        text((x + 22, 534), c, F_CHIP, (219, 234, 254))
        x += cw + gap

    text((72, 588),
         "Ranks at-risk deals by dollar value  ·  drafts grounded follow-ups  ·  "
         "auth-gated, PII-safe, eval-tested",
         F_FOOT, MUTED)

    # downscale for crisp anti-aliased output.
    img.convert("RGB").resize((W, H), Image.LANCZOS).save(OUT, "PNG")
    print(f"wrote {OUT}  ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
