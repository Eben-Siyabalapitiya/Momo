import time
import servos

HIP_SWING = 50
POWER_SWING = 170
KNEE_LIFT = 60
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


def _dip_target(home, dip):
    if home < 90:
        return min(180, home + dip)
    return max(0, home - dip)

LEG_ORDER = ["FR", "BL", "FL", "BR"]

TURN_SIDE = {"FR": 1, "BR": 1, "FL": -1, "BL": -1}
TURN_CYCLES = 2

POWER_DIR = {"FR": -1, "FL": -1}
BACK_LEGS = ["BR", "BL"]


def _reach_target(home):
    return 0 if home >= 90 else 180


def stand_tall():
    for leg in LEG_ORDER:
        knee_ch = servos.LEGS[leg]["knee"]
        servos.set_channel(knee_ch, servos.get_startup(knee_ch))
    time.sleep(STEP_DELAY)


def _step_leg(leg):
    knee_ch = servos.LEGS[leg]["knee"]
    knee_home = servos.get_startup(knee_ch)
    servos.set_channel(knee_ch, _dip_target(knee_home, KNEE_LIFT))
    time.sleep(STEP_DELAY)
    if leg in BACK_LEGS:
        hip_ch = servos.LEGS[leg]["hip"]
        servos.set_channel(hip_ch, _reach_target(servos.get_startup(hip_ch)))
    else:
        servos.set(leg, "hip", 90 + HIP_SWING)
    time.sleep(STEP_DELAY)
    servos.set_channel(knee_ch, knee_home)
    time.sleep(STEP_DELAY)


def _power_stroke():
    for leg in LEG_ORDER:
        if leg in BACK_LEGS:
            hip_ch = servos.LEGS[leg]["hip"]
            servos.set_channel(hip_ch, servos.get_startup(hip_ch))
        else:
            servos.set(leg, "hip", 90 + POWER_DIR[leg] * POWER_SWING)
    time.sleep(STEP_DELAY * 2)


def walk_forward(cycles=1):
    stand_tall()
    for _ in range(cycles):
        for leg in LEG_ORDER:
            _step_leg(leg)
        _power_stroke()


DIAGONAL_A = ["FR", "BL"]
DIAGONAL_B = ["FL", "BR"]


def _swing_leg(leg):
    knee_ch = servos.LEGS[leg]["knee"]
    knee_home = servos.get_startup(knee_ch)
    servos.set_channel(knee_ch, _dip_target(knee_home, KNEE_LIFT))
    if leg in BACK_LEGS:
        hip_ch = servos.LEGS[leg]["hip"]
        servos.set_channel(hip_ch, _reach_target(servos.get_startup(hip_ch)))
    else:
        servos.set(leg, "hip", 90 + HIP_SWING)
    return knee_ch, knee_home


def _stance_leg(leg):
    if leg in BACK_LEGS:
        hip_ch = servos.LEGS[leg]["hip"]
        servos.set_channel(hip_ch, servos.get_startup(hip_ch))
    else:
        servos.set(leg, "hip", 90 + POWER_DIR[leg] * POWER_SWING)


def _trot_phase(swing_pair, stance_pair):
    plants = []
    for leg in swing_pair:
        knee_ch, knee_home = _swing_leg(leg)
        plants.append((knee_ch, knee_home))
    for leg in stance_pair:
        _stance_leg(leg)
    time.sleep(STEP_DELAY * 2)
    for knee_ch, knee_home in plants:
        servos.set_channel(knee_ch, knee_home)
    time.sleep(STEP_DELAY)


def walk_trot(cycles=1):
    stand_tall()
    for _ in range(cycles):
        _trot_phase(DIAGONAL_A, DIAGONAL_B)
        _trot_phase(DIAGONAL_B, DIAGONAL_A)


RIGHT_PAIR = ["FR", "BR"]
LEFT_PAIR = ["FL", "BL"]


def _turn_swing_pair(pair, direction):
    plants = []
    for leg in pair:
        knee_ch = servos.LEGS[leg]["knee"]
        knee_home = servos.get_startup(knee_ch)
        servos.set_channel(knee_ch, _dip_target(knee_home, KNEE_LIFT))
        if leg in BACK_LEGS:
            hip_ch = servos.LEGS[leg]["hip"]
            servos.set_channel(hip_ch, _reach_target(servos.get_startup(hip_ch)))
        else:
            servos.set(leg, "hip", 90 + direction * TURN_SIDE[leg] * HIP_SWING)
        plants.append((knee_ch, knee_home))
    time.sleep(STEP_DELAY * 2)
    for knee_ch, knee_home in plants:
        servos.set_channel(knee_ch, knee_home)
    time.sleep(STEP_DELAY)


def _turn_pull_pair(pair, direction):
    for leg in pair:
        if leg in BACK_LEGS:
            hip_ch = servos.LEGS[leg]["hip"]
            servos.set_channel(hip_ch, servos.get_startup(hip_ch))
        else:
            servos.set(leg, "hip", 90 - direction * TURN_SIDE[leg] * POWER_SWING)
    time.sleep(STEP_DELAY * 2)


def turn(direction, cycles=TURN_CYCLES):
    stand_tall()
    for _ in range(cycles):
        _turn_swing_pair(RIGHT_PAIR, direction)
        _turn_pull_pair(RIGHT_PAIR, direction)
        _turn_swing_pair(LEFT_PAIR, direction)
        _turn_pull_pair(LEFT_PAIR, direction)


def turn_right(cycles=TURN_CYCLES):
    turn(1, cycles)


def turn_left(cycles=TURN_CYCLES):
    turn(-1, cycles)


def wave():
    wave_knee = servos.LEGS[WAVE_LEG]["knee"]
    wave_hip = servos.LEGS[WAVE_LEG]["hip"]
    dip_a_knee = servos.LEGS["FR"]["knee"]
    dip_b_knee = servos.LEGS["BR"]["knee"]
    wave_knee_home = servos.get_startup(wave_knee)
    dip_a_home = servos.get_startup(dip_a_knee)
    dip_b_home = servos.get_startup(dip_b_knee)
    knee_high, knee_low = _wave_knee_targets(wave_knee_home)

    for leg in servos.LEGS:
        servos.set_channel(servos.LEGS[leg]["hip"], 90)
    time.sleep(STEP_DELAY)

    servos.set_channel(wave_knee, knee_high)
    time.sleep(STEP_DELAY)
    servos.set_channel(dip_a_knee, _dip_target(dip_a_home, WAVE_BACK_DIP))
    servos.set_channel(dip_b_knee, _dip_target(dip_b_home, WAVE_BACK_DIP))
    time.sleep(STEP_DELAY)

    for _ in range(WAVE_REPS):
        servos.set_channel(wave_knee, knee_low)
        servos.set_channel(wave_hip, 90 - WAVE_HIP_SWING)
        time.sleep(WAVE_STEP_DELAY)
        servos.set_channel(wave_knee, knee_high)
        servos.set_channel(wave_hip, 90 + WAVE_HIP_SWING)
        time.sleep(WAVE_STEP_DELAY)

    servos.set_channel(wave_hip, 90)
    servos.set_channel(wave_knee, wave_knee_home)
    servos.set_channel(dip_a_knee, dip_a_home)
    servos.set_channel(dip_b_knee, dip_b_home)


if __name__ == "__main__":
    walk_forward(3)
