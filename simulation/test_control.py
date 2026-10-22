"""Headless check of the DDROID demonstration sequence."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ddroid_control import Controller, Plant
from ddroid_demo import run_demo
from ddroid_scene import TAGS, collar_in_drink_view
from ddroid_track import HerdBook, tags_in_image


def _frame(width, height, fill, blocks):
    """RGB frame. blocks are (x, y, w, h, r, g, b)."""
    red, green, blue = fill
    buf = bytearray([red, green, blue]) * (width * height)
    for x0, y0, w, h, r, g, b in blocks:
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                offset = (y * width + x) * 3
                buf[offset : offset + 3] = bytes((r, g, b))
    return bytes(buf)


def _tag_rgb(name):
    rgba = dict(TAGS)[name]
    return tuple(int(round(channel * 255)) for channel in rgba[:3])


def check_tracking():
    # The camera classifies collar colour and ignores the yard.
    red = _tag_rgb("cow_1")
    blue = _tag_rgb("cow_2")
    frame = _frame(24, 24, (173, 168, 158), [(2, 2, 8, 8, *red), (14, 2, 8, 8, *blue)])
    assert tags_in_image(24, 24, frame) == ["cow_1", "cow_2"]
    shaded = _frame(16, 16, (140, 82, 41), [(2, 2, 10, 10, 190, 40, 35)])
    assert tags_in_image(16, 16, shaded) == ["cow_1"]
    yard = _frame(16, 16, (51, 122, 158), [])
    assert tags_in_image(16, 16, yard) == []

    book = HerdBook()
    # Camera sees only the red collar, so that cow is billed for the sip.
    book.note_camera(["cow_1"])
    book.step(0.1, 0.32, True)
    assert book.source == "camera"
    assert abs(book.intake["cow_1"] - 0.32) < 1e-9
    assert book.intake["cow_2"] == 0.0
    assert collar_in_drink_view(*book.body_poses()["cow_1"])
    assert not collar_in_drink_view(*book.body_poses()["cow_4"])

    # A tag the camera reports outside the lip is ignored. The pair at the
    # lip is billed from the collar positions instead.
    missed = HerdBook()
    missed.note_camera(["wander_1"])
    missed.step(0.1, 0.32, True)
    assert missed.source == "tag"
    assert abs(missed.intake["cow_1"] + missed.intake["cow_2"] - 0.32) < 1e-9
    assert missed.intake["wander_1"] == 0.0

    # The next shift brings a different pair to the camera.
    later = HerdBook()
    later.step(6.0, 0.0, False)
    later.step(0.1, 0.10, True)
    assert later.intake["cow_1"] == 0.0
    assert abs(later.intake["cow_2"] - 0.05) < 1e-9
    assert abs(later.intake["cow_3"] - 0.05) < 1e-9
    x, y = later.gps["cow_2"]
    assert collar_in_drink_view(*later.body_poses()["cow_2"])
    assert abs(x) < 3 and abs(y) < 2

    # Headless drinking still shares the plant's removed litres.
    plant = Plant()
    plant.trough_l = 5.0
    ledger = HerdBook()
    removed = 0.0
    for _ in range(50):
        plant.step(0.1, False)
        removed += plant.last_drunk_l
        at_trough = plant.last_drunk_l > 0
        ledger.step(0.1, plant.last_drunk_l, at_trough)
    billed = sum(ledger.intake.values())
    assert abs(billed - removed) < 1e-6
    assert removed > 1.0
    wander_x, wander_y = ledger.gps["wander_1"]
    assert not collar_in_drink_view(*ledger.body_poses()["wander_1"])
    assert abs(wander_x) > 2 or abs(wander_y) > 2


def main():
    plant = Plant()
    low, high, source, cutoff = plant.raw_switches()
    ctl = Controller(low, high, source, cutoff)
    assert ctl.mode == "STOPPED" and ctl.pump is False

    herd = HerdBook()
    kinds, story = run_demo(plant, ctl, view=None, herd=herd, dt=0.1, realtime=False, hold_s=0.2)
    text = "\n".join(story)
    assert "reset while supply is low" in text
    assert "HIGH CUTOFF" in text
    assert "Demonstration complete" in text

    assert "armed_refill" in kinds
    assert kinds.count("full_stop") >= 2
    assert "fault" in kinds
    faults = [event["fault"] for event in ctl.events if event["kind"] == "fault"]
    assert "LOW SUPPLY" in faults
    assert "HIGH CUTOFF" in faults
    assert "reset" in kinds
    assert ctl.mode == "IDLE"
    assert ctl.pump is False
    assert ctl.fault is None

    # ADEQUATE must not start the pump. Drinking from mid-level stays IDLE
    # until the debounced state is LOW.
    hold = Plant()
    hold.trough_l = 6.0
    hold.supply_l = 15.0
    hold_ctl = Controller(True, False, True, False)
    hold_ctl.mode = "IDLE"
    for _ in range(80):
        hold_ctl.step(0.1, *hold.raw_switches())
        hold.step(0.1, hold_ctl.pump)
        assert hold_ctl.mode == "IDLE", hold_ctl.trough_state()
        assert hold_ctl.pump is False
    assert hold_ctl.trough_state() == "ADEQUATE"
    assert hold.trough_l > 3.0

    billed = sum(herd.intake.values())
    assert billed > 2.0
    assert sum(1 for name, _rgba in TAGS if name.startswith("cow_") and herd.intake[name] > 0) >= 2
    check_tracking()

    print("Control demonstration checks passed.")
    print("Events:", ", ".join(kinds))


if __name__ == "__main__":
    main()
