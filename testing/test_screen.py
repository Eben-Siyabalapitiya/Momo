import time
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7735

cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)

spi = board.SPI()

disp = st7735.ST7735R(
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

width = 128
height = 160

image = Image.new("RGB", (width, height))
draw = ImageDraw.Draw(image)

draw.rectangle((0, 0, width, height), fill=(200, 30, 30))
disp.image(image)
time.sleep(1)

draw.rectangle((0, 0, width, height), fill=(30, 180, 60))
disp.image(image)
time.sleep(1)

draw.rectangle((0, 0, width, height), fill=(30, 60, 200))
disp.image(image)
time.sleep(1)

draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
draw.text((30, 70), "MOMO", fill=(255, 255, 255))
disp.image(image)
