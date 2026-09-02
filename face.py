import time
import random
import threading
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7735

W, H = 160, 128
BG = (8, 14, 36)

_disp = None
current_face = "neutral"
_idle_started = False
_speaking = False


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


def _cut_corner(draw, box, corner, depth_frac=0.55):
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


def _eye(draw, cx, cy, w, h, color, lid=None, pupil_dx=0, sparkle=False, blink=0.0):
    h = max(4, h * (1 - blink))
    box = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
    radius = min(w, h) * 0.42
    draw.rounded_rectangle(box, radius=radius, fill=color)
    if lid == "sad_l":
        _cut_corner(draw, box, "tl")
    elif lid == "sad_r":
        _cut_corner(draw, box, "tr")
    elif lid == "angry_l":
        _cut_corner(draw, box, "tr")
    elif lid == "angry_r":
        _cut_corner(draw, box, "tl")
    elif lid == "heavy":
        _lid_top(draw, box, 0.45)
    if (pupil_dx or sparkle) and blink < 0.7:
        pr = min(w, h) * 0.18
        pcx = cx + pupil_dx
        pcy = cy + h * 0.08
        draw.ellipse([pcx - pr, pcy - pr, pcx + pr, pcy + pr], fill=(25, 30, 45))
    if sparkle and blink < 0.7:
        sr = min(w, h) * 0.09
        scx = cx - w * 0.16
        scy = cy - h * 0.2
        draw.ellipse([scx - sr, scy - sr, scx + sr, scy + sr], fill=(255, 255, 255))


EYE_L = 38
EYE_R = 122
CY = 46


def face_neutral(d, blink=0.0):
    _eye(d, EYE_L, CY, 52, 48, (80, 220, 235), blink=blink)
    _eye(d, EYE_R, CY, 52, 48, (80, 220, 235), blink=blink)
    d.line([58, 104, 102, 104], fill=(210, 220, 230), width=5)


def face_happy(d, blink=0.0):
    _eye(d, EYE_L, CY, 52, 30, (90, 230, 150), blink=blink)
    _eye(d, EYE_R, CY, 52, 30, (90, 230, 150), blink=blink)
    d.arc([52, 88, 108, 122], start=20, end=160, fill=(210, 230, 220), width=6)


def face_sad(d, blink=0.0):
    _eye(d, EYE_L, CY + 2, 50, 40, (120, 170, 230), lid="sad_l", blink=blink)
    _eye(d, EYE_R, CY + 2, 50, 40, (120, 170, 230), lid="sad_r", blink=blink)
    d.arc([54, 100, 106, 126], start=200, end=340, fill=(150, 180, 225), width=5)


def face_annoyed(d, blink=0.0):
    _eye(d, EYE_L, CY, 54, 20, (235, 100, 60), lid="angry_l", blink=blink)
    _eye(d, EYE_R, CY, 54, 20, (235, 100, 60), lid="angry_r", blink=blink)
    d.line([60, 104, 100, 104], fill=(235, 120, 90), width=5)


def face_confused(d, blink=0.0):
    _eye(d, EYE_L, CY - 2, 46, 42, (100, 210, 230), blink=blink)
    _eye(d, EYE_R, CY + 2, 46, 26, (140, 220, 235), lid="sad_r", blink=blink)
    d.line([(56, 104), (66, 96), (78, 104), (90, 96), (102, 104)], fill=(210, 220, 230), width=4)


def face_sleepy(d, blink=0.0):
    _eye(d, EYE_L, CY, 52, 10, (150, 180, 220), blink=0.0)
    _eye(d, EYE_R, CY, 52, 10, (150, 180, 220), blink=0.0)
    d.ellipse([70, 100, 90, 118], outline=(150, 180, 220), width=4)
    font = ImageFont.load_default()
    d.text((128, 4), "Z", fill=(150, 180, 220), font=font)
    d.text((140, 16), "z", fill=(150, 180, 220), font=font)


def face_excited(d, blink=0.0):
    _eye(d, EYE_L, CY - 2, 58, 58, (255, 210, 60), sparkle=True, blink=blink)
    _eye(d, EYE_R, CY - 2, 58, 58, (255, 210, 60), sparkle=True, blink=blink)
    d.ellipse([58, 94, 102, 126], fill=(235, 90, 90))


def face_curious(d, blink=0.0):
    _eye(d, EYE_L, CY, 52, 52, (110, 220, 235), pupil_dx=10, blink=blink)
    _eye(d, EYE_R, CY - 2, 56, 50, (110, 220, 235), pupil_dx=10, blink=blink)
    d.ellipse([68, 100, 92, 118], outline=(210, 220, 230), width=4)


def face_smug(d, blink=0.0):
    _eye(d, EYE_L, CY, 50, 40, (130, 220, 200), blink=blink)
    _eye(d, EYE_R, CY + 4, 50, 22, (130, 220, 200), lid="heavy", blink=blink)
    d.arc([52, 96, 108, 120], start=20, end=90, fill=(230, 210, 120), width=6)


FACES = {
    "neutral": face_neutral,
    "happy": face_happy,
    "sad": face_sad,
    "annoyed": face_annoyed,
    "confused": face_confused,
    "sleepy": face_sleepy,
    "excited": face_excited,
    "curious": face_curious,
    "smug": face_smug,
}


def render(name, talking=False, mouth_open=False, **kwargs):
    if _disp is None:
        init()
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    FACES.get(name, face_neutral)(d, **kwargs)
    if talking:
        if mouth_open:
            d.ellipse([62, 96, 98, 124], fill=(230, 100, 100))
        else:
            d.line([64, 108, 96, 108], fill=(210, 220, 230), width=5)
    _disp.image(img, rotation=270)


def set_current(name):
    global current_face
    if name in FACES:
        current_face = name
        render(name)


def blink(name=None):
    name = name or current_face
    if name == "sleepy":
        return
    render(name, blink=1.0)
    time.sleep(0.09)
    render(name, blink=0.0)


def _idle_loop():
    while True:
        time.sleep(random.uniform(2.5, 5.5))
        if _speaking:
            continue
        try:
            blink()
        except Exception:
            pass


def start_idle():
    global _idle_started
    if _idle_started:
        return
    _idle_started = True
    t = threading.Thread(target=_idle_loop, daemon=True)
    t.start()


def _talk_loop():
    mouth_open = True
    while _speaking:
        try:
            render(current_face, talking=True, mouth_open=mouth_open)
        except Exception:
            pass
        mouth_open = not mouth_open
        time.sleep(0.14)


def start_talking():
    global _speaking
    _speaking = True
    t = threading.Thread(target=_talk_loop, daemon=True)
    t.start()


def stop_talking():
    global _speaking
    _speaking = False
    render(current_face)


if __name__ == "__main__":
    init()
    for name in FACES:
        print(name)
        render(name)
        time.sleep(1.6)
    print("blink")
    blink("neutral")
    time.sleep(0.5)
    render("neutral")
