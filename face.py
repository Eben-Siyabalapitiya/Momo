import time
import random
import threading
import board
import digitalio
from PIL import Image, ImageDraw
from adafruit_rgb_display import st7735

W, H = 160, 128
BG = (8, 14, 36)
CY = 64
EYE_L = 40
EYE_R = 120

_disp = None
_img = None
_draw = None

current_face = "neutral"
_running = False
_speaking = False

EXPR = {
    "neutral":  {"w": 60, "h": 62, "color": (80, 220, 235), "lid": None},
    "happy":    {"w": 60, "h": 36, "color": (90, 230, 150), "lid": None},
    "sad":      {"w": 58, "h": 50, "color": (120, 170, 230), "lid": "sad"},
    "annoyed":  {"w": 62, "h": 24, "color": (235, 100, 60), "lid": "angry"},
    "confused": {"w": 54, "h": 46, "color": (100, 210, 230), "lid": None,
                 "r_dw": 0, "r_dh": -16, "r_lid": "sad"},
    "sleepy":   {"w": 60, "h": 14, "color": (150, 180, 220), "lid": None},
    "excited":  {"w": 68, "h": 70, "color": (255, 210, 60), "lid": None, "sparkle": True},
    "curious":  {"w": 60, "h": 62, "color": (110, 220, 235), "lid": None,
                 "r_dw": 8, "r_dh": 4},
    "smug":     {"w": 58, "h": 44, "color": (130, 220, 200), "lid": None,
                 "r_dw": 0, "r_dh": -20, "r_lid": "heavy"},
}

ENERGY = {
    "excited": 1.0, "annoyed": 0.8, "happy": 0.5, "curious": 0.5,
    "neutral": 0.3, "confused": 0.4, "smug": 0.3, "sad": 0.15, "sleepy": 0.05,
}

cur = {"w": 60.0, "h": 62.0, "r": 80.0, "g": 220.0, "b": 235.0,
       "r_dw": 0.0, "r_dh": 0.0, "ox": 0.0, "oy": 0.0}
tgt = dict(cur)
lid_L = None
lid_R = None
sparkle_on = False
blink_amt = 0.0
_settle_until = 0.0


def init():
    global _disp
    cs_pin = digitalio.DigitalInOut(board.CE0)
    dc_pin = digitalio.DigitalInOut(board.D25)
    reset_pin = digitalio.DigitalInOut(board.D24)
    spi = board.SPI()
    _disp = st7735.ST7735R(
        spi,
        cs=cs_pin,
        dc=dc_pin,
        rst=reset_pin,
        baudrate=24000000,
        width=128,
        height=160,
        x_offset=0,
        y_offset=0,
    )
    return _disp


def _cut_corner(draw, box, corner, depth_frac=0.5):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if corner == "tl":
        pts = [(x0, y0), (x0 + w * depth_frac, y0), (x0, y0 + h * depth_frac)]
    elif corner == "tr":
        pts = [(x1, y0), (x1 - w * depth_frac, y0), (x1, y0 + h * depth_frac)]
    draw.polygon(pts, fill=BG)


def _lid_top(draw, box, frac):
    x0, y0, x1, y1 = box
    draw.rectangle([x0, y0, x1, y0 + (y1 - y0) * frac], fill=BG)


def _draw_eye(draw, cx, cy, w, h, color, lid, left):
    h = max(3, h)
    w = max(6, w)
    box = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
    radius = min(w, h) * 0.28
    draw.rounded_rectangle(box, radius=radius, fill=color)
    if lid == "sad":
        _cut_corner(draw, box, "tl" if left else "tr")
    elif lid == "angry":
        _cut_corner(draw, box, "tr" if left else "tl")
    elif lid == "heavy":
        _lid_top(draw, box, 0.45)


def _frame():
    global _img, _draw
    if _img is None:
        _img = Image.new("RGB", (W, H), BG)
        _draw = ImageDraw.Draw(_img)
    _draw.rectangle([0, 0, W, H], fill=BG)

    color = (int(cur["r"]), int(cur["g"]), int(cur["b"]))
    h_l = cur["h"] * (1 - blink_amt)
    h_r = (cur["h"] + cur["r_dh"]) * (1 - blink_amt)
    w_r = cur["w"] + cur["r_dw"]

    _draw_eye(_draw, EYE_L + cur["ox"], CY + cur["oy"], cur["w"], h_l, color, lid_L, True)
    _draw_eye(_draw, EYE_R + cur["ox"], CY + cur["oy"], w_r, h_r, color, lid_R, False)

    if sparkle_on and blink_amt < 0.6:
        for ex in (EYE_L, EYE_R):
            sr = min(cur["w"], cur["h"]) * 0.1
            scx = ex + cur["ox"] - cur["w"] * 0.18
            scy = CY + cur["oy"] - cur["h"] * 0.22
            _draw.ellipse([scx - sr, scy - sr, scx + sr, scy + sr], fill=(255, 255, 255))

    _disp.image(_img, rotation=270)


def set_current(name):
    global current_face, lid_L, lid_R, sparkle_on, tgt, _settle_until
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
    sparkle_on = spec.get("sparkle", False)
    if ENERGY.get(prev, 0.3) > 0.7 and ENERGY.get(name, 0.3) < 0.5:
        _settle_until = time.time() + random.uniform(3.0, 5.0)


def _do_blink(kind):
    global blink_amt
    if current_face == "sleepy":
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


def _animate_loop():
    global cur, _running
    _running = True
    last_blink = time.time()
    next_blink_gap = random.uniform(2.0, 4.5)
    last_wander = time.time()
    next_wander_gap = random.uniform(2.5, 5.0)
    last_micro = time.time()
    next_micro_gap = random.uniform(3.0, 6.0)

    while True:
        if _speaking:
            time.sleep(0.1)
            last_blink = time.time()
            last_wander = time.time()
            continue

        now = time.time()
        settling = now < _settle_until
        ease = 0.22 if not settling else 0.12

        for k in ("w", "h", "r", "g", "b", "r_dw", "r_dh", "ox", "oy"):
            cur[k] += (tgt[k] - cur[k]) * ease

        try:
            _frame()
        except Exception:
            pass

        if now - last_blink > next_blink_gap:
            last_blink = now
            roll = random.random()
            kind = "quick" if roll < 0.55 else ("slow" if roll < 0.85 else "double")
            try:
                _do_blink(kind)
            except Exception:
                pass
            next_blink_gap = random.uniform(2.0, 5.5)

        if now - last_wander > next_wander_gap:
            last_wander = now
            amp = 10 if not settling else 5
            tgt["ox"] = random.uniform(-amp, amp)
            tgt["oy"] = random.uniform(-amp * 0.5, amp * 0.5)
            next_wander_gap = random.uniform(1.8, 4.0)
            threading.Timer(random.uniform(0.8, 1.6), lambda: tgt.update(ox=0.0, oy=0.0)).start()

        if now - last_micro > next_micro_gap:
            last_micro = now
            base = EXPR[current_face]
            jitter = random.uniform(-4, 4)
            tgt["h"] = base["h"] + jitter
            next_micro_gap = random.uniform(3.5, 7.0)
            threading.Timer(random.uniform(1.0, 2.0), lambda: tgt.update(h=base["h"])).start()

        time.sleep(0.07)


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


if __name__ == "__main__":
    init()
    start_idle()
    for name in EXPR:
        print(name)
        set_current(name)
        time.sleep(3.0)
    set_current("neutral")
    time.sleep(3.0)
