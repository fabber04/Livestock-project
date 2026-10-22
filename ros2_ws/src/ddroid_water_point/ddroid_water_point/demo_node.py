"""Publish the DDROID water-point controller on ROS 2.

The plant and state machine stay in simulation/. This node is the middleware:
it publishes mode, pump, levels and faults, and it accepts operator commands.
Pass --gazebo to drive the Gazebo Jetty scene on the ddroid partition.
"""

import os
import sys
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, String


def find_simulation_dir():
    override = os.environ.get("DDROID_SIM")
    if override and os.path.isfile(os.path.join(override, "ddroid_control.py")):
        return override
    parent = os.path.abspath(os.path.dirname(__file__))
    for _ in range(12):
        candidate = os.path.join(parent, "simulation")
        if os.path.isfile(os.path.join(candidate, "ddroid_control.py")):
            return candidate
        parent = os.path.dirname(parent)
    raise RuntimeError(
        "Could not find simulation/ddroid_control.py. Set DDROID_SIM to that folder."
    )


class DdroidNode(Node):
    def __init__(self, plant, ctl, view, interactive, herd):
        super().__init__("ddroid_controller")
        self.plant = plant
        self.ctl = ctl
        self.view = view
        self.herd = herd
        self.interactive = interactive
        self.dt = 0.1
        self._mode = self.create_publisher(String, "/ddroid/mode", 10)
        self._pump = self.create_publisher(Bool, "/ddroid/pump", 10)
        self._fault = self.create_publisher(String, "/ddroid/fault", 10)
        self._trough_state = self.create_publisher(String, "/ddroid/trough_state", 10)
        self._supply_state = self.create_publisher(String, "/ddroid/supply_state", 10)
        self._trough_l = self.create_publisher(Float32, "/ddroid/trough_litres", 10)
        self._supply_l = self.create_publisher(Float32, "/ddroid/supply_litres", 10)
        self._status = self.create_publisher(String, "/ddroid/status", 10)
        self._intake = self.create_publisher(String, "/ddroid/intake", 10)
        self._gps = self.create_publisher(String, "/ddroid/gps", 10)
        if interactive:
            self.create_subscription(String, "/ddroid/command", self.on_command, 10)
            self.create_timer(self.dt, self.on_timer)
        else:
            self.create_timer(0.5, self.publish_state)

    def log_story(self, text):
        self.get_logger().info(text)

    def publish_state(self, *_args):
        mode = String()
        mode.data = self.ctl.mode
        pump = Bool()
        pump.data = bool(self.plant.hardware_pump)
        fault = String()
        fault.data = self.ctl.fault or ""
        trough_state = String()
        trough_state.data = self.ctl.trough_state()
        supply_state = String()
        supply_state.data = self.ctl.supply_state()
        trough_l = Float32()
        trough_l.data = float(self.plant.trough_l)
        supply_l = Float32()
        supply_l.data = float(self.plant.supply_l)
        status = String()
        status.data = (
            f"{self.ctl.mode} pump={'ON' if pump.data else 'OFF'} "
            f"trough={trough_state.data} {trough_l.data:.1f}L "
            f"supply={supply_state.data} {supply_l.data:.1f}L "
            f"fault={fault.data or '-'}"
        )
        self._mode.publish(mode)
        self._pump.publish(pump)
        self._fault.publish(fault)
        self._trough_state.publish(trough_state)
        self._supply_state.publish(supply_state)
        self._trough_l.publish(trough_l)
        self._supply_l.publish(supply_l)
        self._status.publish(status)
        if self.herd is not None:
            intake = String()
            intake.data = self.herd.intake_text()
            gps = String()
            gps.data = self.herd.gps_text()
            self._intake.publish(intake)
            self._gps.publish(gps)

    def on_timer(self):
        low, high, source, cutoff = self.plant.raw_switches()
        self.ctl.step(self.dt, low, high, source, cutoff)
        self.plant.step(self.dt, self.ctl.pump)
        if self.herd is not None:
            at_trough = (not self.plant.hardware_pump) and (
                self.plant.trough_l > 0.02 or self.plant.last_drunk_l > 0
            )
            self.herd.step(self.dt, self.plant.last_drunk_l, at_trough)
        if self.view is not None:
            self.view.update(self.plant, self.ctl)
        self.publish_state()

    def on_command(self, msg):
        from ddroid_scene import SUPPLY_TOPUP_L

        command = msg.data.strip().lower()
        if command == "arm":
            _ok, why = self.ctl.arm()
        elif command == "stop":
            self.ctl.stop()
            why = "stopped"
        elif command == "reset":
            _ok, why = self.ctl.reset()
        elif command == "acknowledge":
            _ok, why = self.ctl.acknowledge()
        elif command == "manual":
            _ok, why = self.ctl.manual_fill()
        elif command == "topup":
            self.plant.supply_l = SUPPLY_TOPUP_L
            why = "supply topped up"
        else:
            why = "unknown command; use arm, stop, reset, acknowledge, manual, or topup"
        self.get_logger().info(why)


def _prepare(demo):
    simulation = find_simulation_dir()
    if simulation not in sys.path:
        sys.path.insert(0, simulation)
    os.environ.setdefault("GZ_PARTITION", "ddroid")
    use_gazebo = "--gazebo" in sys.argv
    sys.argv = [arg for arg in sys.argv if arg != "--gazebo"]

    from ddroid_control import Controller, Plant
    from ddroid_track import HerdBook

    rclpy.init()
    plant = Plant()
    ctl = Controller(*plant.raw_switches())
    herd = HerdBook()
    view = None
    if use_gazebo:
        from run_sim import GazeboView

        view = GazeboView(herd)
        view.update(plant, ctl)
    node = DdroidNode(plant, ctl, view, interactive=not demo, herd=herd)
    if demo:
        from ddroid_demo import run_demo

        def worker():
            run_demo(
                plant,
                ctl,
                view=view,
                herd=herd,
                dt=0.1,
                realtime=True,
                log=node.log_story,
                hold_s=12.0,
                on_step=node.publish_state,
            )
            node.get_logger().info(
                "Demonstration finished. The last state stays on the topics. Ctrl+C to exit."
            )

        threading.Thread(target=worker, daemon=True).start()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main_demo():
    _prepare(demo=True)


def main_controller():
    _prepare(demo=False)
