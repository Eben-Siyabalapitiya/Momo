import time
import servos

HIP_SWING = 50
POWER_SWING = 75
KNEE_LIFT = 60
KNEE_STANCE = 0
STEP_DELAY = 0.18

LEG_ORDER = ["FR", "BL", "FL", "BR"]


def stand_tall():
    for leg in LEG_ORDER:
        servos.set(leg, "knee", KNEE_STANCE)
    time.sleep(STEP_DELAY)


def _step_leg(leg):
    servos.set(leg, "knee", KNEE_STANCE + KNEE_LIFT)
    time.sleep(STEP_DELAY)
    servos.set(leg, "hip", 90 + HIP_SWING)
    time.sleep(STEP_DELAY)
    servos.set(leg, "knee", KNEE_STANCE)
    time.sleep(STEP_DELAY)


def _power_stroke():
    for leg in LEG_ORDER:
        servos.set(leg, "hip", 90 - POWER_SWING)
    time.sleep(STEP_DELAY * 2)


def walk_forward(cycles=1):
    stand_tall()
    for _ in range(cycles):
        for leg in LEG_ORDER:
            _step_leg(leg)
        _power_stroke()


if __name__ == "__main__":
    walk_forward(3)
