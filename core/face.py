import time
import math
import random
import threading
import datetime
import numpy
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7735

W, H = 160, 128
SS = 2
BG = (8, 14, 36)
CY = 64
EYE_L = 40
EYE_R = 120

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

_disp = None
_img = None
_hi_img = None
_hi_draw = None
_font_big = None
_font_small = None
_font_mid = None
_font_tiny = None

current_face = "neutral"
_running = False
_speaking = False
_overlay_until = 0.0
_overlay_lines = []
_overlay_kind = "text"
_overlay_data = {}

EXPR = {
    "neutral":  {"w": 60, "h": 62, "color": (80, 220, 235), "lid": None},
    "happy":    {"w": 60, "h": 36, "color": (90, 230, 150), "lid": None},
    "sad":      {"w": 58, "h": 50, "color": (120, 170, 230), "lid": "sad"},
    "annoyed":  {"w": 62, "h": 24, "color": (235, 100, 60), "lid": "angry"},
    "confused": {"w": 54, "h": 46, "color": (100, 210, 230), "lid": None,
                 "r_dw": 0, "r_dh": -16, "r_lid": "sad"},
    "sleepy":   {"w": 60, "h": 14, "color": (150, 180, 220), "lid": None},
    "excited":  {"w": 68, "h": 70, "color": (255, 210, 60), "lid": None},
    "curious":  {"w": 60, "h": 62, "color": (110, 220, 235), "lid": None,
                 "r_dw": 8, "r_dh": 4},
    "smug":     {"w": 58, "h": 44, "color": (130, 220, 200), "lid": None,
                 "r_dw": 0, "r_dh": -20, "r_lid": "heavy"},
    "surprised": {"w": 72, "h": 74, "color": (235, 220, 255), "lid": None},
    "playful":  {"w": 62, "h": 58, "color": (140, 230, 190), "lid": None,
                 "r_dw": 4, "r_dh": -30, "r_lid": "heavy"},
    "bored":    {"w": 60, "h": 20, "color": (140, 160, 190), "lid": "heavy"},
    "shy":      {"w": 50, "h": 44, "color": (230, 170, 200), "lid": "sad",
                 "r_dw": -2, "r_dh": -2, "r_lid": "sad"},
    "dreamy":   {"w": 56, "h": 30, "color": (180, 190, 255), "lid": None},
    "alert":    {"w": 66, "h": 66, "color": (150, 235, 235), "lid": None},
    "determined": {"w": 56, "h": 40, "color": (255, 140, 60), "lid": "angry", "r_lid": "angry"},
    "sneaky":   {"w": 60, "h": 56, "color": (160, 120, 220), "lid": None,
                 "r_dw": -30, "r_dh": -50, "r_lid": "heavy"},
    "proud":    {"w": 66, "h": 58, "color": (255, 190, 90), "lid": "heavy"},
    "worried":  {"w": 50, "h": 54, "color": (140, 180, 255), "lid": "sad", "r_lid": "sad"},
    "silly":    {"w": 64, "h": 30, "color": (255, 150, 200), "lid": None,
                 "r_dw": 10, "r_dh": 26},
    "posing":   {"w": 66, "h": 66, "color": (70, 160, 255), "lid": None},
    "sleeping": {"w": 40, "h": 14, "color": (130, 155, 220), "lid": None},
}

ENERGY = {
    "excited": 1.0, "annoyed": 0.8, "surprised": 0.9, "alert": 0.85,
    "happy": 0.5, "curious": 0.5, "playful": 0.6, "determined": 0.75,
    "sneaky": 0.5, "proud": 0.55, "silly": 0.6,
    "neutral": 0.3, "confused": 0.4, "smug": 0.3, "bored": 0.2,
    "shy": 0.25, "sad": 0.15, "dreamy": 0.15, "sleepy": 0.05, "worried": 0.35, "posing": 0.4,
    "sleeping": 0.02,
}

SLEEP_EYE_COLOR = (140, 165, 225)
ZZZ_COLOR = (190, 210, 255)
ZZZ_CYCLE = 2.4
ZZZ_COUNT = 3

SWEAT_COLOR = (120, 200, 255)
SWEAT_CYCLE = 1.6

ANGER_COLOR = (255, 90, 70)

cur = {"w": 60.0, "h": 62.0, "r": 80.0, "g": 220.0, "b": 235.0,
       "r_dw": 0.0, "r_dh": 0.0, "ox": 0.0, "oy": 0.0}
tgt = dict(cur)
lid_L = None
lid_R = None
blink_amt = 0.0
_settle_until = 0.0


def init():
    global _disp, _font_big, _font_small, _font_mid, _font_tiny
    cs_pin = digitalio.DigitalInOut(board.CE0)
    dc_pin = digitalio.DigitalInOut(board.D25)
    reset_pin = digitalio.DigitalInOut(board.D24)
    spi = board.SPI()
    _disp = st7735.ST7735R(
        spi,
        cs=cs_pin,
        dc=dc_pin,
        rst=reset_pin,
        baudrate=16000000,
        width=128,
        height=160,
        x_offset=2,
        y_offset=1,
        bgr=True,
    )
    try:
        _font_big = ImageFont.truetype(FONT_PATH, 26)
        _font_small = ImageFont.truetype(FONT_PATH, 15)
        _font_mid = ImageFont.truetype(FONT_PATH, 20)
        _font_tiny = ImageFont.truetype(FONT_PATH, 12)
    except Exception:
        _font_big = ImageFont.load_default()
        _font_small = _font_big
        _font_mid = _font_big
        _font_tiny = _font_big
    return _disp


def _cut_corner(draw, box, corner, depth_frac=0.5, pad=0):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    ext_x = w * depth_frac + pad
    ext_y = h * depth_frac + pad
    if corner == "tl":
        pts = [(x0 - pad, y0 - pad), (x0 + ext_x, y0 - pad), (x0 - pad, y0 + ext_y)]
    elif corner == "tr":
        pts = [(x1 + pad, y0 - pad), (x1 - ext_x, y0 - pad), (x1 + pad, y0 + ext_y)]
    draw.polygon(pts, fill=BG)


def _lid_top(draw, box, frac):
    x0, y0, x1, y1 = box
    draw.rectangle([x0, y0, x1, y0 + (y1 - y0) * frac], fill=BG)


def _draw_eye(draw, cx, cy, w, h, color, lid, left):
    cx, cy, w, h = cx * SS, cy * SS, w * SS, h * SS
    h = max(3 * SS, h)
    w = max(6 * SS, w)
    box = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
    radius = min(w, h) * 0.28
    draw.rounded_rectangle(box, radius=radius, fill=color)
    if lid == "sad":
        _cut_corner(draw, box, "tl" if left else "tr", pad=radius * 0.6)
    elif lid == "angry":
        _cut_corner(draw, box, "tr" if left else "tl", pad=radius * 0.6)
    elif lid == "heavy":
        _lid_top(draw, box, 0.45)


def _draw_sweat(draw):
    phase = (time.time() % SWEAT_CYCLE) / SWEAT_CYCLE
    size = (5 + 3 * math.sin(phase * math.pi)) * SS
    x = (EYE_R + 30 + cur["ox"]) * SS
    y = (CY - 36 + cur["oy"] + phase * 30) * SS
    draw.ellipse([x - size / 2, y - size, x + size / 2, y + size], fill=SWEAT_COLOR)


def _draw_anger_mark(draw):
    jitter = random.uniform(-1, 1)
    x = (EYE_R + 22 + cur["ox"] + jitter) * SS
    y = (CY - 40 + cur["oy"]) * SS
    s = 9 * SS
    pts = [
        (x, y),
        (x + s * 0.5, y + s * 0.6),
        (x + s * 0.15, y + s * 0.6),
        (x + s * 0.6, y + s * 1.2),
    ]
    draw.line(pts, fill=ANGER_COLOR, width=max(2, int(2 * SS)), joint="curve")


def _draw_sleep_face(draw):
    breathe = 1.0 + 0.08 * math.sin(time.time() * 1.1)
    r = 20 * breathe * SS
    for base_cx in (EYE_L + cur["ox"], EYE_R + cur["ox"]):
        cx = base_cx * SS
        cy = (CY + cur["oy"]) * SS
        box = [cx - r, cy - r, cx + r, cy + r]
        draw.arc(box, start=20, end=160, fill=SLEEP_EYE_COLOR, width=5 * SS)


def _draw_zzz(draw):
    now = time.time()
    origin_x = EYE_R + 16 + cur["ox"]
    origin_y = CY - 28 + cur["oy"]
    step = ZZZ_CYCLE / ZZZ_COUNT
    for i in range(ZZZ_COUNT):
        phase = ((now + i * step) % ZZZ_CYCLE) / ZZZ_CYCLE
        alpha = math.sin(phase * math.pi)
        if alpha <= 0.03:
            continue
        x = origin_x + phase * 28
        y = origin_y - phase * 36
        if phase < 0.35:
            font = _font_tiny
        elif phase < 0.7:
            font = _font_mid
        else:
            font = _font_big
        color = tuple(int(BG[c] + (ZZZ_COLOR[c] - BG[c]) * alpha) for c in range(3))
        draw.text((x, y), "Z", font=font, fill=color)


def _frame():
    global _img, _hi_img, _hi_draw
    if _hi_img is None:
        _hi_img = Image.new("RGB", (W * SS, H * SS), BG)
        _hi_draw = ImageDraw.Draw(_hi_img)
        _img = Image.new("RGB", (W, H), BG)

    if time.time() < _overlay_until:
        if _overlay_kind == "time":
            _push_frame(_draw_time_overlay())
        elif _overlay_kind == "weather":
            _push_frame(_draw_weather_overlay())
        else:
            draw = ImageDraw.Draw(_img)
            draw.rectangle([0, 0, W, H], fill=BG)
            _draw_overlay(draw)
            _push_frame(_img)
        return

    _hi_draw.rectangle([0, 0, W * SS, H * SS], fill=BG)

    if current_face == "sleeping":
        _draw_sleep_face(_hi_draw)
        small = _hi_img.reduce(SS)
        _draw_zzz(ImageDraw.Draw(small))
        _push_frame(small)
        return

    color = (int(cur["r"]), int(cur["g"]), int(cur["b"]))
    h_l = cur["h"] * (1 - blink_amt)
    h_r = (cur["h"] + cur["r_dh"]) * (1 - blink_amt)
    w_r = cur["w"] + cur["r_dw"]

    _draw_eye(_hi_draw, EYE_L + cur["ox"], CY + cur["oy"], cur["w"], h_l, color, lid_L, True)
    _draw_eye(_hi_draw, EYE_R + cur["ox"], CY + cur["oy"], w_r, h_r, color, lid_R, False)

    if current_face in ("worried", "shy"):
        _draw_sweat(_hi_draw)
    elif current_face in ("annoyed", "determined"):
        _draw_anger_mark(_hi_draw)

    small = _hi_img.reduce(SS)
    _push_frame(small)


def _draw_overlay(draw):
    fonts = [_font_big] + [_font_small] * max(0, len(_overlay_lines) - 1)
    heights = []
    for line, font in zip(_overlay_lines, fonts):
        bbox = draw.textbbox((0, 0), line, font=font)
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + 6 * (len(_overlay_lines) - 1)
    y = CY - total_h / 2
    for line, font, h in zip(_overlay_lines, fonts, heights):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (W - w) / 2
        draw.text((x, y), line, font=font, fill=(90, 210, 255))
        y += h + 6


def show_overlay(lines, duration=5.0, kind="text", data=None):
    global _overlay_lines, _overlay_until, _overlay_kind, _overlay_data
    _overlay_lines = lines
    _overlay_until = time.time() + duration
    _overlay_kind = kind
    _overlay_data = data or {}


def _draw_time_overlay():
    _hi_draw.rectangle([0, 0, W * SS, H * SS], fill=BG)
    now = datetime.datetime.now()
    cx, cy, r = 60 * SS, 56 * SS, 34 * SS

    _hi_draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(90, 210, 255), width=int(3 * SS))
    for i in range(12):
        ang = math.radians(i * 30 - 90)
        x0 = cx + math.cos(ang) * (r - 6 * SS)
        y0 = cy + math.sin(ang) * (r - 6 * SS)
        x1 = cx + math.cos(ang) * r
        y1 = cy + math.sin(ang) * r
        _hi_draw.line([x0, y0, x1, y1], fill=(90, 210, 255), width=int(SS))

    hour_ang = math.radians((now.hour % 12 + now.minute / 60) * 30 - 90)
    min_ang = math.radians(now.minute * 6 - 90)
    sec_ang = math.radians(now.second * 6 - 90)
    _hi_draw.line([cx, cy, cx + math.cos(hour_ang) * r * 0.5, cy + math.sin(hour_ang) * r * 0.5],
                  fill=(255, 255, 255), width=int(3 * SS))
    _hi_draw.line([cx, cy, cx + math.cos(min_ang) * r * 0.75, cy + math.sin(min_ang) * r * 0.75],
                  fill=(255, 255, 255), width=int(2 * SS))
    _hi_draw.line([cx, cy, cx + math.cos(sec_ang) * r * 0.85, cy + math.sin(sec_ang) * r * 0.85],
                  fill=(255, 120, 120), width=int(SS))
    _hi_draw.ellipse([cx - 3 * SS, cy - 3 * SS, cx + 3 * SS, cy + 3 * SS], fill=(255, 255, 255))

    small = _hi_img.reduce(SS)
    draw = ImageDraw.Draw(small)
    time_str = now.strftime("%I:%M %p").lstrip("0")
    bbox = draw.textbbox((0, 0), time_str, font=_font_mid)
    w = bbox[2] - bbox[0]
    draw.text(((W - w) / 2, 102), time_str, font=_font_mid, fill=(200, 230, 255))
    return small


def _draw_sun_icon(draw, cx, cy, r):
    now = time.time()
    draw.ellipse([cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55], fill=(255, 210, 90))
    for i in range(8):
        ang = math.radians(i * 45) + now * 0.6
        x0 = cx + math.cos(ang) * r * 0.68
        y0 = cy + math.sin(ang) * r * 0.68
        x1 = cx + math.cos(ang) * r
        y1 = cy + math.sin(ang) * r
        draw.line([x0, y0, x1, y1], fill=(255, 210, 90), width=max(1, int(2 * SS)))


def _draw_cloud_icon(draw, cx, cy, r):
    drift = math.sin(time.time() * 0.8) * r * 0.08
    cx += drift
    draw.ellipse([cx - r * 0.55, cy - r * 0.15, cx + r * 0.05, cy + r * 0.45], fill=(210, 220, 235))
    draw.ellipse([cx - r * 0.15, cy - r * 0.4, cx + r * 0.45, cy + r * 0.35], fill=(225, 232, 245))
    draw.ellipse([cx + r * 0.15, cy - r * 0.1, cx + r * 0.7, cy + r * 0.45], fill=(210, 220, 235))


def _draw_rain_icon(draw, cx, cy, r):
    _draw_cloud_icon(draw, cx, cy - r * 0.2, r * 0.85)
    now = time.time()
    for i in range(4):
        phase = (now * 2 + i * 0.5) % 1.0
        x = cx - r * 0.4 + i * (r * 0.27)
        y0 = cy + r * 0.2 + phase * r * 0.6
        draw.line([x, y0, x - r * 0.06, y0 + r * 0.18], fill=(120, 180, 255), width=max(1, int(2 * SS)))


def _draw_snow_icon(draw, cx, cy, r):
    _draw_cloud_icon(draw, cx, cy - r * 0.2, r * 0.85)
    now = time.time()
    for i in range(4):
        phase = (now * 0.8 + i * 0.5) % 1.0
        x = cx - r * 0.4 + i * (r * 0.27) + math.sin(now * 2 + i) * 3
        y0 = cy + r * 0.2 + phase * r * 0.6
        draw.ellipse([x - 2, y0 - 2, x + 2, y0 + 2], fill=(230, 240, 255))


def _draw_storm_icon(draw, cx, cy, r):
    _draw_cloud_icon(draw, cx, cy - r * 0.2, r * 0.85)
    flash = math.sin(time.time() * 6) > 0.7
    color = (255, 235, 120) if flash else (200, 190, 90)
    pts = [(cx - 4, cy + r * 0.15), (cx + 6, cy + r * 0.15), (cx - 2, cy + r * 0.5),
           (cx + 8, cy + r * 0.5), (cx - 6, cy + r * 0.95)]
    draw.line(pts, fill=color, width=max(1, int(2 * SS)))


WEATHER_ICON_DRAW = {
    "sun": _draw_sun_icon,
    "cloud": _draw_cloud_icon,
    "rain": _draw_rain_icon,
    "snow": _draw_snow_icon,
    "storm": _draw_storm_icon,
}


def _draw_weather_overlay():
    _hi_draw.rectangle([0, 0, W * SS, H * SS], fill=BG)
    kind = _overlay_data.get("icon", "cloud")
    fn = WEATHER_ICON_DRAW.get(kind, _draw_cloud_icon)
    cx, cy, r = (W / 2) * SS, (H / 2 - 14) * SS, 30 * SS
    fn(_hi_draw, cx, cy, r)

    small = _hi_img.reduce(SS)
    draw = ImageDraw.Draw(small)
    lines = _overlay_lines[1:] if len(_overlay_lines) > 1 else _overlay_lines
    y = 100
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=_font_small)
        w = bbox[2] - bbox[0]
        draw.text(((W - w) / 2, y), line, font=_font_small, fill=(200, 225, 255))
        y += 18
    return small


def _push_frame(img):
    try:
        rotated = img.rotate(270, expand=True)
        data = numpy.array(rotated.convert("RGB")).astype(numpy.uint16)
        color = ((data[:, :, 0] & 0xF8) << 8) | ((data[:, :, 1] & 0xFC) << 3) | (data[:, :, 2] >> 3)
        hi = (color >> 8).astype(numpy.uint8)
        lo = (color & 0xFF).astype(numpy.uint8)
        pixels = numpy.dstack((hi, lo)).tobytes()
        w, h = rotated.size
        _disp._block(0, 0, w - 1, h - 1, pixels)
    except Exception:
        _disp.image(img, rotation=270)


def set_current(name):
    global current_face, lid_L, lid_R, tgt, _settle_until
    if name not in EXPR:
        return
    prev = current_face
    current_face = name
    spec = EXPR[name]
    tgt = {
        "w": spec["w"], "h": spec["h"],
        "r": spec["color"][0], "g": spec["color"][1], "b": spec["color"][2],
        "r_dw": spec.get("r_dw", 0), "r_dh": spec.get("r_dh", 0),
        "ox": 0.0, "oy": 0.0,
    }
    lid_L = spec.get("lid")
    lid_R = spec.get("r_lid", spec.get("lid"))
    if ENERGY.get(prev, 0.3) > 0.7 and ENERGY.get(name, 0.3) < 0.5:
        _settle_until = time.time() + random.uniform(3.0, 5.0)
    if name == "confused" and prev != "confused":
        confused_wiggle()
    elif name == "silly" and prev != "silly":
        laugh()


def _do_blink(kind):
    global blink_amt
    if current_face in ("sleepy", "sleeping"):
        return
    if kind == "quick":
        steps = [(0.0, 0.02), (1.0, 0.03), (0.0, 0.04)]
    elif kind == "slow":
        steps = [(0.0, 0.03), (0.5, 0.05), (1.0, 0.09), (0.5, 0.05), (0.0, 0.07)]
    else:
        steps = [(0.0, 0.02), (1.0, 0.03), (0.1, 0.04), (1.0, 0.03), (0.0, 0.05)]
    for amt, dur in steps:
        blink_amt = amt
        time.sleep(dur)
    blink_amt = 0.0


IDLE_BLUE = (70, 160, 255)
IDLE_COLOR_CHOICES = [IDLE_BLUE]

IDLE_SHAPES = [
    {"w": 66, "h": 66},
    {"w": 62, "h": 64},
    {"w": 64, "h": 60},
    {"w": 66, "h": 62},
]


def _animate_loop():
    global cur, _running, lid_L, lid_R
    _running = True
    last_blink = time.time()
    next_blink_gap = random.uniform(2.0, 4.5)
    last_wander = time.time()
    next_wander_gap = random.uniform(1.8, 3.5)
    last_micro = time.time()
    next_micro_gap = random.uniform(3.0, 6.0)
    last_mood = time.time()
    next_mood_gap = random.uniform(6.0, 11.0)
    last_color = time.time()
    next_color_gap = random.uniform(25.0, 45.0)
    was_speaking = False

    while True:
        try:
            if _speaking:
                was_speaking = True
                time.sleep(0.1)
                last_blink = time.time()
                last_wander = time.time()
                last_mood = time.time()
                continue

            if was_speaking:
                was_speaking = False
                set_current("posing")
                last_color = time.time()
                next_color_gap = random.uniform(25.0, 45.0)

            now = time.time()
            settling = now < _settle_until
            ease = 0.22 if not settling else 0.12

            for k in ("w", "h", "r", "g", "b", "r_dw", "r_dh", "ox", "oy"):
                cur[k] += (tgt[k] - cur[k]) * ease

            _frame()

            if now - last_blink > next_blink_gap:
                last_blink = now
                roll = random.random()
                kind = "quick" if roll < 0.55 else ("slow" if roll < 0.85 else "double")
                _do_blink(kind)
                next_blink_gap = random.uniform(2.0, 5.5)

            if now - last_wander > next_wander_gap:
                last_wander = now
                amp = 10 if not settling else 5
                new_ox = random.uniform(-amp, amp)
                new_oy = random.uniform(-amp * 0.9, amp * 0.9)
                base_w = tgt["w"]
                base_r_dw = tgt["r_dw"]
                tgt["ox"] = new_ox
                tgt["oy"] = new_oy
                if abs(new_ox) > amp * 0.65 and current_face != "sleeping":
                    boost = 6
                    if new_ox > 0:
                        tgt["r_dw"] = base_r_dw + boost
                    else:
                        tgt["w"] = base_w + boost
                next_wander_gap = random.uniform(1.8, 4.0)

                def _wander_reset(bw=base_w, brdw=base_r_dw):
                    tgt.update(ox=0.0, oy=0.0, w=bw, r_dw=brdw)

                threading.Timer(random.uniform(0.8, 1.6), _wander_reset).start()

            if now - last_micro > next_micro_gap:
                last_micro = now
                base_h = tgt["h"]
                jitter = random.uniform(-4, 4)
                tgt["h"] = base_h + jitter
                next_micro_gap = random.uniform(3.5, 7.0)
                threading.Timer(random.uniform(1.0, 2.0), lambda: tgt.update(h=base_h)).start()

            if now - last_mood > next_mood_gap:
                last_mood = now
                shape = random.choice(IDLE_SHAPES)
                tgt["w"] = shape["w"]
                tgt["h"] = shape["h"]
                tgt["r_dw"] = shape.get("r_dw", 0)
                tgt["r_dh"] = shape.get("r_dh", 0)
                lid_L = shape.get("lid")
                lid_R = shape.get("r_lid", shape.get("lid"))
                next_mood_gap = random.uniform(6.0, 12.0)

            if now - last_color > next_color_gap:
                last_color = now
                tgt["r"], tgt["g"], tgt["b"] = random.choice(IDLE_COLOR_CHOICES)
                next_color_gap = random.uniform(25.0, 45.0)

            time.sleep(0.02)
        except Exception:
            time.sleep(0.05)


def start_idle():
    global _running
    if _running:
        return
    set_current(current_face)
    for k in ("w", "h", "r", "g", "b", "r_dw", "r_dh", "ox", "oy"):
        cur[k] = tgt[k]
    t = threading.Thread(target=_animate_loop, daemon=True)
    t.start()


def start_talking():
    global _speaking
    _speaking = True


def stop_talking():
    global _speaking
    _speaking = False


PARTY_COLORS = [
    (255, 80, 80), (255, 210, 60), (90, 230, 150),
    (120, 170, 255), (230, 130, 190), (180, 90, 255),
]


def party_flash(duration=2.5):
    def _run():
        end = time.time() + duration
        i = 0
        while time.time() < end:
            r, g, b = PARTY_COLORS[i % len(PARTY_COLORS)]
            cur["r"], cur["g"], cur["b"] = r, g, b
            tgt["r"], tgt["g"], tgt["b"] = r, g, b
            i += 1
            time.sleep(0.09)
        tgt["r"], tgt["g"], tgt["b"] = IDLE_BLUE

    threading.Thread(target=_run, daemon=True).start()


def laugh():
    def _run():
        end = time.time() + 0.5
        base_oy = tgt["oy"]
        while time.time() < end:
            tgt["oy"] = base_oy + random.uniform(-5, 5)
            time.sleep(0.04)
        tgt["oy"] = base_oy

    threading.Thread(target=_run, daemon=True).start()


def confused_wiggle():
    def _run():
        end = time.time() + 0.5
        base_ox = tgt["ox"]
        while time.time() < end:
            tgt["ox"] = base_ox + random.uniform(-20, 20)
            time.sleep(0.04)
        tgt["ox"] = base_ox

    threading.Thread(target=_run, daemon=True).start()


if __name__ == "__main__":
    init()
    start_idle()
    for name in EXPR:
        print(name)
        set_current(name)
        time.sleep(3.0)
    set_current("neutral")
    time.sleep(3.0)
