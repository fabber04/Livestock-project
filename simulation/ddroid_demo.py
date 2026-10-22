"""Supervised demonstration of the DDROID watering cycle.

The sequence is driven by controller events, not a fixed clock, so debounce
and pump timing can change without breaking the story:

1. Arm while the trough is LOW and refill to FULL.
2. Livestock drink through ADEQUATE without another start, then to LOW.
3. The next refill crosses the supply-low switch and latches LOW SUPPLY.
4. An early reset is rejected. Supply is topped up, then reset and arm.
5. The trough is refilled again.
6. A safety drill forces the pump past the high switch until the independent
   cutoff removes pump drive.
7. After the level falls, reset returns the machine to STOPPED and arms IDLE.
"""

import time

from ddroid_scene import SUPPLY_TOPUP_L


def _status_line(t, plant, ctl):
    pump = "ON" if plant.hardware_pump else "OFF"
    fault = ctl.fault or "-"
    return (
        f"[{t:6.1f}s] {ctl.mode:<10} pump={pump:<3} "
        f"trough={ctl.trough_state():<12} {plant.trough_l:4.1f} L  "
        f"supply={ctl.supply_state():<9} {plant.supply_l:4.1f} L  "
        f"fault={fault}"
    )


def run_demo(plant, ctl, view=None, dt=0.1, realtime=False, log=print, hold_s=8.0, on_step=None, herd=None):
    """Run one demonstration. Returns the controller event kinds in order."""
    phase = "boot"
    phase_t = 0.0
    t = 0.0
    boot_wait = 2.0
    seen_second_refill = False
    logged_status = -1.0
    story = []

    def note(text):
        story.append(text)
        log(text)

    note("DDROID water-point simulation")
    note("Startup is STOPPED with the pump OFF.")

    while True:
        low, high, source, cutoff = plant.raw_switches()

        if phase == "boot" and phase_t >= boot_wait:
            ok, reason = ctl.arm()
            note(f"OPERATOR arm automatic -> {reason}")
            phase = "first_fill"
            phase_t = 0.0
        elif phase == "supply_fault" and ctl.fault == "LOW SUPPLY":
            rejected, why = ctl.reset()
            note(f"OPERATOR reset while supply is low -> {why}")
            plant.supply_l = SUPPLY_TOPUP_L
            note("OPERATOR tops up the supply container.")
            phase = "wait_supply"
            phase_t = 0.0
        elif phase == "wait_supply" and ctl.supply_state() == "AVAILABLE":
            ok, why = ctl.reset()
            note(f"OPERATOR reset cleared fault -> {why}")
            ok, why = ctl.arm()
            note(f"OPERATOR arm automatic -> {why}")
            phase = "second_cycle"
            phase_t = 0.0
            seen_second_refill = False
        elif phase == "second_cycle" and seen_second_refill and ctl.mode == "IDLE":
            note("SAFETY DRILL: high switch ignored, cutoff must stop the pump.")
            plant.force_pump = True
            phase = "drill"
            phase_t = 0.0
        elif phase == "clear" and ctl.mode == "FAULT" and not ctl.cutoff_active:
            if phase_t >= 1.0:
                ok, why = ctl.reset()
                note(f"OPERATOR reset after cutoff dried -> {why}")
                ok, why = ctl.arm()
                note(f"OPERATOR arm automatic -> {why}")
                note(
                    "Demonstration complete. Machine is armed IDLE; "
                    "the pump stays OFF until the trough is LOW again."
                )
                phase = "hold"
                phase_t = 0.0

        ctl.step(dt, low, high, source, cutoff)
        plant.step(dt, ctl.pump)
        if herd is not None:
            at_trough = (not plant.hardware_pump) and (plant.trough_l > 0.02 or plant.last_drunk_l > 0)
            herd.step(dt, plant.last_drunk_l, at_trough)

        if phase == "first_fill" and any(
            event["kind"] == "full_stop" for event in ctl.events
        ):
            # Stay in this phase only until the first full stop, then watch
            # the drink-down and the supply fault on the following refill.
            if ctl.mode == "IDLE":
                phase = "supply_fault"
                phase_t = 0.0
        elif phase == "second_cycle" and ctl.mode == "REFILLING":
            seen_second_refill = True
        elif phase == "drill" and ctl.fault == "HIGH CUTOFF":
            note("Independent high cutoff latched HIGH CUTOFF and removed pump drive.")
            phase = "clear"
            phase_t = 0.0

        if view is not None:
            view.update(plant, ctl)
        if on_step is not None:
            on_step(t, plant, ctl)

        if t - logged_status >= 1.0:
            log(_status_line(t, plant, ctl))
            if herd is not None:
                log(herd.one_line())
            logged_status = t

        if phase == "hold" and phase_t >= hold_s:
            break
        if t > 240.0:
            note("Demonstration stopped: scenario exceeded 240 s.")
            break

        if realtime:
            time.sleep(dt)
        t += dt
        phase_t += dt

    return [event["kind"] for event in ctl.events], story
