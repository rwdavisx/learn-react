#!/usr/bin/env python3
"""Render the 'BT Goes Viral' YouTube intro (1920x1080 @ 30 fps).

Usage:
  render.py ASSETS_DIR video                    -> writes raw rgb24 frames to stdout
  render.py ASSETS_DIR preview OUT_DIR t1 t2 ... -> PNG stills at the given times

ASSETS_DIR must contain landmask.png (equirectangular, 3600x1800) and src/f_###.png
(the source clip, 16 fps, watermark cropped).

Timeline: 0-2.8 cold open (ECG + outbreak map + trailer text) | 2.8 drop -> clip in HUD panel
| 8.8 drop -> logo reveal | 10.8 subscribe click | 12.8 end.
"""
import functools
import glob
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
DUR = 12.8
NF = int(round(DUR * FPS))
T_DROP, T_LOGO, T_SUB, T_END = 2.8, 8.8, 10.8, 12.8
SRC_FPS = 16
ASSETS = sys.argv[1]

FONTS = {
    "black": "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
    "xbold": "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "bold": "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "semi": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
    "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
}

NAVY0 = (5, 6, 8)
NAVY1 = (24, 26, 31)
ACCENT = (232, 28, 40)
STEEL = (196, 202, 212)
WHITE = (242, 247, 255)
RED = (255, 38, 72)
YT_RED = (255, 0, 51)
DOT = (64, 68, 76)


# ------------------------------------------------------------------ math helpers
def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def prog(t, a, b):
    return clamp01((t - a) / (b - a))


def lerp(a, b, x):
    return a + (b - a) * x


def e_out3(x):
    return 1 - (1 - x) ** 3


def e_outexpo(x):
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def e_inout(x):
    return x * x * (3 - 2 * x)


def e_in3(x):
    return x ** 3


def mixc(c1, c2, x):
    return tuple(int(round(lerp(a, b, x))) for a, b in zip(c1, c2))


def rgba(c, a=1.0):
    return (int(c[0]), int(c[1]), int(c[2]), int(round(255 * clamp01(a))))


# ------------------------------------------------------------------ compositing
def new_layer(w=W, h=H):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def safe_ac(dst, src, x, y):
    """alpha_composite src onto dst at (x, y), clipping at the edges."""
    sx0, sy0 = max(0, -x), max(0, -y)
    dx0, dy0 = max(0, x), max(0, y)
    w = min(src.width - sx0, dst.width - dx0)
    h = min(src.height - sy0, dst.height - dy0)
    if w > 0 and h > 0:
        dst.alpha_composite(src, (dx0, dy0), (sx0, sy0, sx0 + w, sy0 + h))


def comp(buf, layer, opacity=1.0, x=0, y=0):
    """Alpha-composite an RGBA image onto the float RGB frame buffer at (x, y)."""
    if opacity <= 0:
        return
    bb = layer.getbbox()
    if not bb:
        return
    cx0, cy0 = max(0, x + bb[0]), max(0, y + bb[1])
    cx1, cy1 = min(W, x + bb[2]), min(H, y + bb[3])
    if cx0 >= cx1 or cy0 >= cy1:
        return
    a = np.asarray(layer.crop((cx0 - x, cy0 - y, cx1 - x, cy1 - y)), np.float32)
    al = a[..., 3:4] * (opacity / 255.0)
    region = buf[cy0:cy1, cx0:cx1]
    region *= 1 - al
    region += a[..., :3] * al


def glow(buf, layer, radius, strength=1.0, x=0, y=0):
    """Additive blurred copy of a layer (premultiplied, blurred at reduced res)."""
    if strength <= 0:
        return
    bb = layer.getbbox()
    if not bb:
        return
    pad = int(radius * 2.5) + 4
    x0, y0, x1, y1 = bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad
    sub = layer.crop((x0, y0, x1, y1))
    a = np.asarray(sub, np.float32)
    pm = (a[..., :3] * (a[..., 3:4] / 255.0)).astype(np.uint8)
    w, h = sub.size
    f = 4 if radius >= 12 else 2
    small = Image.fromarray(pm).resize((max(1, w // f), max(1, h // f)), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(radius / f))
    g = np.asarray(small.resize((w, h), Image.BILINEAR), np.float32) * strength
    X0, Y0 = x + x0, y + y0
    cx0, cy0, cx1, cy1 = max(0, X0), max(0, Y0), min(W, X0 + w), min(H, Y0 + h)
    if cx0 < cx1 and cy0 < cy1:
        buf[cy0:cy1, cx0:cx1] += g[cy0 - Y0:cy1 - Y0, cx0 - X0:cx1 - X0]


def ss_layer():
    """2x supersampled full-frame layer for anti-aliased vector drawing."""
    return Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))


# ------------------------------------------------------------------ text
@functools.lru_cache(maxsize=None)
def font(name, size):
    return ImageFont.truetype(FONTS[name], size)


def text_w(s, fname, size, tracking=0):
    f = font(fname, size)
    if tracking == 0:
        return f.getlength(s)
    return sum(f.getlength(c) for c in s) + tracking * max(0, len(s) - 1)


@functools.lru_cache(maxsize=2048)
def text_img(s, fname, size, color, tracking=0):
    f = font(fname, size)
    per_char = isinstance(color[0], tuple)
    adv = [f.getlength(c) for c in s]
    whole = tracking == 0 and not per_char
    width = f.getlength(s) if whole else sum(adv) + tracking * max(0, len(s) - 1)
    asc, desc = f.getmetrics()
    pad = int(size * 0.35) + 4
    img = Image.new("RGBA", (int(math.ceil(width)) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = pad + asc
    if whole:
        d.text((pad, base), s, font=f, fill=color, anchor="ls")
    else:
        x = pad
        for i, c in enumerate(s):
            d.text((x, base), c, font=f, fill=color[i] if per_char else color, anchor="ls")
            x += adv[i] + tracking
    return img, pad, base, width


def scale_alpha(img, a):
    if a >= 0.999:
        return img
    im = img.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im


def draw_text(layer, s, fname, size, color, x, base_y, tracking=0, align="l", alpha=1.0, clip=None, dx=0, dy=0):
    if not s or alpha <= 0.003:
        return 0
    img, pad, base, width = text_img(s, fname, size, color, tracking)
    if align == "c":
        x -= width / 2
    elif align == "r":
        x -= width
    px, py = int(round(x - pad + dx)), int(round(base_y - base + dy))
    img = scale_alpha(img, alpha)
    if clip is not None:
        y0, y1 = max(0, clip[0] - py), min(img.height, clip[1] - py)
        if y1 <= y0:
            return width
        img = img.crop((0, y0, img.width, y1))
        py += y0
    safe_ac(layer, img, px, py)
    return width


def reveal_words(layer, words, fname, size, colors, x_left, base_y, t, t0, stagger=0.08, dur=0.5, alpha=1.0):
    """Words slide up into place from behind a clip line, staggered."""
    f = font(fname, size)
    sp = f.getlength(" ")
    clip = (int(base_y - size * 1.1), int(base_y + size * 0.28))
    x = x_left
    for i, (w, c) in enumerate(zip(words, colors)):
        p = e_outexpo(prog(t, t0 + i * stagger, t0 + i * stagger + dur))
        if p > 0:
            draw_text(layer, w, fname, size, c, x, base_y, dy=(1 - p) * size * 1.15, clip=clip, alpha=alpha)
        x += f.getlength(w) + sp


def words_width(words, fname, size):
    f = font(fname, size)
    return sum(f.getlength(w) for w in words) + f.getlength(" ") * (len(words) - 1)


# ------------------------------------------------------------------ static backgrounds
@functools.lru_cache(maxsize=None)
def statics():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.45) / (H * 0.75)) ** 2)
    k = np.clip(1 - r, 0, 1)[..., None] ** 1.3
    bg = np.array(NAVY0, np.float32) * (1 - k) + np.array(NAVY1, np.float32) * k
    vign = (1 - 0.55 * np.clip(r - 0.35, 0, 1) ** 1.4).astype(np.float32)
    center_dim = np.exp(-((xx - W / 2) / 760) ** 2 - ((yy - 540) / 230) ** 2).astype(np.float32)
    glow_r = np.exp(-(((xx - W / 2) / 520) ** 2 + ((yy - 345) / 520) ** 2)).astype(np.float32)
    rng = np.random.default_rng(3)
    grain = [np.repeat(np.repeat(rng.normal(0, 2.6, (H // 2, W // 2)), 2, 0), 2, 1).astype(np.float32) for _ in range(6)]
    grid = np.zeros((H, W), np.float32)
    grid[::60, :] = 1
    grid[:, ::60] = 1
    return bg, vign, center_dim, glow_r, grain, grid


# ------------------------------------------------------------------ world map
S_MAP = 5.6
LON_C, LAT_C = 12.0, 14.0

CITIES = {
    "NYC": (-74.0, 40.7, "NEW YORK"), "LON": (-0.1, 51.5, "LONDON"), "LIM": (-77.0, -12.0, "LIMA"),
    "LAX": (-118.2, 34.0, "LOS ANGELES"), "NBO": (36.8, -1.3, "NAIROBI"), "MOW": (37.6, 55.8, "MOSCOW"),
    "RKV": (-21.9, 64.1, "REYKJAVIK"), "RIO": (-43.2, -22.9, "RIO DE JANEIRO"), "MEX": (-99.1, 19.4, "MEXICO CITY"),
    "DEL": (77.2, 28.6, "NEW DELHI"), "CPT": (18.4, -33.9, "CAPE TOWN"), "DXB": (55.3, 25.2, "DUBAI"),
    "BUE": (-58.4, -34.6, "BUENOS AIRES"), "ACC": (-0.2, 5.6, "ACCRA"), "BKK": (100.5, 13.75, "BANGKOK"),
    "KTM": (85.3, 27.7, "KATHMANDU"), "SYD": (151.2, -33.9, "SYDNEY"), "CAI": (31.2, 30.0, "CAIRO"),
    "SIN": (103.8, 1.35, "SINGAPORE"), "TYO": (139.7, 35.7, "TOKYO"), "AKL": (174.8, -36.8, "AUCKLAND"),
}
EDGES = [("NYC", "LON"), ("NYC", "LIM"), ("NYC", "LAX"), ("LON", "NBO"), ("LON", "MOW"), ("LON", "RKV"),
         ("LIM", "RIO"), ("LAX", "MEX"), ("NBO", "DEL"), ("NBO", "CPT"), ("MOW", "DXB"), ("RIO", "BUE"),
         ("RIO", "ACC"), ("DEL", "BKK"), ("DEL", "KTM"), ("CPT", "SYD"), ("ACC", "CAI"), ("BKK", "SIN"),
         ("BKK", "TYO"), ("SYD", "AKL")]


def proj(lon, lat, z=1.0):
    return W / 2 + (lon - LON_C) * S_MAP * z, H / 2 - (lat - LAT_C) * S_MAP * z


@functools.lru_cache(maxsize=None)
def dots():
    m = np.asarray(Image.open(os.path.join(ASSETS, "landmask.png")).convert("L"))
    pts, step = [], 1.6
    for row, lat in enumerate(np.arange(76, -56, -step)):
        off = step / 2 if row % 2 else 0.0
        for lon in np.arange(-180 + off, 180, step):
            if m[int((90 - lat) * 10), int((lon + 180) * 10) % 3600] > 127:
                pts.append((lon, lat))
    return np.array(pts)


@functools.lru_cache(maxsize=None)
def outbreak():
    arrive = {"NYC": 0.55}
    arcs = []
    for a, b in EDGES:
        t0 = arrive[a] + 0.03
        la, pa, _ = CITIES[a]
        lb, pb, _ = CITIES[b]
        dur = 0.22 + math.hypot(lb - la, pb - pa) / 330
        arcs.append((a, b, t0, dur))
        arrive[b] = t0 + dur
    return arrive, arcs


def cam_z(t):
    return 1.0 + 0.12 * e_inout(prog(t, 0.3, 2.8)) + 0.85 * e_in3(prog(t, 2.45, 2.8))


def arc_points(a, b, z, n=60):
    p0 = np.array(proj(*CITIES[a][:2], z))
    p2 = np.array(proj(*CITIES[b][:2], z))
    d = p2 - p0
    dist = np.hypot(*d)
    nrm = np.array([-d[1], d[0]]) / dist
    if nrm[1] > 0:
        nrm = -nrm
    p1 = (p0 + p2) / 2 + nrm * dist * 0.28
    u = np.linspace(0, 1, n)[:, None]
    return (1 - u) ** 2 * p0 + 2 * (1 - u) * u * p1 + u ** 2 * p2


def draw_map(buf, t, alpha):
    if alpha <= 0:
        return
    z = cam_z(t)
    arrive, arcs = outbreak()
    P = dots()
    X = W / 2 + (P[:, 0] - LON_C) * S_MAP * z
    Y = H / 2 - (P[:, 1] - LAT_C) * S_MAP * z
    v = np.zeros(len(P))
    for c, ta in arrive.items():
        if t < ta:
            continue
        cx, cy = proj(*CITIES[c][:2], z)
        r = 165 * z * e_out3(prog(t, ta, ta + 1.2)) + 1e-3
        v = np.maximum(v, np.clip(1.25 - np.hypot(X - cx, Y - cy) / r, 0, 1))
    vis = (X > -12) & (X < W + 12) & (Y > -12) & (Y < H + 12)
    L = ss_layer()
    d = ImageDraw.Draw(L)
    zz = z ** 0.7
    for x, y, vv in zip(X[vis] * 2, Y[vis] * 2, v[vis]):
        rr = (1.9 + 1.0 * vv) * zz * 2
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=rgba(mixc(DOT, ACCENT, vv), (0.42 + 0.5 * vv) * alpha))
    comp(buf, L.reduce(2))

    A = ss_layer()
    da = ImageDraw.Draw(A)
    for a, b, t0, dur in arcs:
        if t < t0:
            continue
        p = e_inout(prog(t, t0, t0 + dur))
        settle = prog(t, t0 + dur, t0 + dur + 0.6)
        pts = arc_points(a, b, z)
        m = max(2, int(len(pts) * p))
        seg = pts[:m] * 2
        for k in range(m - 1):
            moving = 0.25 + 0.75 * (k / max(1, m - 2))
            da.line([tuple(seg[k]), tuple(seg[k + 1])], fill=rgba(STEEL, lerp(moving, 0.28, settle) * alpha), width=3)
        if p < 1:
            hx, hy = seg[-1]
            da.ellipse((hx - 8, hy - 8, hx + 8, hy + 8), fill=rgba(WHITE, alpha))
    for c, ta in arrive.items():
        if t < ta:
            continue
        x, y = (v_ * 2 for v_ in proj(*CITIES[c][:2], z))
        q = prog(t, ta, ta + 0.85)
        if q < 1:
            r = (10 + 85 * e_out3(q)) * 2
            da.ellipse((x - r, y - r, x + r, y + r), outline=rgba(ACCENT, (1 - q) * alpha), width=5)
        r = 11
        da.ellipse((x - r, y - r, x + r, y + r), fill=rgba(ACCENT, alpha))
    A = A.reduce(2)
    comp(buf, A)
    glow(buf, A, 14, 0.6)


def latest_city(t):
    arrive, _ = outbreak()
    best = None
    for c, ta in arrive.items():
        if ta <= t and (best is None or ta > arrive[best]):
            best = c
    return best


# ------------------------------------------------------------------ opener
def ecg_y(x):
    u = x - W / 2
    return H / 2 - (18 * np.exp(-((u + 120) / 24) ** 2) - 26 * np.exp(-((u + 30) / 7) ** 2)
                    + 240 * np.exp(-(u / 9) ** 2) - 75 * np.exp(-((u - 26) / 9) ** 2)
                    + 46 * np.exp(-((u - 130) / 32) ** 2))


def draw_ecg(buf, t):
    fade = 1 - prog(t, 0.55, 0.9)
    if fade <= 0:
        return
    head = W * t / 0.6
    L = ss_layer()
    d = ImageDraw.Draw(L)
    xs = np.arange(0, min(head, W + 3), 3.0)
    if len(xs) < 2:
        return
    ys = ecg_y(xs)
    for k in range(len(xs) - 1):
        a = clamp01(1 - (head - xs[k]) / 1500) * fade
        d.line([(xs[k] * 2, ys[k] * 2), (xs[k + 1] * 2, ys[k + 1] * 2)], fill=rgba(ACCENT, a), width=6)
    if head < W:
        hy = ecg_y(np.array([head]))[0]
        d.ellipse((head * 2 - 12, hy * 2 - 12, head * 2 + 12, hy * 2 + 12), fill=rgba(WHITE, fade))
    L = L.reduce(2)
    comp(buf, L)
    glow(buf, L, 18, 0.9)


def corner_brackets(d, x0, y0, x1, y1, size, color, width):
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(cx, cy + sy * size), (cx, cy), (cx + sx * size, cy)], fill=color, width=width)


def draw_opener_hud(buf, t):
    a = e_out3(prog(t, 0.35, 0.8)) * (1 - prog(t, 2.6, 2.8))
    if a <= 0:
        return
    L = new_layer()
    d = ImageDraw.Draw(L)
    corner_brackets(d, 36, 36, W - 36, H - 36, 34, rgba(WHITE, 0.45 * a), 2)
    blink = 1.0 if (t * 3) % 1 < 0.6 else 0.25
    d.rectangle((64, 58, 76, 70), fill=rgba(ACCENT, a * blink))
    draw_text(L, "GLOBAL TRANSMISSION MAP", "mono", 20, WHITE, 90, 71, tracking=4, alpha=0.8 * a)
    cases = int(round(10 ** (6.5 * e_inout(prog(t, 0.55, 2.75)))))
    draw_text(L, f"{cases:,}".rjust(9), "mono", 26, ACCENT, W - 64, 73, align="r", alpha=a)
    draw_text(L, "CASES", "mono", 20, WHITE, W - 64 - text_w(f"{cases:,}".rjust(9), "mono", 26) - 16, 71,
              tracking=4, align="r", alpha=0.7 * a)
    c = latest_city(t)
    if c:
        draw_text(L, "LAST CONTACT:", "mono", 20, WHITE, 64, H - 58, tracking=3, alpha=0.7 * a)
        draw_text(L, CITIES[c][2], "mono", 20, ACCENT, 64 + text_w("LAST CONTACT:", "mono", 20, 3) + 14, H - 58,
                  tracking=3, alpha=a)
    draw_text(L, "STRAIN BT-26 // UNCONTAINED", "mono", 20, WHITE, W - 64, H - 58, tracking=3, align="r", alpha=0.7 * a)
    comp(buf, L)


def draw_card(buf, t, small, big_words, big_colors, t_in, t_out, size=128):
    if t < t_in or t > t_out + 0.12:
        return
    out = e_in3(prog(t, t_out, t_out + 0.12))
    alpha = 1 - out
    dy = -60 * out
    L = new_layer()
    n = len(small)
    k = int(round(n * prog(t, t_in, t_in + 0.22)))
    sw = text_w(small, "mono", 34, 10)
    draw_text(L, small[:k], "mono", 34, ACCENT, W / 2 - sw / 2, 452 + dy, tracking=10, alpha=alpha)
    bw = words_width(big_words, "black", size)
    T = new_layer()
    reveal_words(T, big_words, "black", size, big_colors, W / 2 - bw / 2, 600, t, t_in + 0.1, alpha=alpha)
    comp(buf, L)
    glow(buf, L, 10, 0.25)
    comp(buf, T, y=int(dy))
    glow(buf, T, 24, 0.1, y=int(dy))


def render_opener(buf, t):
    bg, vign, center_dim, glow_r, grain, grid = statics()
    buf[:] = bg
    map_a = e_out3(prog(t, 0.3, 0.9))
    draw_map(buf, t, map_a)
    txt = max(prog(t, 0.45, 0.7), 0) * (1 - prog(t, 2.75, 2.8))
    buf *= (1 - 0.7 * center_dim * txt)[..., None]
    draw_ecg(buf, t)
    draw_opener_hud(buf, t)
    draw_card(buf, t, "IN A WORLD WHERE", ["VIRUSES", "TRAVEL..."], [WHITE, WHITE], 0.5, 1.42)
    draw_card(buf, t, "ONE DOCTOR", ["TRAVELS", "FASTER."], [WHITE, ACCENT], 1.58, 2.9)


# ------------------------------------------------------------------ clip scene
PX0, PY0, PH = 250, 90, 900
PW = int(round(PH * 416 / 712))
COL_X = 880
HUD_LINES = [("CALLSIGN:", "BT", 3.70),
             ("FIELD OF OPS:", "WORLDWIDE", 4.50),
             ("TARGETS:", "VIRUSES, BACTERIA, PARASITES", 5.30),
             ("STATUS:", "ACTIVE", 6.10)]
TYPE_CPS = 1 / 0.018


@functools.lru_cache(maxsize=None)
def src_frames():
    files = sorted(glob.glob(os.path.join(ASSETS, "src", "f_*.png")))
    out = []
    for f in files:
        im = Image.open(f).convert("RGB")
        im = ImageEnhance.Contrast(im).enhance(1.15)
        im = ImageEnhance.Color(im).enhance(0.8)
        out.append(im)
    return out


def src_at(ts):
    fr = src_frames()
    return fr[max(0, min(len(fr) - 1, int(ts * SRC_FPS)))]


@functools.lru_cache(maxsize=8)
def round_mask(w, h, r):
    m = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), radius=r * 2, fill=255)
    return m.resize((w, h), Image.LANCZOS)


@functools.lru_cache(maxsize=None)
def panel_shadow():
    pad = 80
    sh = Image.new("RGBA", (PW + pad * 2, PH + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 18, pad + PW, pad + PH + 18), radius=8, fill=(0, 0, 0, 200))
    return sh.filter(ImageFilter.GaussianBlur(30)), pad


def draw_clip_bg(buf, t, img):
    bg, vign, center_dim, glow_r, grain, grid = statics()
    band = img.crop((0, 140, 416, 374))
    small = band.resize((96, 54), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2.5))
    big = np.asarray(small.resize((W, H), Image.BILINEAR), np.float32)
    lum = big.mean(axis=2, keepdims=True)
    buf[:] = bg * 0.9 + lum * 0.2 * np.array([0.82, 0.86, 0.92], np.float32)
    buf += (grid * 6.0)[..., None]


def draw_panel(buf, t, img):
    ts = t - T_DROP
    p_in = e_outexpo(prog(t, T_DROP, T_DROP + 0.5))
    s = lerp(1.25, 1.0, p_in)
    zoom = 1.0 + 0.07 * e_inout(clamp01(ts / 6.0))
    cw, ch = 416 / zoom, 712 / zoom
    cx, cy = 208, 330
    box = (cx - cw / 2, max(0, cy - ch / 2), cx + cw / 2, max(0, cy - ch / 2) + ch)
    pw, ph = int(PW * s), int(PH * s)
    fr = img.resize((pw, ph), Image.LANCZOS, box=box).filter(ImageFilter.UnsharpMask(2, 70, 2))
    arr = np.asarray(fr, np.float32).copy()
    arr[::3] *= 0.93
    fr = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
    fr.putalpha(round_mask(pw, ph, 6))
    px, py = int(PX0 + PW / 2 - pw / 2), int(PY0 + PH / 2 - ph / 2)
    sh, pad = panel_shadow()
    comp(buf, sh, p_in, PX0 - pad, PY0 - pad)
    comp(buf, fr, clamp01(prog(t, T_DROP, T_DROP + 0.12)), px, py)

    L = new_layer()
    d = ImageDraw.Draw(L)
    d.rounded_rectangle((px, py, px + pw, py + ph), radius=6, outline=rgba(WHITE, 0.8), width=2)
    corner_brackets(d, px - 18, py - 18, px + pw + 18, py + ph + 18, 36, rgba(ACCENT, 0.95), 4)
    comp(buf, L)
    glow(buf, L, 14, 0.25)

    O = new_layer()
    od = ImageDraw.Draw(O)
    a = clamp01(prog(t, T_DROP + 0.2, T_DROP + 0.5))
    od.rounded_rectangle((px + 16, py + 16, px + 120, py + 54), radius=8, fill=(0, 0, 0, int(120 * a)))
    if (ts * 2) % 1 < 0.62:
        od.ellipse((px + 28, py + 27, px + 44, py + 43), fill=rgba(RED, a))
    draw_text(O, "REC", "mono", 22, WHITE, px + 54, py + 43, tracking=2, alpha=a)
    fi = int(ts * FPS)
    tc = f"00:00:{fi // FPS:02d}:{fi % FPS:02d}"
    tcw = text_w(tc, "mono", 20, 1)
    od.rounded_rectangle((px + pw - tcw - 36, py + 16, px + pw - 16, py + 54), radius=8, fill=(0, 0, 0, int(120 * a)))
    draw_text(O, tc, "mono", 20, WHITE, px + pw - 26, py + 42, tracking=1, align="r", alpha=a)
    od.rounded_rectangle((px + 16, py + ph - 54, px + 236, py + ph - 16), radius=8, fill=(0, 0, 0, int(120 * a)))
    draw_text(O, "FIELD CAM // BT-01", "mono", 18, WHITE, px + 28, py + ph - 28, tracking=1, alpha=a)
    comp(buf, O)


def draw_column(buf, t):
    L = new_layer()
    d = ImageDraw.Draw(L)
    x0 = COL_X
    # tag pill
    a = e_out3(prog(t, 3.0, 3.2))
    if a > 0:
        tag = "SUBJECT IDENTIFIED"
        tw = text_w(tag, "mono", 22, 4)
        d.rounded_rectangle((x0, 268, x0 + tw + 56, 314), radius=3, outline=rgba(ACCENT, a), width=2)
        if (t * 3) % 1 < 0.6:
            d.ellipse((x0 + 17, 284, x0 + 31, 298), fill=rgba(ACCENT, a))
        k = int(round(len(tag) * prog(t, 3.0, 3.0 + len(tag) * 0.014)))
        draw_text(L, tag[:k], "mono", 22, ACCENT, x0 + 42, 299, tracking=4, alpha=a)
    # name
    size = 124
    while words_width(["DR.", "BILL", "TIMM"], "black", size) > 960:
        size -= 2
    reveal_words(L, ["DR.", "BILL", "TIMM"], "black", size, [WHITE] * 3, x0 - 4, 438, t, 3.12, stagger=0.08)
    # role
    p = e_out3(prog(t, 3.4, 3.8))
    draw_text(L, "INFECTIOUS DISEASE PHYSICIAN", "bold", 40, ACCENT, x0, 504, tracking=3, alpha=p, dx=-(1 - p) * 40)
    # separator
    p = e_inout(prog(t, 3.5, 4.0))
    if p > 0:
        d.line([(x0, 540), (x0 + 900 * p, 540)], fill=rgba(WHITE, 0.25), width=2)
        d.line([(x0, 540), (x0 + 140 * p, 540)], fill=rgba(ACCENT, 1), width=4)
    # typed HUD lines
    active = None
    for i, (key, val, ts0) in enumerate(HUD_LINES):
        if t < ts0:
            continue
        s = "> " + key + " " + val
        cols = tuple([ACCENT] * (len(key) + 3) + [WHITE] * len(val))
        k = min(len(s), int((t - ts0) * TYPE_CPS))
        y = 604 + i * 54
        draw_text(L, s[:k], "mono", 28, cols[:k] if k else ACCENT, x0, y, tracking=1)
        active = (x0 + text_w(s[:k], "mono", 28, 1) + 6, y)
    if active and (t * 2.5) % 1 < 0.55 and t < 7.0:
        d.rectangle((active[0], active[1] - 24, active[0] + 15, active[1] + 4), fill=rgba(ACCENT, 0.9))
    # virality meter
    a = e_out3(prog(t, 6.75, 7.0))
    if a > 0:
        p = e_inout(prog(t, 6.9, 8.35))
        crit = p >= 1
        flash = (t * 8) % 1 < 0.5
        label = "THREAT LEVEL: CRITICAL" if crit else "THREAT LEVEL"
        lc = WHITE if crit and flash else ACCENT
        draw_text(L, label, "mono", 22, lc, x0, 842, tracking=4, alpha=a)
        draw_text(L, f"{int(p * 100):3d}%", "mono", 24, WHITE, x0 + 900, 842, align="r", alpha=a)
        nseg, gap, bw = 25, 6, 900
        sw = (bw - gap * (nseg - 1)) / nseg
        filled = p * nseg
        for j in range(nseg):
            sx = x0 + j * (sw + gap)
            box = (sx, 860, sx + sw, 892)
            if j < int(filled):
                col = (WHITE if flash else ACCENT) if crit else mixc((255, 170, 40), ACCENT, j / nseg)
                d.rectangle(box, fill=rgba(col, a))
            elif j < filled:
                d.rectangle(box, fill=rgba(WHITE, a * 0.9))
            else:
                d.rectangle(box, outline=rgba(WHITE, 0.25 * a), width=2)
    comp(buf, L)
    glow(buf, L, 10, 0.1)


def render_clip(buf, t):
    img = src_at(t - T_DROP)
    draw_clip_bg(buf, t, img)
    draw_panel(buf, t, img)
    draw_column(buf, t)


# ------------------------------------------------------------------ logo scene
EM_CX, EM_CY, EM_R = W // 2, 338, 112


@functools.lru_cache(maxsize=None)
def logo_bg():
    bg, vign, center_dim, glow_r, grain, grid = statics()
    buf = bg.copy()
    L = ss_layer()
    d = ImageDraw.Draw(L)
    for lon, lat in dots():
        x, y = proj(lon, lat, 1.08)
        rr = 2.1 * 2
        d.ellipse((x * 2 - rr, y * 2 - rr, x * 2 + rr, y * 2 + rr), fill=rgba(DOT, 0.5))
    comp(buf, L.reduce(2))
    return buf


@functools.lru_cache(maxsize=None)
def burst():
    rng = np.random.default_rng(5)
    return [dict(ang=rng.uniform(0, 2 * math.pi), spd=rng.uniform(400, 1600), size=rng.uniform(1.2, 3.2),
                 col=ACCENT if rng.random() < 0.35 else STEEL, life=rng.uniform(0.5, 1.1))
            for _ in range(80)]


def draw_burst(buf, t):
    """Shockwave ring plus spark streaks flying out of the emblem."""
    dt = t - T_LOGO
    if dt < 0 or dt > 1.2:
        return
    L = new_layer()
    d = ImageDraw.Draw(L)
    q = prog(dt, 0, 0.6)
    if q < 1:
        r = 60 + 1150 * e_out3(q)
        d.ellipse((EM_CX - r, EM_CY - r, EM_CX + r, EM_CY + r), outline=rgba(WHITE, 0.6 * (1 - q)),
                  width=max(1, int(5 * (1 - q))))
    for p in burst():
        if dt > p["life"]:
            continue

        def pos(tt):
            dist = 40 + p["spd"] * (1 - math.exp(-3.2 * tt)) / 3.2
            return EM_CX + math.cos(p["ang"]) * dist, EM_CY + math.sin(p["ang"]) * dist

        a = (1 - dt / p["life"]) ** 1.5
        d.line([pos(max(0.0, dt - 0.05)), pos(dt)], fill=rgba(p["col"], a), width=max(1, int(p["size"])))
    comp(buf, L)
    glow(buf, L, 10, 0.4)


def draw_emblem(buf, t):
    """Targeting reticle locking onto a wireframe globe (drawn at 2x for anti-aliasing)."""
    a = e_out3(prog(t, T_LOGO, T_LOGO + 0.25))
    if a <= 0:
        return
    s = lerp(1.35, 1.0, e_outexpo(prog(t, T_LOGO, T_LOGO + 0.6)))
    box = 360
    E = Image.new("RGBA", (box * 4, box * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(E)
    c = box * 2
    R2 = EM_R * s * 2
    rot = (t - T_LOGO) * 40
    d.ellipse((c - R2, c - R2, c + R2, c + R2), fill=(9, 10, 12, 235))
    for lat in (-60, -30, 0, 30, 60):
        yy = c - R2 * math.sin(math.radians(lat))
        hw = R2 * math.cos(math.radians(lat))
        d.line([(c - hw, yy), (c + hw, yy)], fill=rgba(WHITE, 0.3), width=3)
    for k in range(6):
        hw = R2 * abs(math.cos(math.radians(rot + k * 30)))
        if hw < 3:
            d.line([(c, c - R2), (c, c + R2)], fill=rgba(WHITE, 0.3), width=3)
        else:
            d.ellipse((c - hw, c - R2, c + hw, c + R2), outline=rgba(WHITE, 0.3), width=3)
    d.ellipse((c - R2, c - R2, c + R2, c + R2), outline=rgba(WHITE, 0.95), width=8)
    # four red arcs sweep around the globe like a lock-on
    Ro = R2 + 60 * s
    sweep = e_inout(prog(t, T_LOGO + 0.05, T_LOGO + 0.45))
    if sweep > 0:
        for k in range(4):
            st = k * 90 + 12
            d.arc((c - Ro, c - Ro, c + Ro, c + Ro), st, st + 66 * sweep, fill=rgba(ACCENT, 1), width=8)
    # slowly rotating tick ring
    Rt = Ro + 30 * s
    for k in range(72):
        ang = math.radians(k * 5 + rot * 0.25)
        ln = (22 if k % 6 == 0 else 10) * s
        d.line([(c + math.cos(ang) * Rt, c + math.sin(ang) * Rt),
                (c + math.cos(ang) * (Rt + ln), c + math.sin(ang) * (Rt + ln))], fill=rgba(WHITE, 0.4), width=3)
    # crosshair arms slide in from outside
    ci = e_outexpo(prog(t, T_LOGO + 0.1, T_LOGO + 0.55))
    if ci > 0:
        off = (1 - ci) * 160
        for k in range(4):
            ang = math.radians(k * 90)
            r0, r1 = R2 + 18 * s + off, Rt + 70 * s + off
            d.line([(c + math.cos(ang) * r0, c + math.sin(ang) * r0),
                    (c + math.cos(ang) * r1, c + math.sin(ang) * r1)], fill=rgba(ACCENT, ci), width=8)
    lock = prog(t, T_LOGO + 0.45, T_LOGO + 0.5)
    if lock > 0:
        r = 10 * s
        blink = 1.0 if (t * 2) % 1 < 0.7 else 0.35
        d.ellipse((c - r, c - r, c + r, c + r), fill=rgba(ACCENT, lock * blink))
    L = new_layer()
    safe_ac(L, scale_alpha(E.reduce(2), a), EM_CX - box, EM_CY - box)
    comp(buf, L)
    glow(buf, L, 18, 0.3)


def draw_subscribe(buf, t):
    a = clamp01(prog(t, T_SUB - 0.15, T_SUB))
    if a <= 0:
        return
    p = e_outexpo(prog(t, T_SUB - 0.15, T_SUB + 0.3))
    bw, bh = 300, 70
    S = Image.new("RGBA", (bw * 2, bh * 2), (0, 0, 0, 0))
    ImageDraw.Draw(S).rounded_rectangle((0, 0, bw * 2 - 1, bh * 2 - 1), radius=10, fill=rgba(YT_RED))
    S = S.reduce(2)
    draw_text(S, "SUBSCRIBE", "xbold", 30, WHITE, bw / 2, bh / 2 + 11, tracking=5, align="c")
    L = new_layer()
    safe_ac(L, scale_alpha(S, a), int(W / 2 - bw / 2), int(905 - bh / 2 + (1 - p) * 50))
    comp(buf, L)


def render_logo(buf, t):
    bg, vign, center_dim, glow_r, grain, grid = statics()
    buf[:] = logo_bg()
    pulse = 0.5 + 0.5 * math.exp(-(t - T_LOGO) * 2.2)
    buf += (glow_r * 26 * pulse)[..., None] * np.array([1.0, 0.16, 0.14], np.float32)
    draw_burst(buf, t)
    draw_emblem(buf, t)
    T = new_layer()
    words = ["BT", "GOES", "VIRAL"]
    size = 150
    tw = words_width(words, "black", size)
    reveal_words(T, words, "black", size, [WHITE, WHITE, ACCENT], W / 2 - tw / 2, 700, t, 9.0, stagger=0.09, dur=0.55)
    comp(buf, T)
    glow(buf, T, 22, 0.12)
    a = prog(t, 9.4, 9.85)
    if a > 0:
        tr = round(lerp(18, 6, e_out3(prog(t, 9.4, 10.15))) * 2) / 2
        tag = "DR. BILL TIMM  \u2022  INFECTIOUS DISEASE  \u2022  WORLD TRAVEL"
        cols = tuple(ACCENT if ch == "\u2022" else WHITE for ch in tag)
        G = new_layer()
        draw_text(G, tag, "semi", 30, cols, W / 2, 792, tracking=tr, align="c", alpha=a * 0.92)
        comp(buf, G)
    draw_subscribe(buf, t)


# ------------------------------------------------------------------ post FX
def pulse_env(t, t0, rise, fall):
    if t < t0 - rise or t > t0 + fall:
        return 0.0
    if t < t0:
        return e_in3(prog(t, t0 - rise, t0))
    return 1 - e_out3(prog(t, t0, t0 + fall))


def fx_amounts(t):
    chroma = max(10 * pulse_env(t, T_DROP, 0.3, 0.35), 12 * pulse_env(t, T_LOGO, 0.3, 0.35),
                 6 * pulse_env(t, 1.5, 0.06, 0.1), 3 * pulse_env(t, T_SUB, 0.01, 0.2))
    glitch = max(pulse_env(t, T_DROP, 0.08, 0.28), pulse_env(t, T_LOGO, 0.25, 0.22), 0.45 * pulse_env(t, 1.5, 0.05, 0.08))
    for g0 in (10.46,):
        if g0 <= t < g0 + 0.07:
            glitch = max(glitch, 0.35)
    shake = 0.0
    if t >= T_DROP:
        shake = max(shake, 16 * math.exp(-(t - T_DROP) * 8))
    if t >= T_LOGO:
        shake = max(shake, 18 * math.exp(-(t - T_LOGO) * 7))
    shake = max(shake, 4 * prog(t, 2.45, 2.8) if t < T_DROP else 0)
    flash = max(pulse_env(t, T_DROP, 0.02, 0.24), 0.9 * pulse_env(t, T_LOGO, 0.02, 0.28), 0.12 * pulse_env(t, T_SUB, 0.01, 0.12))
    return chroma, glitch, shake, flash


def post(buf, t, i):
    bg, vign, center_dim, glow_r, grain, grid = statics()
    rng = np.random.default_rng(1000 + i)
    chroma, glitch, shake, flash = fx_amounts(t)
    if glitch > 0.02:
        for _ in range(int(4 + 10 * glitch)):
            y0 = int(rng.integers(0, H - 10))
            h = int(rng.integers(6, 30 + int(90 * glitch)))
            sh = int(rng.normal(0, 140 * glitch))
            buf[y0:y0 + h] = np.roll(buf[y0:y0 + h], sh, axis=1)
            if rng.random() < 0.35:
                buf[y0:y0 + h, :, 1] *= 0.6
    k = int(round(chroma))
    if k >= 1:
        buf[..., 0] = np.roll(buf[..., 0], -k, axis=1)
        buf[..., 2] = np.roll(buf[..., 2], k, axis=1)
    if shake >= 0.5:
        sx, sy = int(rng.normal(0, shake)), int(rng.normal(0, shake * 0.7))
        m = int(abs(sx)) + int(abs(sy)) + 2
        padded = np.pad(buf, ((m, m), (m, m), (0, 0)), mode="edge")
        buf[:] = padded[m + sy:m + sy + H, m + sx:m + sx + W]
    if flash > 0:
        buf += (255 - buf) * flash
    buf *= vign[..., None]
    buf += grain[i % len(grain)][..., None]
    fade = e_in3(prog(t, T_END - 0.5, T_END))
    fade_in = 1 - prog(t, 0.0, 0.12)
    if fade > 0 or fade_in > 0:
        buf *= 1 - max(fade, fade_in)
    return np.clip(buf, 0, 255).astype(np.uint8)


def render_frame(i):
    t = i / FPS
    buf = np.zeros((H, W, 3), np.float32)
    if t < T_DROP:
        render_opener(buf, t)
    elif t < T_LOGO:
        render_clip(buf, t)
    else:
        render_logo(buf, t)
    return post(buf, t, i)


def main():
    mode = sys.argv[2]
    if mode == "preview":
        out = sys.argv[3]
        os.makedirs(out, exist_ok=True)
        for ts in sys.argv[4:]:
            i = int(round(float(ts) * FPS))
            Image.fromarray(render_frame(i)).save(os.path.join(out, f"t{float(ts):05.2f}.png"))
            print("frame", ts, flush=True)
    elif mode == "video":
        from multiprocessing import Pool
        sink = sys.stdout.buffer
        with Pool(4) as pool:
            for k, fr in enumerate(pool.imap(render_frame, range(NF), chunksize=2)):
                sink.write(fr.tobytes())
                if k % 30 == 0:
                    print(f"frame {k}/{NF}", file=sys.stderr, flush=True)
        sink.flush()


if __name__ == "__main__":
    main()
