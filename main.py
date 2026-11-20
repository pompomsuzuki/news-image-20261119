#!/usr/bin/env python3
"""The World in One Day - 19 November 2026.

Draws a newspaper front page that sums up the world news of Thursday
19 November 2026 in a single 1024x1024 PNG, using only the Python
standard library. The output is fully deterministic: the same bytes
are written on every run.

Stories shown (all first reported on 19 November 2026):
  * Trump, Xi and Putin hold their first trilateral summit in
    Shenzhen and issue a joint declaration: "a nuclear war cannot
    be won and must never be fought".
  * The International Court of Justice rules that Myanmar committed
    genocide against the Rohingya - the first time a state has been
    held responsible for genocide at the World Court.
  * Grand Theft Auto VI launches, 13 years after GTA V.
  * NASA confirms Voyager 1 has reached one light-day from Earth.
  * Anthropic (ANT) makes the biggest IPO debut in history on
    Nasdaq: priced at $83, about $81 billion raised.
"""

import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (247, 241, 227)
INK = (26, 26, 26)
RED = (179, 53, 43)
BLUE = (36, 86, 166)
GOLD = (217, 164, 65)
TEAL = (23, 124, 117)
GREY = (110, 104, 92)
WHITE = (255, 255, 255)
SKY = (16, 24, 64)
PINK = (232, 93, 158)
GREEN = (46, 139, 87)

# ---------------------------------------------------------------- canvas

class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, color)

    def frame(self, x, y, w, h, color, t=3):
        self.rect(x, y, w, t, color)
        self.rect(x, y + h - t, w, t, color)
        self.rect(x, y, t, h, color)
        self.rect(x + w - t, y, t, h, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        r = t // 2
        while True:
            for yy in range(y0 - r, y0 - r + t):
                for xx in range(x0 - r, x0 - r + t):
                    self.set(xx, yy, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, rad, color, fill=False):
        if fill:
            for yy in range(cy - rad, cy + rad + 1):
                for xx in range(cx - rad, cx + rad + 1):
                    if (xx - cx) ** 2 + (yy - cy) ** 2 <= rad * rad:
                        self.set(xx, yy, color)
        else:
            for yy in range(cy - rad, cy + rad + 1):
                for xx in range(cx - rad, cx + rad + 1):
                    d = (xx - cx) ** 2 + (yy - cy) ** 2
                    if rad * rad - 2 * rad <= d <= rad * rad + 2 * rad:
                        self.set(xx, yy, color)

    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        minx = max(0, min(x0, x1, x2))
        maxx = min(self.w - 1, max(x0, x1, x2))
        miny = max(0, min(y0, y1, y2))
        maxy = min(self.h - 1, max(y0, y1, y2))

        def edge(ax, ay, bx, by, px_, py_):
            return (px_ - ax) * (by - ay) - (py_ - ay) * (bx - ax)

        for yy in range(miny, maxy + 1):
            for xx in range(minx, maxx + 1):
                d0 = edge(x0, y0, x1, y1, xx, yy)
                d1 = edge(x1, y1, x2, y2, xx, yy)
                d2 = edge(x2, y2, x0, y0, xx, yy)
                if (d0 >= 0 and d1 >= 0 and d2 >= 0) or \
                   (d0 <= 0 and d1 <= 0 and d2 <= 0):
                    self.set(xx, yy, color)

# ---------------------------------------------------------------- font
# 5x7 pixel font, one string per row, '#' marks a filled pixel.

FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    'X': ("#...#", ".#.#.", "..#..", "..#..", ".#.#.", "#...#", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#..##", "#.#.#", "#.#.#", "##..#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "..##.", ".#...", "#....", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "'": ("..#..", "..#..", "..#..", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    '$': ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    '+': (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    '(': ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ')': ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
}


def text_width(s, scale):
    if not s:
        return 0
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, scale, color, bold=False):
    for ch in s.upper():
        glyph = FONT.get(ch, FONT[' '])
        passes = [(0, 0)]
        if bold:
            passes.append((max(1, scale // 2), 0))
        for row_i, row in enumerate(glyph):
            for col_i, cell in enumerate(row):
                if cell == '#':
                    for ox, oy in passes:
                        cv.rect(x + col_i * scale + ox,
                                y + row_i * scale + oy,
                                scale, scale, color)
        x += 6 * scale
    return x


def draw_centered(cv, cx, y, s, scale, color, bold=False):
    x = cx - text_width(s, scale) // 2
    draw_text(cv, x, y, s, scale, color, bold)


def draw_right(cv, rx, y, s, scale, color, bold=False):
    x = rx - text_width(s, scale)
    draw_text(cv, x, y, s, scale, color, bold)

# ---------------------------------------------------------------- icons

def flag_us(cv, x, y, w, h):
    stripe = h // 7
    for i in range(7):
        cv.rect(x, y + i * stripe, w, stripe, RED if i % 2 == 0 else WHITE)
    cv.rect(x, y, w * 2 // 5, stripe * 4, BLUE)
    for r in range(4):
        for cix in range(5):
            cv.set(x + 4 + cix * 7, y + 3 + r * 6, WHITE)
            cv.rect(x + 4 + cix * 7, y + 3 + r * 6, 2, 2, WHITE)


def flag_cn(cv, x, y, w, h):
    cv.rect(x, y, w, h, RED)
    star = [(x + 12, y + 10), (x + 26, y + 6), (x + 30, y + 14),
            (x + 30, y + 24), (x + 26, y + 32)]
    for sx, sy in star:
        cv.rect(sx - 2, sy - 2, 5, 5, GOLD)


def flag_ru(cv, x, y, w, h):
    third = h // 3
    cv.rect(x, y, w, third, WHITE)
    cv.rect(x, y + third, w, third, BLUE)
    cv.rect(x, y + 2 * third, w, h - 2 * third, RED)


def scales_icon(cv, cx, top, color):
    # central post
    cv.line(cx, top, cx, top + 92, color, 5)
    # beam
    cv.line(cx - 62, top + 8, cx + 62, top + 8, color, 5)
    cv.circle(cx, top + 2, 6, color, fill=True)
    # pans
    for sgn in (-1, 1):
        px = cx + sgn * 62
        cv.line(px, top + 8, px - 20, top + 52, color, 3)
        cv.line(px, top + 8, px + 20, top + 52, color, 3)
        cv.line(px - 26, top + 52, px + 26, top + 52, color, 4)
        for xx in range(px - 26, px + 27):
            depth = 10 - abs(xx - px) * 10 // 27
            cv.line(xx, top + 52, xx, top + 52 + depth, color, 1)
    # base
    cv.line(cx - 26, top + 98, cx + 26, top + 98, color, 6)


def palm_icon(cv, cx, base_y, color, sun_color):
    cv.circle(cx + 62, base_y - 118, 22, sun_color, fill=True)
    # trunk
    cv.line(cx - 12, base_y, cx + 6, base_y - 104, color, 8)
    top = (cx + 6, base_y - 104)
    # fronds fanning out from the crown
    # fronds: (dx, peak height above crown, end height vs crown)
    fronds = [(-66, -30, -6), (-48, -44, -16), (-20, -52, -26),
              (12, -50, -28), (42, -42, -18), (64, -28, -4),
              (-72, -16, 6), (72, -12, 8)]
    for dx, peak, drop in fronds:
        mx = top[0] + dx // 2
        my = top[1] + peak
        cv.line(top[0], top[1], mx, my, color, 4)
        cv.line(mx, my, top[0] + dx, top[1] + drop, color, 4)
    # coconuts
    cv.circle(top[0] - 6, top[1] + 8, 5, color, fill=True)
    cv.circle(top[0] + 6, top[1] + 8, 5, color, fill=True)


def voyager_icon(cv, x, y):
    # star field
    stars = [(6, 8), (38, 22), (70, 4), (104, 30), (140, 10), (176, 26),
             (210, 6), (244, 20), (20, 52), (250, 54), (58, 66), (228, 74)]
    for sx, sy in stars:
        cv.rect(x + sx, y + sy, 3, 3, WHITE)
    # Earth, far bottom-left
    cv.circle(x + 26, y + 128, 11, BLUE, fill=True)
    cv.circle(x + 22, y + 124, 4, GREEN, fill=True)
    # dashed signal arc from Earth toward the probe
    for i in range(9):
        sx = x + 40 + i * 16
        sy = y + 118 - i * 7
        cv.rect(sx, sy, 7, 3, GOLD)
    # probe body
    bx, by = x + 196, y + 44
    cv.rect(bx - 10, by - 8, 20, 16, GOLD)
    # big dish
    for r in range(30, 0, -2):
        cv.circle(bx - 34, by - 20, r, WHITE)
    cv.circle(bx - 34, by - 20, 8, GREY, fill=True)
    cv.line(bx - 34, by - 20, bx - 12, by - 6, GREY, 3)
    # boom and magnetometer tail
    cv.line(bx + 10, by + 4, bx + 62, by + 26, WHITE, 3)
    cv.line(bx - 6, by + 8, bx - 30, by + 62, WHITE, 3)
    cv.rect(bx - 34, by + 62, 8, 8, WHITE)


def chart_icon(cv, x, y, w, h, color):
    cv.line(x, y + h, x + w, y + h, color, 3)
    cv.line(x, y, x, y + h, color, 3)
    pts = [(x + 8, y + h - 18), (x + 52, y + h - 34), (x + 92, y + h - 26),
           (x + 132, y + h - 58), (x + 172, y + h - 50), (x + w - 14, y + 12)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], color, 5)
    # arrow head
    ax, ay = pts[-1]
    cv.line(ax, ay, ax - 20, ay + 2, color, 5)
    cv.line(ax, ay, ax - 4, ay + 18, color, 5)

# ---------------------------------------------------------------- panels

def masthead(cv):
    cv.rect(28, 30, W - 56, 4, INK)
    draw_centered(cv, W // 2, 48, "THE WORLD IN ONE DAY", 7, INK, bold=True)
    cv.rect(28, 108, W - 56, 3, RED)
    draw_centered(cv, W // 2, 122, "THURSDAY 19 NOVEMBER 2026", 4, RED,
                  bold=True)
    draw_text(cv, 28, 122, "EST. 2026", 2, GREY)
    draw_right(cv, W - 28, 122, "ONE PAGE", 2, GREY)
    cv.rect(28, 152, W - 56, 6, INK)


def lead_panel(cv, x, y, w, h):
    cv.frame(x, y, w, h, INK, 3)
    draw_text(cv, x + 22, y + 18, "SHENZHEN - APEC SUMMIT", 3, RED, bold=True)
    # flags row
    fy = y + 66
    fw, fh = 132, 84
    gap = (w - 44 - 3 * fw) // 2
    flag_us(cv, x + 22, fy, fw, fh)
    flag_cn(cv, x + 22 + (fw + gap), fy, fw, fh)
    flag_ru(cv, x + 22 + 2 * (fw + gap), fy, fw, fh)
    cv.rect(x + 22, fy + fh + 12, w - 44, 3, GREY)
    hy = fy + fh + 34
    draw_text(cv, x + 22, hy, "TRUMP XI PUTIN", 5, INK, bold=True)
    draw_text(cv, x + 22, hy + 48, "MEET IN SHENZHEN", 5, INK, bold=True)
    sy = hy + 112
    draw_text(cv, x + 22, sy, "FIRST US-CHINA-RUSSIA SUMMIT", 3, TEAL,
              bold=True)
    draw_text(cv, x + 22, sy + 34, "JOINT PEACE DECLARATION:", 3, INK)
    draw_text(cv, x + 22, sy + 68, "\"A NUCLEAR WAR MUST\"", 3, RED)
    draw_text(cv, x + 22, sy + 100, "\"NEVER BE FOUGHT\"", 3, RED)


def icj_panel(cv, x, y, w, h):
    cv.frame(x, y, w, h, INK, 3)
    draw_centered(cv, x + w // 2, y + 18, "THE HAGUE", 3, RED, bold=True)
    scales_icon(cv, x + w // 2, y + 62, INK)
    hy = y + 196
    draw_centered(cv, x + w // 2, hy, "WORLD COURT:", 4, INK, bold=True)
    draw_centered(cv, x + w // 2, hy + 40, "MYANMAR COMMITTED", 3, INK,
                  bold=True)
    draw_centered(cv, x + w // 2, hy + 74, "GENOCIDE", 6, RED, bold=True)
    sy = hy + 138
    lines = ["FIRST STATE EVER HELD",
             "RESPONSIBLE FOR GENOCIDE",
             "AGAINST THE ROHINGYA -",
             "CASE BROUGHT BY THE GAMBIA"]
    for i, ln in enumerate(lines):
        draw_centered(cv, x + w // 2, sy + i * 24, ln, 2, INK)


def gta_panel(cv, x, y, w, h):
    cv.frame(x, y, w, h, INK, 3)
    palm_icon(cv, x + w // 2, y + 148, TEAL, PINK)
    hy = y + 164
    draw_centered(cv, x + w // 2, hy, "GTA VI", 5, INK, bold=True)
    draw_centered(cv, x + w // 2, hy + 44, "IS HERE", 5, RED, bold=True)
    sy = hy + 88
    draw_centered(cv, x + w // 2, sy, "13 YEARS AFTER GTA V", 2, INK)
    draw_centered(cv, x + w // 2, sy + 22, "RAVE REVIEWS - RECORD", 2, INK)
    draw_centered(cv, x + w // 2, sy + 44, "PRESALES $1.5 BILLION", 2, INK)


def voyager_panel(cv, x, y, w, h):
    cv.rect(x, y, w, h, SKY)
    cv.frame(x, y, w, h, INK, 3)
    voyager_icon(cv, x + 22, y + 14)
    hy = y + 176
    draw_centered(cv, x + w // 2, hy, "VOYAGER 1", 4, WHITE, bold=True)
    draw_centered(cv, x + w // 2, hy + 42, "ONE LIGHT-DAY", 3, GOLD, bold=True)
    draw_centered(cv, x + w // 2, hy + 68, "FROM EARTH", 3, GOLD, bold=True)
    draw_centered(cv, x + w // 2, hy + 98, "NASA CONFIRMS IT", 2, WHITE)
    draw_centered(cv, x + w // 2, hy + 118, "SIGNALS TAKE 24 HOURS", 2, WHITE)


def ipo_panel(cv, x, y, w, h):
    cv.frame(x, y, w, h, INK, 3)
    chart_icon(cv, x + 52, y + 30, w - 104, 108, GREEN)
    hy = y + 168
    draw_centered(cv, x + w // 2, hy, "BIGGEST IPO EVER", 3, INK, bold=True)
    draw_centered(cv, x + w // 2, hy + 34, "ANTHROPIC (ANT) DEBUTS", 2, INK)
    sy = hy + 62
    draw_centered(cv, x + w // 2, sy, "ON NASDAQ AT $83 A SHARE", 2, INK)
    draw_centered(cv, x + w // 2, sy + 24, "$81 BILLION RAISED", 2, RED)
    draw_centered(cv, x + w // 2, sy + 48, "AN ALL-TIME RECORD", 2, RED)


def footer(cv):
    cv.rect(28, 950, W - 56, 3, INK)
    draw_centered(cv, W // 2, 962, "FIVE STORIES - ONE DAY - ONE PAGE", 3,
                  INK, bold=True)
    cv.rect(28, 990, W - 56, 4, INK)


def build():
    cv = Canvas(W, H, PAPER)
    masthead(cv)
    lead_panel(cv, 28, 178, 604, 428)
    icj_panel(cv, 648, 178, 348, 428)
    gta_panel(cv, 28, 622, 314, 312)
    voyager_panel(cv, 355, 622, 314, 312)
    ipo_panel(cv, 682, 622, 314, 312)
    footer(cv)
    return cv

# ---------------------------------------------------------------- png out

def png_bytes(cv):
    raw = bytearray()
    row_len = cv.w * 3
    for yy in range(cv.h):
        raw.append(0)
        raw += cv.px[yy * row_len:(yy + 1) * row_len]

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(build())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(data)
    print("wrote", path, len(data), "bytes")


if __name__ == "__main__":
    main()
