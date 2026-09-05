import time
from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)

kit.servo[0].angle = 30
time.sleep(1)
kit.servo[0].angle = 150
time.sleep(1)
kit.servo[0].angle = 90
time.sleep(1)
kit.servo[0].angle = None
