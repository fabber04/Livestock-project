"""Render a top-down clip of collar tags, the trough camera, and per-cow litres.

The motion and the totals come from the same plant and herd ledger as the
Gazebo scene. Playback is realtime. Gazebo itself is not required.
"""

import math
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "simulation"))

from ddroid_control import Plant
from ddroid_scene import (
    DRINK_CAM_POSE,
    DRINK_GATE,
    SHADE_TREE_XY,
    TAGS,
    TROUGH,
    TROUGH_CAPACITY_L,
    collar_world,
)
from ddroid_track import tag_label, tags_in_image

FPS = 12
DURATION_S = 22.0
REFILL_S = 2.0
W, H = 1280, 720
S = 2
SCALE = 40

X0, X1 = -9.0, 8.2
Y0, Y1 = -7.6, 7.2

# Same hide order as the world: herd, then the walking cattle.
HIDES = (
    (0.93, 0.91, 0.86),
    (0.55, 0.32, 0.16),
    (0.90, 0.88, 0.82),
    (0.40, 0.24, 0.12),
    (0.72, 0.68, 0.62),
    (0.82, 0.78, 0.70),
    (0.48, 0.30, 0.16),
    (0.95, 0.93, 0.88),
    (0.33, 0.22, 0.14),
)

OUT_PATH = os.path.join(ROOT, "media", "intake_demo.mp4")


def _rgb(colour):
    return tuple(int(round(channel * 255)) for channel in colour[:3])


def _font(size, bold=False):
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name)
    if os.path.isfile(path):
        return ImageFont.truetype(path, size * S)
    return ImageFont.load_default()


def _wrap(text, font, width):
    lines = []
    current = ""
    for word in text.split():
        trial = word if not current else current + " " + word
        if font.getlength(trial) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _xy(x, y):
    px = (28 + (x - X0) * SCALE) * S
    py = (24 + (Y1 - y) * SCALE) * S
    return px, py


def _lerp_angle(a, b, t):
    delta = (b - a + math.pi) % (2 * math.pi) - math.pi
    return a + delta * t


def _ease(current, target, amount):
    return (
        current[0] + (target[0] - current[0]) * amount,
        current[1] + (target[1] - current[1]) * amount,
        target[2],
        _lerp_angle(current[3], target[3], amount),
    )


def _poly(pose, local):
    x, y, _z, yaw = pose
    c = math.cos(yaw)
    s = math.sin(yaw)
    points = []
    for lx, ly in local:
        points.append(_xy(x + c * lx - s * ly, y + s * lx + c * ly))
    return points


def _caption(t):
    if t < REFILL_S:
        return "The tank refills the trough. Every collar is already sending a GPS fix."
    if t < 8:
        return "The pump stops. Two cows step to the lip, and the camera reads their collar colours."
    if t < 15:
        return "Litres are shared only by the tags the camera picked. The others stay on GPS."
    return "A new pair steps up. Each cow keeps the water already credited to its tag."


def _camera_frame(book):
    """Small frame whose only saturated colours are the collars in the gate."""
    width, height = 80, 48
    buf = bytearray([173, 168, 158]) * (width * height)
    named = [name for name in book.in_gate if name.startswith("cow_")]
    for index, name in enumerate(named[:2]):
        red, green, blue = _rgb(dict(TAGS)[name])
        x0 = 8 + index * 36
        for y in range(10, 38):
            for x in range(x0, x0 + 26):
                offset = (y * width + x) * 3
                buf[offset : offset + 3] = bytes((red, green, blue))
    return tags_in_image(width, height, bytes(buf))


def _draw_map(draw, plant, shown, seen):
    grass = (78, 112, 58)
    dirt = (122, 90, 52)
    wood = (92, 58, 28)
    x0, y_north = _xy(-8, 6.5)
    x1, y_south = _xy(8, -6.5)
    draw.rectangle((0, 0, _xy(X1, Y0)[0] + 20, H * S), fill=grass)
    draw.rectangle((x0, y_north, x1, y_south), fill=dirt)

    tree_x, tree_y = _xy(*SHADE_TREE_XY)
    canopy = 1.25 * SCALE * S
    draw.ellipse((tree_x - canopy, tree_y - canopy, tree_x + canopy, tree_y + canopy), fill=(46, 102, 41))
    trunk = 0.18 * SCALE * S
    draw.ellipse((tree_x - trunk, tree_y - trunk, tree_x + trunk, tree_y + trunk), fill=wood)

    gate = 1.8
    rails = (
        ((-8, 6.5), (8, 6.5)),
        ((-8, -6.5), (-gate, -6.5)),
        ((gate, -6.5), (8, -6.5)),
        ((-8, -6.5), (-8, 6.5)),
        ((8, -6.5), (8, 6.5)),
    )
    for (ax, ay), (bx, by) in rails:
        draw.line((*_xy(ax, ay), *_xy(bx, by)), fill=wood, width=4 * S)

    (gx0, gx1), (gy0, gy1), _gz = DRINK_GATE
    gate_box = (*_xy(gx0, gy1), *_xy(gx1, gy0))
    draw.rectangle(gate_box, outline=(230, 190, 70), width=2 * S)

    tank = 0.55 * SCALE * S
    tx, ty = _xy(-2.6, 0.0)
    draw.ellipse((tx - tank, ty - tank, tx + tank, ty + tank), fill=(28, 82, 46), outline=(18, 50, 28), width=3 * S)
    draw.text((tx - 28 * S, ty - 10 * S), "tank", font=_font(13), fill=(230, 240, 220))

    trough = TROUGH
    left = trough["cx"] - trough["sx"] / 2
    right = trough["cx"] + trough["sx"] / 2
    bottom = trough["cy"] - trough["sy"] / 2
    top = trough["cy"] + trough["sy"] / 2
    box = (*_xy(left, top), *_xy(right, bottom))
    draw.rectangle(box, fill=(168, 164, 154), outline=(90, 88, 82), width=4 * S)
    level = plant.trough_l / TROUGH_CAPACITY_L
    inset = 5 * S
    water = (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset)
    # Fill from the bottom of the trough graphic up to the current level.
    span = water[3] - water[1]
    water_top = water[3] - span * max(0.08, level)
    draw.rectangle((water[0], water_top, water[2], water[3]), fill=(36, 110, 150))
    draw.text(_xy(left - 1.55, trough["cy"] + 0.15), "trough", font=_font(13), fill=(245, 236, 214))

    yaw = DRINK_CAM_POSE[5]
    fov = 1.15
    length = 3.3
    origin = _xy(DRINK_CAM_POSE[0], DRINK_CAM_POSE[1])
    left_edge = _xy(
        DRINK_CAM_POSE[0] + length * math.cos(yaw - fov / 2),
        DRINK_CAM_POSE[1] + length * math.sin(yaw - fov / 2),
    )
    right_edge = _xy(
        DRINK_CAM_POSE[0] + length * math.cos(yaw + fov / 2),
        DRINK_CAM_POSE[1] + length * math.sin(yaw + fov / 2),
    )
    draw.line((*origin, *left_edge), fill=(196, 150, 40), width=2 * S)
    draw.line((*origin, *right_edge), fill=(196, 150, 40), width=2 * S)
    draw.line((*left_edge, *right_edge), fill=(196, 150, 40), width=2 * S)
    cam_r = 8 * S
    draw.ellipse((origin[0] - cam_r, origin[1] - cam_r, origin[0] + cam_r, origin[1] + cam_r), fill=(25, 25, 28))
    draw.text((origin[0] + 12 * S, origin[1] - 8 * S), "camera", font=_font(13, bold=True), fill=(40, 30, 10))

    hides = {name: hide for (name, _rgba), hide in zip(TAGS, HIDES)}
    colours = dict(TAGS)
    for name, pose in shown.items():
        hide = hides[name]
        tag = colours[name]
        body = _poly(
            pose,
            ((-0.95, -0.36), (0.45, -0.36), (0.7, 0.0), (0.45, 0.36), (-0.95, 0.36)),
        )
        head = _poly(
            pose,
            ((0.55, -0.22), (1.15, -0.18), (1.35, 0.0), (1.15, 0.18), (0.55, 0.22)),
        )
        collar = _poly(pose, ((0.9, -0.30), (1.15, -0.30), (1.15, 0.30), (0.9, 0.30)))
        outline = (255, 255, 255) if name in seen else (45, 32, 18)
        width = 4 * S if name in seen else 2 * S
        draw.polygon(body, fill=_rgb(hide))
        draw.line(body + [body[0]], fill=outline, width=width)
        draw.polygon(head, fill=_rgb(hide))
        draw.line(head + [head[0]], fill=outline, width=max(1, width - S))
        draw.polygon(collar, fill=_rgb(tag))
        cx, cy, _cz = collar_world(*pose)
        px, py = _xy(cx, cy)
        radius = 7 * S
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=_rgb(tag), outline=(20, 20, 20), width=2 * S)
        label_at = _poly(pose, ((-1.35, 0.55),))[0]
        tag_name = tag_label(name)
        font = _font(13, bold=True)
        text_box = font.getbbox(tag_name)
        pad = 2 * S
        plate = (
            label_at[0] - pad,
            label_at[1] - pad,
            label_at[0] + text_box[2] + pad,
            label_at[1] + text_box[3] + pad,
        )
        draw.rectangle(plate, fill=(42, 30, 16))
        draw.text(label_at, tag_name, font=font, fill=(255, 255, 255))


def _draw_panel(draw, t, plant, book, pumping):
    left = int(_xy(X1, 0)[0]) + 28 * S
    draw.rectangle((left - 16 * S, 0, W * S, H * S), fill=(28, 32, 34))
    title = _font(26, bold=True)
    body = _font(16)
    small = _font(15)
    draw.text((left, 22 * S), "Who drank", font=title, fill=(255, 248, 235))
    draw.text((left, 58 * S), f"t = {t:4.1f} s", font=body, fill=(190, 198, 190))
    pump = "REFILLING" if pumping else "DRINKING"
    draw.text((left + 130 * S, 58 * S), pump, font=_font(16, bold=True), fill=(120, 210, 140) if pumping else (120, 190, 255))

    caption_top = 96 * S
    for line in _wrap(_caption(t), body, W * S - left - 28 * S):
        draw.text((left, caption_top), line, font=body, fill=(230, 230, 224))
        caption_top += 24 * S

    bar_top = caption_top + 16 * S
    draw.text((left, bar_top), "Trough", font=small, fill=(180, 186, 180))
    bar = (left, bar_top + 24 * S, W * S - 28 * S, bar_top + 46 * S)
    draw.rectangle(bar, fill=(50, 54, 56))
    fraction = max(0.0, min(1.0, plant.trough_l / TROUGH_CAPACITY_L))
    draw.rectangle((bar[0], bar[1], bar[0] + (bar[2] - bar[0]) * fraction, bar[3]), fill=(36, 130, 170))
    draw.text((bar[0] + 8 * S, bar[1] + 2 * S), f"{plant.trough_l:.1f} / {TROUGH_CAPACITY_L:.0f} L", font=small, fill=(255, 255, 255))

    cam_top = bar[3] + 22 * S
    how = "camera" if book.source == "camera" else "collar position"
    draw.text((left, cam_top), f"Picked by {how}", font=_font(16, bold=True), fill=(255, 220, 140))
    chip_x = left
    chip_y = cam_top + 30 * S
    if book.seen:
        for name in book.seen:
            colour = _rgb(dict(TAGS)[name])
            draw.rounded_rectangle((chip_x, chip_y, chip_x + 70 * S, chip_y + 28 * S), radius=6 * S, fill=colour)
            ink = (20, 20, 20) if name in ("cow_3", "cow_5", "wander_3") else (255, 255, 255)
            draw.text((chip_x + 18 * S, chip_y + 3 * S), tag_label(name), font=small, fill=ink)
            chip_x += 80 * S
    else:
        draw.text((left, chip_y), "none at the lip", font=body, fill=(180, 180, 170))

    row = chip_y + 48 * S
    draw.text((left, row), "Tag", font=small, fill=(150, 156, 150))
    draw.text((left + 70 * S, row), "Litres", font=small, fill=(150, 156, 150))
    draw.text((left + 170 * S, row), "GPS  x, y", font=small, fill=(150, 156, 150))
    row += 26 * S
    for name, rgba in TAGS:
        if name == "wander_1":
            row += 8 * S
            draw.text((left, row), "Walking, GPS only", font=small, fill=(150, 156, 150))
            row += 24 * S
        colour = _rgb(rgba)
        draw.ellipse((left, row + 3 * S, left + 16 * S, row + 19 * S), fill=colour)
        weight = name in book.seen
        font = _font(16, bold=weight)
        ink = (255, 248, 230) if weight else (210, 214, 208)
        draw.text((left + 26 * S, row), tag_label(name), font=font, fill=ink)
        draw.text((left + 70 * S, row), f"{book.intake[name]:5.2f}", font=font, fill=ink)
        gx, gy = book.gps[name]
        draw.text((left + 170 * S, row), f"{gx:5.1f}  {gy:5.1f}", font=font, fill=ink)
        row += 26 * S


def render_frame(t, plant, book, shown, pumping):
    image = Image.new("RGB", (W * S, H * S), (78, 112, 58))
    draw = ImageDraw.Draw(image)
    _draw_map(draw, plant, shown, set(book.seen))
    _draw_panel(draw, t, plant, book, pumping)
    return image.resize((W, H), Image.Resampling.LANCZOS)


def main():
    plant = Plant()
    plant.trough_l = 8.0
    plant.supply_l = 14.0
    from ddroid_track import HerdBook

    book = HerdBook()
    shown = dict(book.body_poses())
    frames = int(DURATION_S * FPS)
    dt = 1.0 / FPS
    folder = tempfile.mkdtemp(prefix="ddroid_clip_")
    try:
        t = 0.0
        for index in range(frames):
            pumping = t < REFILL_S
            plant.step(dt, pumping)
            at_trough = (not plant.hardware_pump) and (plant.trough_l > 0.02 or plant.last_drunk_l > 0)
            # Show the camera the collars for the pose this step is about to credit.
            saved_t = book.t
            saved_at = book.at_trough
            book.t = saved_t + dt
            book.at_trough = at_trough
            book.body_poses()
            book.note_camera(_camera_frame(book))
            book.t = saved_t
            book.at_trough = saved_at
            book.step(dt, plant.last_drunk_l, at_trough)
            target = book.body_poses()
            for name, pose in target.items():
                if name.startswith("wander_"):
                    shown[name] = pose
                else:
                    shown[name] = _ease(shown[name], pose, 0.42)
            frame = render_frame(t, plant, book, shown, pumping or plant.hardware_pump)
            frame.save(os.path.join(folder, f"f{index:04d}.png"))
            t += dt
            if index % FPS == 0:
                print(f"{t:5.1f}s  {book.one_line()}", flush=True)
        print("Encoding video...", flush=True)
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(FPS),
                "-i",
                os.path.join(folder, "f%04d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-crf",
                "20",
                OUT_PATH,
            ],
            check=True,
            capture_output=True,
        )
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
