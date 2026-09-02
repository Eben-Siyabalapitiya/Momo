import time
import servos

HIP_SWING = 50
POWER_SWING = 75
KNEE_LIFT = 60
KNEE_STANCE = 0
STEP_DELAY = 0.18

WAVE_LEG = "FL"
WAVE_BACK_DIP = 70
WAVE_HIP_SWING = 40
WAVE_REPS = 5
WAVE_STEP_DELAY = 0.15


def _wave_knee_targets(home):
    if home < 90:
        return 180, 150
    return 0, 30

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


def wave():
    wave_knee = servos.LEGS[WAVE_LEG]["knee"]
    br_knee = servos.LEGS["BR"]["knee"]
    bl_knee = servos.LEGS["BL"]["knee"]
    wave_knee_home = servos.get_startup(wave_knee)
    br_knee_home = servos.get_startup(br_knee)
    bl_knee_home = servos.get_startup(bl_knee)
    knee_high, knee_low = _wave_knee_targets(wave_knee_home)

    servos.set_channel(wave_knee, knee_high)
    time.sleep(STEP_DELAY)
    servos.set_channel(br_knee, max(0, br_knee_home - WAVE_BACK_DIP))
    servos.set_channel(bl_knee, min(180, bl_knee_home + WAVE_BACK_DIP))
    time.sleep(STEP_DELAY)

    for _ in range(WAVE_REPS):
        servos.set_channel(wave_knee, knee_low)
        servos.set(WAVE_LEG, "hip", 90 - WAVE_HIP_SWING)
        time.sleep(WAVE_STEP_DELAY)
        servos.set_channel(wave_knee, knee_high)
        servos.set(WAVE_LEG, "hip", 90 + WAVE_HIP_SWING)
        time.sleep(WAVE_STEP_DELAY)

    servos.set(WAVE_LEG, "hip", 90)
    servos.set_channel(wave_knee, wave_knee_home)
    servos.set_channel(br_knee, br_knee_home)
    servos.set_channel(bl_knee, bl_knee_home)
    time.sleep(STEP_DELAY)


if __name__ == "__main__":
    walk_forward(3)
