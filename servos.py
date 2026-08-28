import json
import os
from adafruit_servokit import ServoKit

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

kit = ServoKit(channels=16)

startup_angles = {str(ch): 90 for ch in range(8)}

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH) as f:
        saved = json.load(f)
    startup_angles.update(saved.get("startup_angles", {}))

for _ch in range(8):
    kit.servo[_ch].angle = startup_angles[str(_ch)]


def save_config():
    with open(CONFIG_PATH, "w") as f:
        json.dump({"startup_angles": startup_angles}, f, indent=2)


def set_channel(channel, angle):
    angle = max(0, min(180, angle))
    kit.servo[channel].angle = angle


def save_startup(channel, angle):
    startup_angles[str(channel)] = angle
    save_config()


def get_startup(channel):
    return startup_angles.get(str(channel), 90)


def reset_all():
    for ch in range(8):
        startup_angles[str(ch)] = 90
    save_config()
    for ch in range(8):
        set_channel(ch, 90)


def release_channel(channel):
    kit.servo[channel].angle = None


def center_all(channels=range(8)):
    for ch in channels:
        set_channel(ch, 90)


def release_all(channels=range(8)):
    for ch in channels:
        release_channel(ch)


LEGS = {
    "FR": {"hip": 0, "knee": 1, "hip_sign": -1, "knee_sign": 1},
    "BR": {"hip": 2, "knee": 3, "hip_sign": -1, "knee_sign": -1},
    "FL": {"hip": 4, "knee": 5, "hip_sign": 1, "knee_sign": -1},
    "BL": {"hip": 6, "knee": 7, "hip_sign": 1, "knee_sign": 1},
}


def set(leg, joint, angle):
    cfg = LEGS[leg]
    channel = cfg[joint]
    sign = cfg[joint + "_sign"]
    home = startup_angles[str(channel)]
    physical = home + sign * (angle - 90)
    set_channel(channel, physical)
