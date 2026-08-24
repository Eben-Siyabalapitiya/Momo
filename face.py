import time
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7735

W, H = 160, 128
BG = (8, 14, 36)

_disp = None


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


def _eye(draw, cx, cy, w, h, color, lid=None, pupil_dx=0, sparkle=False):
    h = max(h, 4)
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
    if pupil_dx or sparkle:
        pr = min(w, h) * 0.18
        pcx = cx + pupil_dx
        pcy = cy + h * 0.08
        draw.ellipse([pcx - pr, pcy - pr, pcx + pr, pcy + pr], fill=(25, 30, 45))
    if sparkle:
        sr = min(w, h) * 0.09
        scx = cx - w * 0.16
        scy = cy - h * 0.2
        draw.ellipse([scx - sr, scy - sr, scx + sr, scy + sr], fill=(255, 255, 255))


def face_neutral(d, blink=0.0):
    h = max(4, 40 * (1 - blink))
    _eye(d, 54, 50, 44, h, (80, 220, 235))
    _eye(d, 106, 50, 44, h, (80, 220, 235))
    d.line([65, 100, 95, 100], fill=(210, 220, 230), width=4)


def face_happy(d):
    _eye(d, 54, 50, 44, 24, (90, 230, 150))
    _eye(d, 106, 50, 44, 24, (90, 230, 150))
    d.arc([60, 86, 100, 114], start=20, end=160, fill=(210, 230, 220), width=5)


def face_sad(d):
    _eye(d, 54, 52, 42, 34, (120, 170, 230), lid="sad_l")
    _eye(d, 106, 52, 42, 34, (120, 170, 230), lid="sad_r")
    d.arc([62, 100, 98, 122], start=200, end=340, fill=(150, 180, 225), width=4)


def face_annoyed(d):
    _eye(d, 54, 50, 46, 16, (235, 100, 60), lid="angry_l")
    _eye(d, 106, 50, 46, 16, (235, 100, 60), lid="angry_r")
    d.line([68, 100, 92, 100], fill=(235, 120, 90), width=4)


def face_confused(d):
    _eye(d, 54, 48, 40, 36, (100, 210, 230))
    _eye(d, 106, 52, 40, 22, (140, 220, 235), lid="sad_r")
    d.line([(64, 100), (72, 94), (80, 100), (88, 94), (96, 100)], fill=(210, 220, 230), width=3)


def face_sleepy(d):
    _eye(d, 54, 50, 44, 8, (150, 180, 220))
    _eye(d, 106, 50, 44, 8, (150, 180, 220))
    d.ellipse([76, 98, 86, 108], outline=(150, 180, 220), width=3)
    font = ImageFont.load_default()
    d.text((122, 6), "Z", fill=(150, 180, 220), font=font)
    d.text((132, 16), "z", fill=(150, 180, 220), font=font)


def face_excited(d):
    _eye(d, 54, 48, 52, 52, (255, 210, 60), sparkle=True)
    _eye(d, 106, 48, 52, 52, (255, 210, 60), sparkle=True)
    d.ellipse([64, 90, 96, 118], fill=(235, 90, 90))


def face_curious(d):
    _eye(d, 54, 50, 46, 46, (110, 220, 235), pupil_dx=8)
    _eye(d, 106, 48, 50, 44, (110, 220, 235), pupil_dx=8)
    d.ellipse([74, 96, 88, 110], outline=(210, 220, 230), width=3)


def face_smug(d):
    _eye(d, 54, 50, 44, 36, (130, 220, 200))
    _eye(d, 106, 54, 44, 20, (130, 220, 200), lid="heavy")
    d.arc([58, 92, 102, 112], start=20, end=90, fill=(230, 210, 120), width=5)


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


def render(name, **kwargs):
    if _disp is None:
        init()
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    FACES.get(name, face_neutral)(d, **kwargs)
    _disp.image(img, rotation=90)


def blink():
    render("neutral", blink=0.0)
    time.sleep(0.05)
    render("neutral", blink=0.6)
    time.sleep(0.04)
    render("neutral", blink=1.0)
    time.sleep(0.06)
    render("neutral", blink=0.6)
    time.sleep(0.04)
    render("neutral", blink=0.0)


if __name__ == "__main__":
    init()
    for name in FACES:
        print(name)
        render(name)
        time.sleep(1.6)
    print("blink")
    blink()
    time.sleep(0.5)
    render("neutral")
