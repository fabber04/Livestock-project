"""Shared geometry and thresholds for the DDROID water-point simulation.

Levels are fractions of each vessel. Switch thresholds match the SRS:
trough LOW / ADEQUATE / FULL, plus an independent high cutoff and a supply
low switch. Volumes are in litres so the animated Gazebo scene and the
controller stay in lockstep.
"""

import math

SLICES = 16

TROUGH_LOW = 0.30
TROUGH_HIGH = 0.75
TROUGH_CUTOFF = 0.92
SUPPLY_LOW = 0.20

TROUGH_CAPACITY_L = 10.0
SUPPLY_CAPACITY_L = 18.0

PUMP_L_PER_S = 0.40
DRINK_L_PER_S = 0.32
MAX_RUN_S = 60.0
MANUAL_LIMIT_S = 15.0
SAMPLE_PERIOD_S = 1.0
DEBOUNCE_SAMPLES = 2

# Starts low in the trough, with enough supply for one full refill and a
# second refill that crosses the supply-low switch.
TROUGH_START_L = 1.2
SUPPLY_START_L = 12.3
SUPPLY_TOPUP_L = 14.0

# Ground-level farm yard. The tank and concrete trough sit on the dirt,
# and the herd stands on the ground beside the trough.
SUPPLY = {
    "cx": -2.6,
    "cy": 0.0,
    "z0": 0.22,
    "sx": 0.72,
    "sy": 0.72,
    "h": 1.10,
}
TROUGH = {
    "cx": 0.7,
    "cy": 0.0,
    "z0": 0.28,
    "sx": 2.40,
    "sy": 0.70,
    "h": 0.42,
}

HIDDEN_Z = -4.0
# Inside the kraal, north-west corner, clear of the walking loops.
SHADE_TREE_XY = (-6.9, 5.5)
PUMP_XYZ = (-0.85, 0.0, 0.42)
MODE_LAMP_XYZ = (-0.85, -0.55, 1.25)
STATUS_XYZ = (0.6, -7.6, 1.75)
# x y z roll pitch yaw. Positive pitch looks down toward the kraal.
CAMERA_POSE = (8.0, -12.5, 6.4, 0.0, 0.36, 2.16)

# Rest pose, then the y used when the herd is drinking. They only drink
# while the pump is off, which is the same rule as the plant.
HERD = (
    ("cow_1", -0.3, -1.90, 0.0, 1.57, -1.25),
    ("cow_2", 0.7, -2.00, 0.0, 1.45, -1.32),
    ("cow_3", 1.6, -1.85, 0.0, 1.75, -1.22),
    ("cow_4", 0.1, 1.90, 0.0, -1.57, 1.25),
    ("cow_5", 1.2, 2.00, 0.0, -1.40, 1.32),
)

# Worn collar tags. The colour is what the trough camera reads. The same
# tag is the GPS track. Nothing is pierced or implanted.
# Order is the drinking herd, then the animals walking the kraal.
TAGS = (
    ("cow_1", (1.00, 0.05, 0.05, 1.0)),
    ("cow_2", (0.05, 0.25, 1.00, 1.0)),
    ("cow_3", (1.00, 0.85, 0.05, 1.0)),
    ("cow_4", (0.85, 0.05, 0.85, 1.0)),
    ("cow_5", (0.05, 0.85, 0.90, 1.0)),
    ("wander_1", (1.00, 0.45, 0.05, 1.0)),
    ("wander_2", (0.55, 0.05, 0.90, 1.0)),
    ("wander_3", (0.10, 0.85, 0.25, 1.0)),
    ("wander_4", (0.95, 0.40, 0.70, 1.0)),
)
# Tag plate on the right side of the neck, in the cow's local frame.
COLLAR_LOCAL = (1.05, -0.22, 1.25)
# Two places at the south lip. Pairs rotate through them while drinking.
DRINK_STATIONS = (
    (0.05, -1.28, 1.57),
    (1.35, -1.28, 1.57),
)
DRINK_SHIFT_S = 6.0
# Collar positions the drink camera is responsible for.
DRINK_GATE = ((-0.40, 2.05), (-0.70, 0.20), (0.90, 1.70))
# x y z roll pitch yaw. Looks west along the south lip, slightly down.
DRINK_CAM_POSE = (2.70, -1.15, 1.55, 0.0, 0.15, 2.66)
INTAKE_XYZ = (3.20, -2.40, 2.10)

# Closed paths inside the larger kraal, clear of the trough and the tank.
# Each cow walks the loop at its own speed.
WANDERERS = (
    ("wander_1", 0.55, ((-6.4, -4.6), (-6.2, 4.2), (-3.6, 4.8), (-3.8, -4.8))),
    ("wander_2", 0.70, ((5.8, -4.8), (6.4, 1.2), (5.2, 4.8), (3.2, 2.4), (3.4, -4.2))),
    ("wander_3", 0.45, ((-1.2, 4.6), (4.2, 4.8), (2.4, 3.2), (-2.8, 3.4))),
    ("wander_4", 0.85, ((5.2, -1.6), (6.2, 3.0), (-5.4, 2.6), (-6.0, -2.2), (1.2, -4.8))),
)


def fraction(volume_l, capacity_l):
    if capacity_l <= 0:
        return 0.0
    return max(0.0, min(1.0, volume_l / capacity_l))


def slice_pose(vessel, index, visible):
    """World pose for one water slice. Hidden slices park below the ground."""
    if not visible:
        return (vessel["cx"], vessel["cy"], HIDDEN_Z)
    step = vessel["h"] / SLICES
    z = vessel["z0"] + (index + 0.5) * step
    return (vessel["cx"], vessel["cy"], z)


def visible_slice_count(level_fraction):
    count = int(round(level_fraction * SLICES))
    return max(0, min(SLICES, count))


def switch_anchor(vessel, level_fraction, x_shift=0.0):
    z = vessel["z0"] + level_fraction * vessel["h"]
    y = vessel["cy"] - vessel["sy"] / 2.0 - 0.14
    x = vessel["cx"] + x_shift
    return (x, y, z)


def along_loop(path, distance):
    """Position and facing yaw at a distance around a closed waypoint loop."""
    lengths = []
    for index, (x1, y1) in enumerate(path):
        x2, y2 = path[(index + 1) % len(path)]
        lengths.append(math.hypot(x2 - x1, y2 - y1))
    total = sum(lengths) or 1.0
    remaining = distance % total
    for index, length in enumerate(lengths):
        x1, y1 = path[index]
        x2, y2 = path[(index + 1) % len(path)]
        if remaining <= length or index == len(lengths) - 1:
            frac = 0.0 if length == 0 else min(1.0, remaining / length)
            return (
                x1 + (x2 - x1) * frac,
                y1 + (y2 - y1) * frac,
                math.atan2(y2 - y1, x2 - x1),
            )
        remaining -= length
    x, y = path[0]
    return x, y, 0.0


def collar_world(x, y, z, yaw):
    """World position of the collar tag for a cow standing at this pose."""
    lx, ly, lz = COLLAR_LOCAL
    c = math.cos(yaw)
    s = math.sin(yaw)
    return (x + c * lx - s * ly, y + s * lx + c * ly, z + lz)


def collar_in_drink_view(x, y, z, yaw):
    """True when the collar sits in the box the trough camera is aimed at."""
    cx, cy, cz = collar_world(x, y, z, yaw)
    (x0, x1), (y0, y1), (z0, z1) = DRINK_GATE
    return x0 <= cx <= x1 and y0 <= cy <= y1 and z0 <= cz <= z1
