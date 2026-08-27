import time
import servos

HIP_SWING = 25
KNEE_LIFT = 25
STEP_DELAY = 0.15

LEG_ORDER = ["FR", "BL", "FL", "BR"]


def _step_leg(leg):
    servos.set(leg, "knee", 90 + KNEE_LIFT)
    time.sleep(STEP_DELAY)
    servos.set(leg, "hip", 90 + HIP_SWING)
    time.sleep(STEP_DELAY)
    servos.set(leg, "knee", 90)
    time.sleep(STEP_DELAY)


def _power_stroke():
    for leg in LEG_ORDER:
        servos.set(leg, "hip", 90 - HIP_SWING)
    time.sleep(STEP_DELAY * 2)
    for leg in LEG_ORDER:
        servos.set(leg, "hip", 90)
    time.sleep(STEP_DELAY)


def walk_forward(cycles=1):
    for _ in range(cycles):
        for leg in LEG_ORDER:
            _step_leg(leg)
        _power_stroke()


if __name__ == "__main__":
    walk_forward(3)
