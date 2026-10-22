"""DDROID bench controller and water-point plant.

The state machine follows the SRS appendix: STOPPED, IDLE, REFILLING,
MANUAL and FAULT. Float changes are debounced for two one-second samples.
The independent high cutoff stops the pump on the same step, with no debounce.
"""

from ddroid_scene import (
    DEBOUNCE_SAMPLES,
    DRINK_L_PER_S,
    MANUAL_LIMIT_S,
    MAX_RUN_S,
    PUMP_L_PER_S,
    SAMPLE_PERIOD_S,
    SUPPLY_CAPACITY_L,
    SUPPLY_LOW,
    SUPPLY_START_L,
    TROUGH_CAPACITY_L,
    TROUGH_CUTOFF,
    TROUGH_HIGH,
    TROUGH_LOW,
    TROUGH_START_L,
)


class Plant:
    """Two vessels, a pump, drinking livestock, and a hardware cutoff."""

    def __init__(self):
        self.trough_l = TROUGH_START_L
        self.supply_l = SUPPLY_START_L
        self.force_pump = False
        self.hardware_pump = False
        self.last_drunk_l = 0.0

    def trough_fraction(self):
        return self.trough_l / TROUGH_CAPACITY_L

    def supply_fraction(self):
        return self.supply_l / SUPPLY_CAPACITY_L

    def raw_switches(self):
        trough = self.trough_fraction()
        supply = self.supply_fraction()
        low_wet = trough >= TROUGH_LOW
        high_wet = trough >= TROUGH_HIGH
        source_wet = supply >= SUPPLY_LOW
        cutoff = trough >= TROUGH_CUTOFF
        return low_wet, high_wet, source_wet, cutoff

    def step(self, dt, software_pump):
        """Move water. The cutoff removes pump drive even if software is wrong."""
        cutoff = self.trough_fraction() >= TROUGH_CUTOFF
        commanded = bool(software_pump or self.force_pump)
        self.hardware_pump = commanded and not cutoff
        self.last_drunk_l = 0.0
        if cutoff:
            self.force_pump = False
            self.trough_l = min(self.trough_l, TROUGH_CUTOFF * TROUGH_CAPACITY_L)

        if self.hardware_pump:
            room = TROUGH_CAPACITY_L - self.trough_l
            moved = min(PUMP_L_PER_S * dt, self.supply_l, max(0.0, room))
            self.supply_l -= moved
            self.trough_l += moved
            if self.trough_fraction() >= TROUGH_CUTOFF:
                self.trough_l = TROUGH_CUTOFF * TROUGH_CAPACITY_L
                self.hardware_pump = False
                self.force_pump = False
        elif self.trough_l > 0.0:
            before = self.trough_l
            self.trough_l = max(0.0, self.trough_l - DRINK_L_PER_S * dt)
            self.last_drunk_l = before - self.trough_l

        self.supply_l = max(0.0, min(SUPPLY_CAPACITY_L, self.supply_l))
        self.trough_l = max(0.0, min(TROUGH_CAPACITY_L, self.trough_l))
        return self.hardware_pump


class Controller:
    """Local pump interlocks. Dashboard loss is irrelevant here: this is the device."""

    def __init__(self, low_wet, high_wet, source_wet, cutoff):
        self.mode = "STOPPED"
        self.pump = False
        self.fault = None
        self.acknowledged = False
        self.low_wet = bool(low_wet)
        self.high_wet = bool(high_wet)
        self.source_wet = bool(source_wet)
        self.cutoff_active = bool(cutoff)
        self.run_s = 0.0
        self.manual_s = 0.0
        self._sample_acc = 0.0
        self._cand = {
            "low_wet": self.low_wet,
            "high_wet": self.high_wet,
            "source_wet": self.source_wet,
        }
        self._count = {"low_wet": 0, "high_wet": 0, "source_wet": 0}
        self.events = []

    def trough_state(self):
        if self.high_wet and not self.low_wet:
            return "SENSOR FAULT"
        if self.low_wet and self.high_wet:
            return "FULL"
        if self.low_wet:
            return "ADEQUATE"
        return "LOW"

    def supply_state(self):
        return "AVAILABLE" if self.source_wet else "LOW"

    def _emit(self, kind):
        self.events.append(
            {
                "kind": kind,
                "mode": self.mode,
                "pump": self.pump,
                "fault": self.fault or "",
                "trough": self.trough_state(),
                "supply": self.supply_state(),
            }
        )

    def _fault(self, code):
        if self.mode == "FAULT":
            self.pump = False
            return
        self.mode = "FAULT"
        self.fault = code
        self.pump = False
        self.run_s = 0.0
        self.manual_s = 0.0
        self.acknowledged = False
        self._emit("fault")

    def _sample(self, low_raw, high_raw, source_raw):
        raw = {
            "low_wet": bool(low_raw),
            "high_wet": bool(high_raw),
            "source_wet": bool(source_raw),
        }
        for key, sample in raw.items():
            current = getattr(self, key)
            if sample == current:
                self._cand[key] = sample
                self._count[key] = 0
                continue
            if self._cand[key] != sample:
                self._cand[key] = sample
                self._count[key] = 1
            else:
                self._count[key] += 1
            if self._count[key] >= DEBOUNCE_SAMPLES:
                setattr(self, key, sample)
                self._count[key] = 0

    def _inputs_safe(self):
        if self.cutoff_active:
            return False
        if self.high_wet and not self.low_wet:
            return False
        if not self.source_wet:
            return False
        if self.fault:
            return False
        return True

    def arm(self):
        if self.mode != "STOPPED":
            return False, "arm only from STOPPED"
        if not self._inputs_safe():
            return False, "unsafe inputs or latched fault"
        if self.trough_state() == "LOW":
            self.mode = "REFILLING"
            self.pump = True
            self.run_s = 0.0
            self._emit("armed_refill")
            return True, "armed into REFILLING"
        self.mode = "IDLE"
        self.pump = False
        self._emit("armed_idle")
        return True, "armed into IDLE"

    def stop(self):
        if self.mode == "FAULT":
            self.pump = False
            self._emit("stopped")
            return
        self.mode = "STOPPED"
        self.pump = False
        self.run_s = 0.0
        self.manual_s = 0.0
        self._emit("stopped")

    def acknowledge(self):
        if self.mode != "FAULT":
            return False, "no alarm"
        self.acknowledged = True
        self._emit("acknowledged")
        return True, "acknowledged; fault remains latched"

    def reset(self):
        if self.mode != "FAULT":
            return False, "no active fault"
        if self.fault == "LOW SUPPLY" and not self.source_wet:
            return False, "supply still low"
        if self.fault == "SENSOR FAULT" and self.high_wet and not self.low_wet:
            return False, "sensor fault still present"
        if self.fault == "HIGH CUTOFF" and self.cutoff_active:
            return False, "high cutoff still wet"
        self.fault = None
        self.acknowledged = False
        self.mode = "STOPPED"
        self.pump = False
        self.run_s = 0.0
        self._emit("reset")
        return True, "reset to STOPPED"

    def manual_fill(self):
        if self.mode != "STOPPED":
            return False, "manual fill only from STOPPED"
        if not self._inputs_safe():
            return False, "unsafe inputs or latched fault"
        if self.trough_state() == "FULL":
            return False, "trough already full"
        self.mode = "MANUAL"
        self.pump = True
        self.manual_s = 0.0
        self._emit("manual_started")
        return True, "manual fill"

    def step(self, dt, low_raw, high_raw, source_raw, cutoff_raw):
        self.cutoff_active = bool(cutoff_raw)
        if self.cutoff_active:
            self._fault("HIGH CUTOFF")

        self._sample_acc += dt
        while self._sample_acc >= SAMPLE_PERIOD_S:
            self._sample_acc -= SAMPLE_PERIOD_S
            self._sample(low_raw, high_raw, source_raw)

        if self.high_wet and not self.low_wet:
            self._fault("SENSOR FAULT")
        if not self.source_wet:
            self._fault("LOW SUPPLY")

        if self.mode == "REFILLING":
            self.run_s += dt
            if self.run_s >= MAX_RUN_S:
                self._fault("PUMP TIMEOUT")
            elif self.trough_state() == "FULL":
                self.mode = "IDLE"
                self.pump = False
                self.run_s = 0.0
                self._emit("full_stop")
        elif self.mode == "MANUAL":
            self.manual_s += dt
            if (
                self.manual_s >= MANUAL_LIMIT_S
                or self.trough_state() == "FULL"
            ):
                self.mode = "STOPPED"
                self.pump = False
                self.manual_s = 0.0
                self._emit("manual_stop")
        elif self.mode == "IDLE":
            if self.trough_state() == "LOW" and self._inputs_safe():
                self.mode = "REFILLING"
                self.pump = True
                self.run_s = 0.0
                self._emit("refill_started")

        if self.mode == "FAULT":
            self.pump = False

        if self.mode not in ("REFILLING", "MANUAL"):
            self.pump = False
