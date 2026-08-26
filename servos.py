import json
import os
from adafruit_servokit import ServoKit

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

kit = ServoKit(channels=16)

offsets = {str(ch): 0 for ch in range(8)}

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH) as f:
        saved = json.load(f)
    offsets.update(saved.get("offsets", {}))

current_physical = {}

for _ch in range(8):
    kit.servo[_ch].set_pulse_width_range(500, 2500)
    physical = max(0, min(180, 90 + offsets[str(_ch)]))
    kit.servo[_ch].angle = physical
    current_physical[str(_ch)] = physical


def save_offsets():
    with open(CONFIG_PATH, "w") as f:
        json.dump({"offsets": offsets}, f, indent=2)


def set_offset(channel, offset):
    offsets[str(channel)] = offset
    save_offsets()


def get_offset(channel):
    return offsets.get(str(channel), 0)

LEGS = {
    "FR": {"hip": 0, "knee": 1, "sign": -1},
    "BR": {"hip": 2, "knee": 3, "sign": -1},
    "FL": {"hip": 4, "knee": 5, "sign": 1},
    "BL": {"hip": 6, "knee": 7, "sign": 1},
}


def set_channel(channel, angle):
    physical = max(0, min(180, angle + offsets[str(channel)]))
    kit.servo[channel].angle = physical
    current_physical[str(channel)] = physical


def center_channel(channel):
    set_channel(channel, 90)


def zero_here(channel):
    offset = current_physical[str(channel)] - 90
    set_offset(channel, offset)


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
