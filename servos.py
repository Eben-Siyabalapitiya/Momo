from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)

for _ch in range(8):
    kit.servo[_ch].angle = 90

LEGS = {
    "FR": {"hip": 0, "knee": 1, "sign": -1},
    "BR": {"hip": 2, "knee": 3, "sign": -1},
    "FL": {"hip": 4, "knee": 5, "sign": 1},
    "BL": {"hip": 6, "knee": 7, "sign": 1},
}


def set_channel(channel, angle):
    angle = max(0, min(180, angle))
    kit.servo[channel].angle = angle


def center_channel(channel):
    set_channel(channel, 90)


def release_channel(channel):
    kit.servo[channel].angle = None


def center_all(channels=range(8)):
    for ch in channels:
        center_channel(ch)


def release_all(channels=range(8)):
    for ch in channels:
        release_channel(ch)


def set(leg, joint, angle):
    cfg = LEGS[leg]
    channel = cfg[joint]
    sign = cfg["sign"]
    physical = 90 + sign * (angle - 90)
    set_channel(channel, physical)
