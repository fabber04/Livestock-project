"""Write the Gazebo world and the model library for the DDROID water point.

Props live under simulation/models, grouped by kind:

  Yard, Trees, Kraal, Sign, Water, Cameras, Controls, Cattle

The world places them with <include><uri>model://name</uri>. Gazebo 10
resolves a relative include path from the directory it was started in,
not from the world file, so model:// plus GZ_SIM_RESOURCE_PATH is the
only form that loads from anywhere. scripts/launch_gui.sh puts every
group folder on that path. Model names are therefore unique across groups.
"""

import math
import os
import shutil
import xml.etree.ElementTree as ET

from ddroid_scene import (
    CAMERA_POSE,
    COLLAR_LOCAL,
    DRINK_CAM_POSE,
    HERD,
    HIDDEN_Z,
    MODE_LAMP_XYZ,
    PUMP_XYZ,
    SHADE_TREE_XY,
    SLICES,
    STATUS_XYZ,
    SUPPLY,
    SUPPLY_LOW,
    TAGS,
    TROUGH,
    TROUGH_CUTOFF,
    TROUGH_HIGH,
    TROUGH_LOW,
    WANDERERS,
    slice_pose,
    switch_anchor,
)
from ddroid_track import tags_in_image

SIM_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SIM_DIR, "models")
WORLD_PATH = os.path.join(SIM_DIR, "worlds", "ddroid_water_point.sdf")
GUI_PATH = os.path.join(SIM_DIR, "gui.config")

PLASTIC_DARK = (0.28, 0.32, 0.36, 1.0)
WATER = (0.20, 0.48, 0.62, 0.92)
WOOD = (0.40, 0.26, 0.13, 1.0)
GUM_POLE = (0.47, 0.40, 0.32, 1.0)
BARK = (0.30, 0.22, 0.15, 1.0)
GROUND = (0.36, 0.50, 0.22, 1.0)
DIRT = (0.50, 0.37, 0.22, 1.0)
MUD = (0.30, 0.21, 0.11, 1.0)
TRACK = (0.58, 0.45, 0.29, 1.0)
CONCRETE = (0.68, 0.66, 0.62, 1.0)
LEAF = (0.18, 0.40, 0.16, 1.0)
LEAF_LIGHT = (0.30, 0.44, 0.18, 1.0)
LEAF_DARK = (0.13, 0.30, 0.12, 1.0)
TUFT = (0.24, 0.42, 0.16, 1.0)
TUFT_DRY = (0.62, 0.56, 0.34, 1.0)
ROCK = (0.52, 0.50, 0.46, 1.0)
ROCK_DARK = (0.40, 0.38, 0.35, 1.0)
COW_HIDES = (
    (0.93, 0.91, 0.86, 1.0),
    (0.55, 0.32, 0.16, 1.0),
    (0.90, 0.88, 0.82, 1.0),
    (0.40, 0.24, 0.12, 1.0),
    (0.72, 0.68, 0.62, 1.0),
    (0.82, 0.78, 0.70, 1.0),
    (0.48, 0.30, 0.16, 1.0),
    (0.95, 0.93, 0.88, 1.0),
    (0.33, 0.22, 0.14, 1.0),
)
COAT_NAMES = (
    "cow_cream",
    "cow_brown",
    "cow_offwhite",
    "cow_dark_brown",
    "cow_grey",
    "cow_tan",
    "cow_chestnut",
    "cow_white",
    "cow_dark",
)
WET = (0.10, 0.35, 0.85, 1.0)
DRY = (0.75, 0.75, 0.72, 1.0)
CUTOFF_WET = (0.85, 0.15, 0.12, 1.0)
PUMP_BODY = (0.15, 0.16, 0.18, 1.0)
LAMP_ON = (0.95, 0.55, 0.05, 1.0)
LAMP_OFF = (0.25, 0.25, 0.25, 1.0)
MODE_COLOURS = {
    "stopped": (0.45, 0.45, 0.45, 1.0),
    "idle": (0.15, 0.65, 0.25, 1.0),
    "refilling": (0.10, 0.35, 0.90, 1.0),
    "manual": (0.90, 0.70, 0.10, 1.0),
    "fault": (0.85, 0.12, 0.10, 1.0),
}
TANK_GREEN = (0.10, 0.36, 0.20, 1.0)
SIGN_BOARD = (0.08, 0.09, 0.10, 1.0)
ENCLOSURE = (0.86, 0.86, 0.82, 1.0)
ALUMINIUM = (0.70, 0.72, 0.74, 1.0)
SOLAR_CELL = (0.07, 0.10, 0.22, 1.0)
DARK = (0.06, 0.06, 0.07, 1.0)

# Lamps and markers are meant to be bright; the camera's gate box keeps
# them from being billed. Collar visuals carry the tag colour on purpose.
SIGNAL_PREFIXES = ("mode_", "pump_lamp_", "marker_")
TAG_VISUALS = ("collar", "collar_tag", "gps_puck")

# model name -> group folder, filled by write_model
MODEL_GROUPS = {}


def _fmt(values):
    return " ".join(f"{value:.4f}" for value in values)


def _material(rgba, glow=False):
    r, g, b, a = rgba
    emissive = ""
    if glow:
        emissive = f"<emissive>{r * 0.7:.3f} {g * 0.7:.3f} {b * 0.7:.3f} 1</emissive>"
    return (
        "<material>"
        f"<ambient>{r} {g} {b} {a}</ambient>"
        f"<diffuse>{r} {g} {b} {a}</diffuse>"
        f"<specular>0.15 0.15 0.15 {a}</specular>"
        f"{emissive}"
        "</material>"
    )


def _pose(values):
    x, y, z = values[:3]
    roll = values[3] if len(values) > 3 else 0.0
    pitch = values[4] if len(values) > 4 else 0.0
    yaw = values[5] if len(values) > 5 else 0.0
    return f"{x:.4f} {y:.4f} {z:.4f} {roll:.4f} {pitch:.4f} {yaw:.4f}"


def write_model(category, name, description, body):
    """Write model.sdf and model.config for one prop."""
    if MODEL_GROUPS.get(name, category) != category:
        raise RuntimeError(f"model {name} is in both {MODEL_GROUPS[name]} and {category}")
    MODEL_GROUPS[name] = category
    folder = os.path.join(MODELS_DIR, category, name)
    os.makedirs(folder, exist_ok=True)
    sdf = (
        '<?xml version="1.0" ?>\n'
        '<sdf version="1.9">\n'
        f'  <model name="{name}">\n'
        "    <pose>0 0 0 0 0 0</pose>\n"
        f"{body.rstrip()}\n"
        "  </model>\n"
        "</sdf>\n"
    )
    config = (
        '<?xml version="1.0" ?>\n'
        "<model>\n"
        f"  <name>{name}</name>\n"
        "  <version>1.0</version>\n"
        '  <sdf version="1.9">model.sdf</sdf>\n'
        "  <author>\n"
        "    <name>DDROID</name>\n"
        "    <email>n02528843x@students.nust.ac.zw</email>\n"
        "  </author>\n"
        f"  <description>{description}</description>\n"
        "</model>\n"
    )
    with open(os.path.join(folder, "model.sdf"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(sdf)
    with open(os.path.join(folder, "model.config"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(config)


def include(model, name=None, pose=(0, 0, 0, 0, 0, 0)):
    if model not in MODEL_GROUPS:
        raise RuntimeError(f"{model} is placed before it is written")
    instance = model if name is None else name
    return (
        "    <include>\n"
        f"      <uri>model://{model}</uri>\n"
        f"      <name>{instance}</name>\n"
        f"      <pose>{_pose(pose)}</pose>\n"
        "    </include>"
    )


def _visual(name, pose, geometry, rgba, glow=False):
    return (
        f'        <visual name="{name}">\n'
        f"          <pose>{pose}</pose>\n"
        f"          <geometry>{geometry}</geometry>\n"
        f"          {_material(rgba, glow)}\n"
        "        </visual>"
    )


def link_box(name, center, size, rgba, collision=True):
    collision_xml = ""
    if collision:
        collision_xml = (
            '\n      <collision name="collision">'
            f"<geometry><box><size>{_fmt(size)}</size></box></geometry>"
            "</collision>"
        )
    return (
        f'    <link name="{name}">\n'
        f"      <pose>{_fmt(center)} 0 0 0</pose>\n"
        '      <visual name="visual">\n'
        f"        <geometry><box><size>{_fmt(size)}</size></box></geometry>\n"
        f"        {_material(rgba)}\n"
        "      </visual>"
        f"{collision_xml}\n"
        "    </link>"
    )


def centered_shape(geometry, rgba, collision_geometry=None, movable=False, mass=0.05, glow=False):
    """One link whose geometry sits on the model origin."""
    collision_xml = ""
    if collision_geometry is not None:
        collision_xml = (
            '\n      <collision name="collision">'
            f"<geometry>{collision_geometry}</geometry></collision>"
        )
    if movable:
        motion = (
            "    <static>false</static>\n"
            '    <link name="link">\n'
            "      <kinematic>true</kinematic>\n"
            "      <gravity>false</gravity>\n"
            "      <inertial>\n"
            f"        <mass>{mass}</mass>\n"
            "        <inertia>\n"
            "          <ixx>0.0001</ixx><ixy>0</ixy><ixz>0</ixz>\n"
            "          <iyy>0.0001</iyy><iyz>0</iyz><izz>0.0001</izz>\n"
            "        </inertia>\n"
            "      </inertial>\n"
        )
    else:
        motion = '    <static>true</static>\n    <link name="link">\n'
    return (
        f"{motion}"
        '      <visual name="visual">\n'
        f"        <geometry>{geometry}</geometry>\n"
        f"        {_material(rgba, glow)}\n"
        "      </visual>"
        f"{collision_xml}\n"
        "    </link>"
    )


def static_visuals(visuals, collision_geometry=None, collision_pose="0 0 0 0 0 0"):
    """One static link made of several visuals, with an optional collision."""
    collision_xml = ""
    if collision_geometry is not None:
        collision_xml = (
            '\n      <collision name="collision">'
            f"<pose>{collision_pose}</pose>"
            f"<geometry>{collision_geometry}</geometry></collision>"
        )
    return (
        "    <static>true</static>\n"
        '    <link name="link">\n'
        f"{chr(10).join(visuals)}"
        f"{collision_xml}\n"
        "    </link>"
    )


def box_geom(size):
    return f"<box><size>{_fmt(size)}</size></box>"


def cylinder_geom(radius, length):
    return f"<cylinder><radius>{radius:.4f}</radius><length>{length:.4f}</length></cylinder>"


def sphere_geom(radius):
    return f"<sphere><radius>{radius:.4f}</radius></sphere>"


def ellipsoid_geom(rx, ry, rz):
    return f"<ellipsoid><radii>{rx:.4f} {ry:.4f} {rz:.4f}</radii></ellipsoid>"


def capsule_geom(radius, length):
    return f"<capsule><radius>{radius:.4f}</radius><length>{length:.4f}</length></capsule>"


def flat_oval_geom(rx, ry, height, sides=40):
    """Thin oval slab. A squashed ellipsoid would shade like a dome."""
    points = "".join(
        f"<point>{rx * math.cos(2 * math.pi * k / sides):.4f} "
        f"{ry * math.sin(2 * math.pi * k / sides):.4f}</point>"
        for k in range(sides)
    )
    return f"<polyline>{points}<height>{height:.4f}</height></polyline>"


def cow_body(hide, tag):
    """Full-size cow. Feet rest on the origin, head towards local +X.

    The collar and the plate on the right side of the neck are one worn
    tag. The trough camera reads the plate colour. The same point is the
    GPS fix.
    """
    patch = (0.10, 0.10, 0.11, 1.0)
    hoof = (0.08, 0.07, 0.06, 1.0)
    horn = (0.86, 0.80, 0.66, 1.0)
    nose = (0.20, 0.14, 0.13, 1.0)
    lx, ly, lz = COLLAR_LOCAL
    visuals = [
        _visual("body", "0 0 1.05 0 0 0", ellipsoid_geom(0.98, 0.36, 0.33), hide),
        _visual("belly", "0.05 0 0.88 0 0 0", ellipsoid_geom(0.72, 0.30, 0.24), hide),
        _visual("rump", "-0.70 0 1.10 0 0 0", ellipsoid_geom(0.34, 0.33, 0.30), hide),
        _visual("hump", "0.62 0 1.36 0 0 0", ellipsoid_geom(0.24, 0.17, 0.13), hide),
        _visual("patch_shoulder", "0.32 0.08 1.14 0 0 0", ellipsoid_geom(0.30, 0.30, 0.22), patch),
        _visual("patch_hip", "-0.48 -0.08 1.12 0 0 0", ellipsoid_geom(0.26, 0.30, 0.20), patch),
        _visual("neck", "1.00 0 1.20 0 -0.45 0", ellipsoid_geom(0.28, 0.18, 0.22), hide),
        _visual("dewlap", "1.02 0 0.98 0 0 0", ellipsoid_geom(0.20, 0.06, 0.16), hide),
        _visual("head", "1.40 0 1.24 0 0.35 0", ellipsoid_geom(0.27, 0.16, 0.17), hide),
        _visual("muzzle", "1.62 0 1.10 0 0 0", ellipsoid_geom(0.13, 0.12, 0.10), nose),
        _visual("eye_left", "1.46 0.14 1.30 0 0 0", sphere_geom(0.028), DARK),
        _visual("eye_right", "1.46 -0.14 1.30 0 0 0", sphere_geom(0.028), DARK),
        _visual("ear_left", "1.30 0.24 1.36 0.35 0 0", box_geom((0.06, 0.20, 0.10)), hide),
        _visual("ear_right", "1.30 -0.24 1.36 -0.35 0 0", box_geom((0.06, 0.20, 0.10)), hide),
        _visual("horn_left", "1.30 0.16 1.50 -0.6 0 0", capsule_geom(0.03, 0.22), horn),
        _visual("horn_right", "1.30 -0.16 1.50 0.6 0 0", capsule_geom(0.03, 0.22), horn),
        _visual("tail", "-1.02 0 0.92 0 -0.2 0", capsule_geom(0.025, 0.60), hide),
        _visual("tail_tuft", "-0.95 0 0.58 0 0 0", sphere_geom(0.06), patch),
        _visual("collar", "1.05 0 1.22 0 0 0", box_geom((0.14, 0.40, 0.18)), tag),
        _visual(
            "collar_tag",
            f"{lx:.2f} {ly:.2f} {lz:.2f} 0 0 0",
            box_geom((0.20, 0.05, 0.32)),
            tag,
        ),
        _visual("gps_puck", "1.05 0 1.42 0 0 0", sphere_geom(0.06), tag),
    ]
    for index, (dx, dy) in enumerate(((-0.62, -0.22), (-0.62, 0.22), (0.55, -0.22), (0.55, 0.22))):
        visuals.append(
            _visual(f"leg_{index}", f"{dx:.2f} {dy:.2f} 0.42 0 0 0", capsule_geom(0.065, 0.56), hide)
        )
        visuals.append(
            _visual(f"hoof_{index}", f"{dx:.2f} {dy:.2f} 0.04 0 0 0", cylinder_geom(0.07, 0.08), hoof)
        )
    return (
        "    <static>false</static>\n"
        '    <link name="link">\n'
        "      <kinematic>true</kinematic>\n"
        "      <gravity>false</gravity>\n"
        "      <inertial>\n"
        "        <mass>1</mass>\n"
        "        <inertia>\n"
        "          <ixx>0.02</ixx><ixy>0</ixy><ixz>0</ixz>\n"
        "          <iyy>0.02</iyy><iyz>0</iyz><izz>0.02</izz>\n"
        "        </inertia>\n"
        "      </inertial>\n"
        f"{chr(10).join(visuals)}\n"
        "    </link>"
    )


def vessel_body(spec, wall_h, rgba, wall):
    """Open-top tank. The near wall is lower so the water surface stays visible."""
    cx, cy, z0 = spec["cx"], spec["cy"], spec["z0"]
    sx, sy = spec["sx"], spec["sy"]
    side_z = z0 + wall_h / 2
    lip = wall_h * 0.42
    parts = [
        link_box("floor", (cx, cy, z0 - wall / 2), (sx + 2 * wall, sy + 2 * wall, wall), rgba),
        link_box("wall_left", (cx - sx / 2 - wall / 2, cy, side_z), (wall, sy, wall_h), rgba),
        link_box("wall_right", (cx + sx / 2 + wall / 2, cy, side_z), (wall, sy, wall_h), rgba),
        link_box("wall_back", (cx, cy + sy / 2 + wall / 2, side_z), (sx + 2 * wall, wall, wall_h), rgba),
        link_box(
            "wall_front",
            (cx, cy - sy / 2 - wall / 2, z0 + lip / 2),
            (sx + 2 * wall, wall, lip),
            rgba,
        ),
    ]
    return "    <static>true</static>\n" + "\n".join(parts)


ROCKS = (
    ("rock", -9.4, -3.2, 0.4),
    ("rock", -10.2, 2.5, 1.1),
    ("rock", 9.3, 4.8, 2.0),
    ("rock", 10.1, -5.6, 0.3),
    ("rock", -4.5, 7.8, 1.7),
    ("rock", 5.2, 7.6, 0.9),
    ("rock", -6.8, -7.9, 2.4),
    ("rock", 3.6, -8.4, 1.2),
    ("rock", 12.0, 1.0, 0.7),
    ("rock", -12.5, 6.0, 2.9),
    ("rock_small", -9.1, -2.6, 0.2),
    ("rock_small", 9.6, 5.3, 1.4),
    ("rock_small", -4.0, 8.2, 0.8),
    ("rock_small", 4.2, -8.0, 2.2),
    ("rock_small", -7.3, -8.3, 1.0),
    ("rock_small", 11.2, -2.0, 0.5),
)
TUFTS = (
    (-9.0, 0.5), (-9.8, -6.0), (-11.0, 4.0), (9.2, 1.5),
    (10.4, -1.0), (9.0, -6.8), (-2.5, 7.6), (2.0, 7.9),
    (6.8, 8.6), (-7.5, 8.4), (-3.5, -7.9), (5.8, -7.6),
    (-10.6, -1.4), (12.4, 4.4), (-13.0, -3.5), (7.4, -9.2),
)


def build_yard():
    write_model(
        "Yard",
        "ground",
        "Grass plane under the kraal.",
        (
            "    <static>true</static>\n"
            '    <link name="link">\n'
            '      <collision name="collision">\n'
            "        <geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry>\n"
            "      </collision>\n"
            '      <visual name="visual">\n'
            "        <geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry>\n"
            f"        {_material(GROUND)}\n"
            "      </visual>\n"
            "    </link>"
        ),
    )
    write_model(
        "Yard",
        "yard",
        "Dirt pad of the kraal.",
        centered_shape(box_geom((18.0, 15.0, 0.03)), DIRT),
    )
    write_model(
        "Yard",
        "trough_mud",
        "Trampled wet ground where the herd stands to drink.",
        centered_shape(flat_oval_geom(2.3, 2.9, 0.012), MUD),
    )
    write_model(
        "Yard",
        "gate_track",
        "Worn track from the south gate to the trough.",
        centered_shape(flat_oval_geom(1.4, 2.6, 0.006), TRACK),
    )
    write_model(
        "Yard",
        "rock",
        "Granite boulder.",
        centered_shape(ellipsoid_geom(0.35, 0.25, 0.18), ROCK),
    )
    write_model(
        "Yard",
        "rock_small",
        "Small stone.",
        centered_shape(ellipsoid_geom(0.18, 0.14, 0.10), ROCK_DARK),
    )
    write_model(
        "Yard",
        "grass_tuft",
        "Clump of veld grass.",
        static_visuals(
            [
                _visual("clump_a", "0 0 0.06 0 0 0", ellipsoid_geom(0.20, 0.18, 0.13), TUFT),
                _visual("clump_b", "0.16 0.08 0.05 0 0 0.6", ellipsoid_geom(0.14, 0.12, 0.10), TUFT_DRY),
                _visual("clump_c", "-0.12 0.10 0.04 0 0 1.1", ellipsoid_geom(0.12, 0.10, 0.08), TUFT),
            ]
        ),
    )
    parts = [
        include("ground"),
        include("yard", pose=(0.0, 0.0, 0.015, 0, 0, 0)),
        include("trough_mud", pose=(TROUGH["cx"], TROUGH["cy"] - 0.4, 0.03, 0, 0, 0)),
        include("gate_track", pose=(0.4, -4.4, 0.03, 0, 0, 0.12)),
    ]
    counts = {}
    for model, x, y, yaw in ROCKS:
        counts[model] = counts.get(model, 0) + 1
        parts.append(include(model, name=f"{model}_{counts[model]}", pose=(x, y, 0.0, 0, 0, yaw)))
    for index, (x, y) in enumerate(TUFTS, start=1):
        parts.append(include("grass_tuft", name=f"grass_tuft_{index}", pose=(x, y, 0.0, 0, 0, index * 0.7)))
    return "\n".join(parts)


ACACIAS = (
    (-11.5, 8.2, 0.4),
    (11.2, -4.6, 1.9),
    (11.5, 7.8, 3.1),
    (-12.4, -6.0, 5.0),
)


def build_trees():
    visuals = [
        _visual("trunk", "0 0 1.10 0 0.08 0", cylinder_geom(0.14, 2.2), BARK),
        _visual("branch_east", "0.35 0.10 2.35 0 0.75 0", cylinder_geom(0.07, 1.2), BARK),
        _visual("branch_west", "-0.30 -0.15 2.30 0 -0.7 0", cylinder_geom(0.06, 1.1), BARK),
        _visual("canopy", "0.15 0 3.05 0 0 0", ellipsoid_geom(2.1, 1.8, 0.38), LEAF),
        _visual("canopy_top", "-0.20 0.20 3.35 0 0 0", ellipsoid_geom(1.3, 1.1, 0.28), LEAF_LIGHT),
        _visual("canopy_low", "1.10 -0.60 2.85 0 0 0", ellipsoid_geom(1.0, 0.9, 0.26), LEAF_DARK),
    ]
    write_model(
        "Trees",
        "acacia",
        "Flat-topped acacia: leaning trunk, two limbs, layered canopy.",
        static_visuals(visuals, cylinder_geom(0.14, 2.2), "0 0 1.10 0 0 0"),
    )
    parts = [include("acacia", name="shade_tree", pose=(*SHADE_TREE_XY, 0.0, 0, 0, 2.2))]
    for index, (x, y, yaw) in enumerate(ACACIAS, start=1):
        parts.append(include("acacia", name=f"acacia_{index}", pose=(x, y, 0.0, 0, 0, yaw)))
    return "\n".join(parts)


def _kraal_posts():
    half_x, half_y = 8.0, 6.5
    gap = 1.8
    posts = []
    x = -half_x
    while x <= half_x + 0.01:
        if abs(x) > gap:
            posts.append((x, -half_y))
        posts.append((x, half_y))
        x += 2.0
    y = -half_y + 2.0
    while y < half_y - 0.01:
        posts.append((-half_x, y))
        posts.append((half_x, y))
        y += 2.0
    return posts, half_x, half_y, gap


def build_kraal():
    posts, half_x, half_y, gap = _kraal_posts()
    if len(posts) != 29:
        raise RuntimeError(f"expected 29 kraal posts, got {len(posts)}")
    span = half_x * 2
    depth = half_y * 2
    side = half_x - gap
    rail = (0.08, 0.08)
    write_model(
        "Kraal",
        "post",
        "Gum-pole kraal post.",
        centered_shape(cylinder_geom(0.07, 1.6), GUM_POLE, cylinder_geom(0.07, 1.6)),
    )
    write_model(
        "Kraal",
        "rail_span",
        "Long kraal rail used on the north side.",
        centered_shape(box_geom((span, rail[0], rail[1])), WOOD),
    )
    write_model(
        "Kraal",
        "rail_gate",
        "Shorter kraal rail used on either side of the south gate.",
        centered_shape(box_geom((side, rail[0], rail[1])), WOOD),
    )
    write_model(
        "Kraal",
        "rail_side",
        "Kraal rail used on the east and west sides.",
        centered_shape(box_geom((rail[0], depth, rail[1])), WOOD),
    )
    leaf = gap - 0.05
    brace = (leaf**2 + 0.75**2) ** 0.5
    write_model(
        "Kraal",
        "gate_leaf",
        "One leaf of the south gate. The origin is the hinge.",
        static_visuals(
            [
                _visual("stile_hinge", "0.04 0 0.78 0 0 0", box_geom((0.08, 0.08, 0.90)), GUM_POLE),
                _visual("stile_end", f"{leaf - 0.04:.4f} 0 0.78 0 0 0", box_geom((0.08, 0.08, 0.90)), GUM_POLE),
                _visual("rail_top", f"{leaf / 2:.4f} 0 1.15 0 0 0", box_geom((leaf, 0.06, 0.08)), WOOD),
                _visual("rail_mid", f"{leaf / 2:.4f} 0 0.78 0 0 0", box_geom((leaf, 0.06, 0.06)), WOOD),
                _visual("rail_low", f"{leaf / 2:.4f} 0 0.40 0 0 0", box_geom((leaf, 0.06, 0.08)), WOOD),
                _visual(
                    "brace",
                    f"{leaf / 2:.4f} 0 0.78 0 {-math.atan2(0.75, leaf):.4f} 0",
                    box_geom((brace, 0.05, 0.06)),
                    WOOD,
                ),
            ]
        ),
    )
    parts = [
        include("post", name=f"kraal_post_{index}", pose=(x, y, 0.8, 0, 0, 0))
        for index, (x, y) in enumerate(posts)
    ]
    for level, z in (("low", 0.55), ("mid", 0.85), ("high", 1.15)):
        parts.extend(
            [
                include("rail_span", name=f"rail_north_{level}", pose=(0.0, half_y, z, 0, 0, 0)),
                include(
                    "rail_gate",
                    name=f"rail_south_left_{level}",
                    pose=(-(gap + side / 2), -half_y, z, 0, 0, 0),
                ),
                include(
                    "rail_gate",
                    name=f"rail_south_right_{level}",
                    pose=(gap + side / 2, -half_y, z, 0, 0, 0),
                ),
                include("rail_side", name=f"rail_west_{level}", pose=(-half_x, 0.0, z, 0, 0, 0)),
                include("rail_side", name=f"rail_east_{level}", pose=(half_x, 0.0, z, 0, 0, 0)),
            ]
        )
    # Both leaves swing out of the kraal and rest open beside the fence.
    parts.append(include("gate_leaf", name="gate_west", pose=(-gap, -half_y, 0.0, 0, 0, math.pi + 0.35)))
    parts.append(include("gate_leaf", name="gate_east", pose=(gap, -half_y, 0.0, 0, 0, -0.35)))
    return "\n".join(parts)


def build_sign():
    sx, sy, sz = STATUS_XYZ
    post_h = sz + 0.645
    body = "\n".join(
        [
            "    <static>true</static>",
            link_box("post_left", (sx - 0.95, sy, post_h / 2), (0.08, 0.08, post_h), GUM_POLE, collision=False),
            link_box("post_right", (sx + 0.95, sy, post_h / 2), (0.08, 0.08, post_h), GUM_POLE, collision=False),
            link_box("board", (sx, sy, sz), (2.2, 0.06, 1.15), SIGN_BOARD, collision=False),
            link_box("cap", (sx, sy, sz + 0.62), (2.4, 0.16, 0.05), WOOD, collision=False),
        ]
    )
    write_model("Sign", "status_sign", "Mode board under a small roof, on two posts.", body)
    return include("status_sign")


def build_water():
    write_model(
        "Water",
        "supply_tank",
        "Green storage tank, open at the top.",
        vessel_body(SUPPLY, SUPPLY["h"] + 0.18, TANK_GREEN, wall=0.06),
    )
    write_model(
        "Water",
        "trough",
        "Concrete drinking trough, open at the top.",
        vessel_body(TROUGH, TROUGH["h"] + 0.12, CONCRETE, wall=0.08),
    )
    write_model(
        "Water",
        "supply_plinth",
        "Concrete pad under the storage tank.",
        centered_shape(cylinder_geom(0.66, 0.16), CONCRETE, cylinder_geom(0.66, 0.16)),
    )
    supply_x = SUPPLY["cx"] + 0.58
    trough_x = TROUGH["cx"] - TROUGH["sx"] / 2
    pipe_length = max(0.2, trough_x - supply_x)
    write_model(
        "Water",
        "pipe",
        "Pipe from the storage tank to the trough.",
        centered_shape(box_geom((pipe_length, 0.06, 0.06)), PLASTIC_DARK, box_geom((pipe_length, 0.06, 0.06))),
    )
    for prefix, vessel in (("supply", SUPPLY), ("trough", TROUGH)):
        step = vessel["h"] / SLICES
        size = (vessel["sx"] * 0.96, vessel["sy"] * 0.96, step * 0.92)
        write_model(
            "Water",
            f"{prefix}_water",
            f"One movable slice of water in the {prefix}.",
            centered_shape(box_geom(size), WATER, movable=True, mass=0.05),
        )
    slices = []
    for prefix, vessel in (("supply", SUPPLY), ("trough", TROUGH)):
        for index in range(SLICES):
            center = slice_pose(vessel, index, visible=False)
            slices.append(
                include(
                    f"{prefix}_water",
                    name=f"{prefix}_water_{index:02d}",
                    pose=(*center, 0, 0, 0),
                )
            )
    return "\n".join(
        [
            include("supply_plinth", pose=(SUPPLY["cx"], SUPPLY["cy"], 0.08, 0, 0, 0)),
            include("supply_tank"),
            include("trough"),
            include("pipe", pose=((supply_x + trough_x) / 2, 0.0, 0.62, 0, 0, 0)),
            *slices,
        ]
    )


def build_cattle():
    if len(COAT_NAMES) != len(COW_HIDES):
        raise RuntimeError("each hide colour needs a coat name")
    animals = [row[0] for row in HERD] + [row[0] for row in WANDERERS]
    if animals != [name for name, _rgba in TAGS]:
        raise RuntimeError("each animal needs a collar tag, herd first")
    if len(animals) != len(COAT_NAMES):
        raise RuntimeError("each animal needs a coat")
    for coat, hide, (animal, tag) in zip(COAT_NAMES, COW_HIDES, TAGS):
        label = coat.removeprefix("cow_").replace("_", " ")
        write_model(
            "Cattle",
            coat,
            f"Cow with a {label} coat and a {animal} collar tag.",
            cow_body(hide, tag),
        )
    parts = []
    for (name, x, y, z, yaw, _drink_y), coat in zip(HERD, COAT_NAMES):
        parts.append(include(coat, name=name, pose=(x, y, z, 0, 0, yaw)))
    for (name, _speed, path), coat in zip(WANDERERS, COAT_NAMES[len(HERD) :]):
        x, y = path[0]
        parts.append(include(coat, name=name, pose=(x, y, 0.0, 0, 0, 0)))
    return "\n".join(parts)


def build_controls():
    write_model(
        "Controls",
        "pump",
        "Pump body between the tank and the trough.",
        centered_shape(cylinder_geom(0.16, 0.48), PUMP_BODY, cylinder_geom(0.16, 0.48)),
    )
    write_model(
        "Controls",
        "pump_lamp_off",
        "Dark pump lamp, shown while the pump is off.",
        centered_shape(sphere_geom(0.08), LAMP_OFF, movable=True, mass=0.02),
    )
    write_model(
        "Controls",
        "pump_lamp_on",
        "Amber pump lamp, shown while the pump is running.",
        centered_shape(sphere_geom(0.08), LAMP_ON, movable=True, mass=0.02, glow=True),
    )
    for name, rgba in MODE_COLOURS.items():
        write_model(
            "Controls",
            f"mode_{name}",
            f"Mode lamp for the {name} state.",
            centered_shape(sphere_geom(0.09), rgba, movable=True, mass=0.02, glow=name != "stopped"),
        )
    write_model(
        "Controls",
        "marker_wet",
        "Blue float-switch marker.",
        centered_shape(sphere_geom(0.06), WET, movable=True, mass=0.02, glow=True),
    )
    write_model(
        "Controls",
        "marker_dry",
        "Grey float-switch marker.",
        centered_shape(sphere_geom(0.06), DRY, movable=True, mass=0.02),
    )
    write_model(
        "Controls",
        "marker_cutoff_wet",
        "Red high-cutoff marker.",
        centered_shape(sphere_geom(0.07), CUTOFF_WET, movable=True, mass=0.02, glow=True),
    )
    write_model(
        "Controls",
        "marker_cutoff_dry",
        "Grey high-cutoff marker.",
        centered_shape(sphere_geom(0.07), DRY, movable=True, mass=0.02),
    )
    lamp_base = MODE_LAMP_XYZ[2] - 0.09
    write_model(
        "Controls",
        "controller_cabinet",
        "ESP32 controller enclosure on a pole. The mode lamp sits on top.",
        static_visuals(
            [
                _visual("pole", "0 0 0.34 0 0 0", cylinder_geom(0.04, 0.68), ALUMINIUM),
                _visual("enclosure", "0 0 0.86 0 0 0", box_geom((0.30, 0.16, 0.36)), ENCLOSURE),
                _visual("display", "0 -0.082 0.92 0 0 0", box_geom((0.20, 0.006, 0.08)), DARK),
                _visual(
                    "lamp_holder",
                    f"0 0 {(1.04 + lamp_base) / 2:.4f} 0 0 0",
                    cylinder_geom(0.04, lamp_base - 1.04),
                    PUMP_BODY,
                ),
            ],
            box_geom((0.30, 0.16, 1.04)),
            "0 0 0.52 0 0 0",
        ),
    )
    write_model(
        "Controls",
        "solar_panel",
        "Panel that charges the pump battery, tilted north.",
        static_visuals(
            [
                _visual("pole", "0 0 0.70 0 0 0", cylinder_geom(0.05, 1.40), ALUMINIUM),
                _visual("mount", "0 0 1.42 0 0 0", box_geom((0.10, 0.10, 0.10)), ALUMINIUM),
                _visual("frame", "0 0 1.50 -0.35 0 0", box_geom((1.24, 0.74, 0.04)), ALUMINIUM),
                _visual("cells", "0 0 1.50 -0.35 0 0", box_geom((1.18, 0.68, 0.046)), SOLAR_CELL),
            ],
            cylinder_geom(0.05, 1.40),
            "0 0 0.70 0 0 0",
        ),
    )

    hidden_mode = (MODE_LAMP_XYZ[0], MODE_LAMP_XYZ[1], HIDDEN_Z, 0, 0, 0)
    shown_mode = (*MODE_LAMP_XYZ, 0, 0, 0)
    lamp_z = PUMP_XYZ[2] + 0.36
    parts = [
        include("pump", pose=(*PUMP_XYZ, 0, 0, 0)),
        include("controller_cabinet", pose=(MODE_LAMP_XYZ[0], MODE_LAMP_XYZ[1], 0.0, 0, 0, 0)),
        include("solar_panel", pose=(SUPPLY["cx"], SUPPLY["cy"] + 1.35, 0.0, 0, 0, 0)),
        include("pump_lamp_off", pose=(PUMP_XYZ[0], PUMP_XYZ[1], lamp_z, 0, 0, 0)),
        include("pump_lamp_on", pose=(PUMP_XYZ[0], PUMP_XYZ[1], HIDDEN_Z, 0, 0, 0)),
    ]
    for name in MODE_COLOURS:
        pose = shown_mode if name == "stopped" else hidden_mode
        parts.append(include(f"mode_{name}", pose=pose))

    def markers(name, anchor, wet_model, dry_model):
        hidden = (anchor[0], anchor[1], HIDDEN_Z, 0, 0, 0)
        shown = (*anchor, 0, 0, 0)
        return [
            include(wet_model, name=f"{name}_wet", pose=hidden),
            include(dry_model, name=f"{name}_dry", pose=shown),
        ]

    parts.extend(markers("supply_low", switch_anchor(SUPPLY, SUPPLY_LOW), "marker_wet", "marker_dry"))
    parts.extend(
        markers(
            "trough_low",
            switch_anchor(TROUGH, TROUGH_LOW, x_shift=-0.80),
            "marker_wet",
            "marker_dry",
        )
    )
    parts.extend(
        markers(
            "trough_high",
            switch_anchor(TROUGH, TROUGH_HIGH, x_shift=0.0),
            "marker_wet",
            "marker_dry",
        )
    )
    parts.extend(
        markers(
            "trough_cutoff",
            switch_anchor(TROUGH, TROUGH_CUTOFF, x_shift=0.80),
            "marker_cutoff_wet",
            "marker_cutoff_dry",
        )
    )
    return "\n".join(parts)


def build_drink_camera():
    """Post and camera at the south lip, looking along the drinking line."""
    x, y, z, roll, pitch, yaw = DRINK_CAM_POSE
    housing = (0.12, 0.12, 0.13, 1.0)
    body = "\n".join(
        [
            "    <static>true</static>",
            link_box("post", (x, y, z / 2), (0.08, 0.08, z), GUM_POLE, collision=False),
            (
                '    <link name="head">\n'
                f"      <pose>{x:.4f} {y:.4f} {z:.4f} {roll:.4f} {pitch:.4f} {yaw:.4f}</pose>\n"
                '      <visual name="housing">\n'
                "        <pose>-0.08 0 0 0 0 0</pose>\n"
                "        <geometry><box><size>0.14 0.10 0.08</size></box></geometry>\n"
                f"        {_material(housing)}\n"
                "      </visual>\n"
                '      <visual name="sun_hood">\n'
                "        <pose>-0.05 0 0.05 0 0 0</pose>\n"
                "        <geometry><box><size>0.20 0.13 0.015</size></box></geometry>\n"
                f"        {_material(housing)}\n"
                "      </visual>\n"
                '      <visual name="lens">\n'
                "        <pose>0.01 0 0 0 0 0</pose>\n"
                "        <geometry><box><size>0.02 0.05 0.05</size></box></geometry>\n"
                f"        {_material((0.02, 0.02, 0.02, 1.0))}\n"
                "      </visual>\n"
                '      <sensor name="drink_cam" type="camera">\n'
                "        <always_on>1</always_on>\n"
                "        <update_rate>4</update_rate>\n"
                "        <visualize>false</visualize>\n"
                "        <topic>drink_cam</topic>\n"
                "        <camera>\n"
                "          <horizontal_fov>1.15</horizontal_fov>\n"
                "          <image>\n"
                "            <width>320</width>\n"
                "            <height>240</height>\n"
                "            <format>R8G8B8</format>\n"
                "          </image>\n"
                "          <clip>\n"
                "            <near>0.15</near>\n"
                "            <far>8</far>\n"
                "          </clip>\n"
                "        </camera>\n"
                "      </sensor>\n"
                "    </link>"
            ),
        ]
    )
    write_model(
        "Cameras",
        "drink_cam",
        "Camera at the trough that reads collar tags while cattle drink.",
        body,
    )
    return include("drink_cam")


def gui_block():
    """Default Gazebo window, with the camera already aimed at the bench."""
    with open(GUI_PATH, encoding="utf-8") as handle:
        body = handle.read().replace("\r\n", "\n").lstrip("\ufeff")
    if body.startswith("<?xml"):
        body = body.split("?>", 1)[1].lstrip()
    indented = "\n".join(("    " + line) if line else line for line in body.splitlines())
    return f'    <gui fullscreen="0">\n{indented}\n    </gui>'


def world_xml():
    sections = "\n\n".join(
        [
            build_yard(),
            build_trees(),
            build_kraal(),
            build_sign(),
            build_water(),
            build_drink_camera(),
            build_controls(),
            build_cattle(),
        ]
    )
    return f"""<?xml version="1.0" ?>
<sdf version="1.9">
  <world name="ddroid">
    <!--
      Generated by simulation/build_world.py. Props are models under
      simulation/models (Yard, Trees, Kraal, Sign, Water, Cameras, Controls,
      Cattle), included as model://name. Open with scripts/launch_gui.sh,
      which puts those folders on GZ_SIM_RESOURCE_PATH.
    -->
    <gravity>0 0 -9.8</gravity>
    <physics name="ddroid_physics" type="ignored">
      <max_step_size>0.004</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>

    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>1.0 0.95 0.84 1</diffuse>
      <specular>0.25 0.25 0.22 1</specular>
      <direction>-0.40 -0.30 -0.86</direction>
    </light>
    <light type="directional" name="sky_fill">
      <cast_shadows>false</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.26 0.30 0.36 1</diffuse>
      <specular>0 0 0 1</specular>
      <direction>0.40 0.30 -0.60</direction>
    </light>
    <scene>
      <ambient>0.40 0.42 0.46 1</ambient>
      <background>0.68 0.80 0.92 1</background>
      <shadows>true</shadows>
      <grid>false</grid>
    </scene>

{sections}

    {gui_block()}

    <model name="overview_camera">
      <static>true</static>
      <pose>{CAMERA_POSE[0]:.2f} {CAMERA_POSE[1]:.2f} {CAMERA_POSE[2]:.2f} 0 {CAMERA_POSE[4]:.2f} {CAMERA_POSE[5]:.2f}</pose>
      <link name="link">
        <sensor name="camera" type="camera">
          <always_on>1</always_on>
          <update_rate>4</update_rate>
          <visualize>false</visualize>
          <topic>overview</topic>
          <camera>
            <horizontal_fov>1.15</horizontal_fov>
            <image>
              <width>960</width>
              <height>540</height>
              <format>R8G8B8</format>
            </image>
            <clip>
              <near>0.1</near>
              <far>40</far>
            </clip>
          </camera>
        </sensor>
      </link>
    </model>
  </world>
</sdf>
"""


def _model_sdf(name):
    return os.path.join(MODELS_DIR, MODEL_GROUPS[name], name, "model.sdf")


def _check_scenery_colours():
    """No prop other than a collar may read as a collar on the drink camera."""
    for name in sorted(MODEL_GROUPS):
        if name.startswith(SIGNAL_PREFIXES):
            continue
        for visual in ET.parse(_model_sdf(name)).getroot().iter("visual"):
            if visual.get("name") in TAG_VISUALS:
                continue
            diffuse = visual.findtext("material/diffuse")
            rgb = bytes(round(float(value) * 255) for value in diffuse.split()[:3])
            hits = tags_in_image(10, 10, rgb * 100)
            if hits:
                raise RuntimeError(
                    f"{MODEL_GROUPS[name]}/{name} visual {visual.get('name')} "
                    f"reads as the {hits[0]} collar"
                )


def _check_world(xml):
    root = ET.fromstring(xml)
    names = []
    for node in root.iter("include"):
        uri = node.findtext("uri")
        instance = node.findtext("name")
        if not uri or not instance:
            raise RuntimeError("an include is missing a uri or a name")
        model = uri.removeprefix("model://")
        if model == uri or model not in MODEL_GROUPS:
            raise RuntimeError(f"unknown model uri {uri}")
        folder = os.path.dirname(_model_sdf(model))
        ET.parse(os.path.join(folder, "model.sdf"))
        ET.parse(os.path.join(folder, "model.config"))
        names.append(instance)
    for node in root.iter("model"):
        if node.get("name"):
            names.append(node.get("name"))
    needed = [f"supply_water_{index:02d}" for index in range(SLICES)]
    needed += [f"trough_water_{index:02d}" for index in range(SLICES)]
    needed += [name for name, *_rest in HERD]
    needed += [name for name, *_rest in WANDERERS]
    for prefix in ("supply_low", "trough_low", "trough_high", "trough_cutoff"):
        needed += [f"{prefix}_wet", f"{prefix}_dry"]
    needed += [f"mode_{name}" for name in MODE_COLOURS]
    needed += ["pump_lamp_on", "pump_lamp_off", "drink_cam"]
    missing = [name for name in needed if name not in names]
    if missing:
        raise RuntimeError("world is missing " + ", ".join(missing))
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise RuntimeError("duplicate model names: " + ", ".join(duplicates))
    _check_scenery_colours()


def main():
    if os.path.isdir(MODELS_DIR):
        shutil.rmtree(MODELS_DIR)
    MODEL_GROUPS.clear()
    os.makedirs(os.path.dirname(WORLD_PATH), exist_ok=True)
    xml = world_xml()
    _check_world(xml)
    with open(WORLD_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(xml)
    print(WORLD_PATH)


if __name__ == "__main__":
    main()
