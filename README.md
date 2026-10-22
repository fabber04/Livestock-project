# DDROID livestock water-point simulation

Prototype for the group project **DDROID Smart Livestock Watering and Monitoring System**, built by the DDROID Project Team (Group 4) for the Second Year Group Project course, BSc Hons Computer Science, National University of Science and Technology (NUST). The requirements are in `docs/DDROID_SRS.pdf`.

## Team

| Team member | Role |
| --- | --- |
| Tapiwa Chigome | Project Manager |
| Fabilous Lashid | Software Engineer |
| Tanatswa Bernard Nyautore | Systems Engineer |
| Tinotenda Gozi | Network Engineer |
| Praise Muzvonda | Programmer 1 |
| Nickson Gondwe | Programmer 2 |
| Claris Chinanga | Test Programmer |
| Divine Pezari | Database Administrator |
| Lionel Tadiwanashe Tiugari | AI/ML Engineer |
| Keith Tawananyasha Mutabvuri | Chief Security Officer |

Repository contact: n02528843x@students.nust.ac.zw

## Workspace

```text
docs/          SRS and the "how the project works" guide (PDF)
media/         intake_demo.mp4, collar intake at the trough
scripts/       install_gazebo.sh, install_ros2.sh, launch_gui.sh, run_ros_demo.sh, verify_ros.sh
simulation/    controller, herd tracking, world builder, and the Gazebo yard
  models/      Yard, Trees, Kraal, Sign, Water, Cameras, Controls, Cattle
  worlds/      ddroid_water_point.sdf, generated from those models
  frames/      screenshots (ignored by git)
ros2_ws/       ROS 2 package ddroid_water_point
tools/         build_guide.py, render_intake_clip.py, snapshot_world.py, windows/ capture helpers
```

Run every script from the repository root.

The machine is a stationary water-point controller. An ESP32-style state machine reads float switches, runs a low-voltage pump, and latches faults. Gazebo shows the bench. ROS 2 carries the same status and operator commands.

This copy was installed and run on:

| Item | Version used here |
| --- | --- |
| Host | Windows, WSL2 |
| Guest | Ubuntu 26.04.1 LTS (Resolute), x86_64 |
| Gazebo | Jetty, `gz sim` 10.5.0 (`gz-jetty` from the OSRF stable archive) |
| ROS 2 | Lyrical, `ros-lyrical-ros-base` |
| Python | 3.14 |

Ubuntu 26.04 is the platform ROS 2 Lyrical publishes packages for. Gazebo Jetty is the matching simulator (`gz-sim` 10) in the OSRF archive for the same Ubuntu release. Older pairs such as ROS 2 Jazzy plus Gazebo Harmonic target Ubuntu 24.04, so they were not installed on this PC.

On this machine Gazebo uses the NVIDIA GeForce GTX 1650 through WSLg's D3D12 driver. `scripts/launch_gui.sh` selects that adapter. The Intel graphics chip is left unused.

## 1. Install Gazebo

Inside Ubuntu, as root:

```bash
apt-get update
apt-get install -y curl ca-certificates gnupg
curl -fsSL https://packages.osrfoundation.org/gazebo.gpg \
  -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  > /etc/apt/sources.list.d/gazebo-stable.list
apt-get update
apt-get install -y gz-jetty python3-gz-transport15 python3-gz-msgs12
gz sim --versions
```

`gz sim --versions` should print `10.5.0` or another Jetty `gz-sim` 10 release. This PC already has that install, so the command is only needed on a new machine. `scripts/install_gazebo.sh` repeats the package install when the OSRF source is already configured.

## 2. Install ROS 2 Lyrical

As root, from the repository root:

```bash
bash scripts/install_ros2.sh
```

That script adds `http://packages.ros.org/ros2/ubuntu resolute` and installs `ros-lyrical-ros-base`, `ros-lyrical-std-msgs`, colcon, and rosdep.

Check it:

```bash
source /opt/ros/lyrical/setup.bash
ros2 pkg list | head
```

## 3. Controller check without Gazebo

From `simulation/` in Ubuntu:

```bash
cd simulation
python3 test_control.py
```

The script must finish without an assertion. It arms a refill, rejects a reset while the supply is still low, then clears a high-cutoff fault only after the cutoff switch has dried.

## 4. Run the Gazebo scene

From Ubuntu, with WSLg (`DISPLAY=:0`):

```bash
bash scripts/launch_gui.sh
```

A window titled **Gazebo Sim** opens on a farm yard: a three-rail kraal with its gate open, acacia trees, a storage tank with a solar panel, the controller cabinet, a concrete trough on trampled mud, and collared cattle. A sign shows the mode, pump, levels, and whether the livestock are drinking. Drag to orbit if you want another angle. Leave this terminal running.

The world includes its props as `model://<name>`. `launch_gui.sh` puts every folder under `simulation/models/` on `GZ_SIM_RESOURCE_PATH`; a bare `gz sim simulation/worlds/ddroid_water_point.sdf` without that path cannot find them.

Without a window, `python3 tools/snapshot_world.py <label>` starts the world headless and saves one frame from the overview camera and one from the drink camera into `simulation/frames/`.

## 5. Run the ROS 2 demonstration

In a second Ubuntu terminal, from the repository root:

```bash
bash scripts/run_ros_demo.sh --gazebo
```

The first run builds `ros2_ws`. The node then publishes while the story runs:

1. Startup is STOPPED and the pump is OFF.
2. Arming a low trough starts REFILLING until FULL, then IDLE.
3. Drinking through ADEQUATE does not start the pump again. The next LOW does.
4. That refill crosses the supply-low switch and latches LOW SUPPLY. Reset is rejected until the supply is topped up.
5. After reset and arm, a second refill completes.
6. A safety drill holds the pump on until the independent high cutoff removes pump drive.
7. After the cutoff dries, reset returns STOPPED and arm leaves the machine IDLE.

Watch the middleware from a third terminal:

```bash
source /opt/ros/lyrical/setup.bash
source ros2_ws/install/setup.bash
ros2 topic echo /ddroid/status
```

Other topics: `/ddroid/mode`, `/ddroid/pump`, `/ddroid/fault`, `/ddroid/trough_state`, `/ddroid/supply_state`, `/ddroid/trough_litres`, `/ddroid/supply_litres`.

Each cow wears a collar. A camera at the trough reads that collar while the cow drinks, and the same collar is the GPS fix. `/ddroid/intake` is litres per animal. `/ddroid/gps` is the collar position in metres.

Without a window, omit `--gazebo`:

```bash
bash scripts/run_ros_demo.sh
```

`bash scripts/verify_ros.sh` rebuilds the package, reruns the controller checks, and prints one `/ddroid/status` message.

## 6. Operator commands

Stop the demo and start the command node instead. Gazebo can already be running.

```bash
source /opt/ros/lyrical/setup.bash
source ros2_ws/install/setup.bash
export GZ_PARTITION=ddroid
export DDROID_SIM="$PWD/simulation"
ros2 run ddroid_water_point ddroid_controller --gazebo
```

From another terminal:

```bash
ros2 topic pub --once /ddroid/command std_msgs/msg/String "{data: arm}"
```

Accepted commands are `arm`, `stop`, `reset`, `acknowledge`, `manual`, and `topup`.

## What the code does

- `simulation/ddroid_control.py` is the plant and the STOPPED / IDLE / REFILLING / MANUAL / FAULT state machine from the SRS. Float changes need two one-second samples. The high cutoff acts on the same step and drops pump drive even if software still asks for it.
- `simulation/ddroid_scene.py` holds the yard poses, collar colours, and the drink-camera gate.
- `simulation/ddroid_track.py` shares the water the herd drinks among the collar tags the trough camera picked, and keeps a GPS fix for every tag.
- `simulation/ddroid_demo.py` is the supervised story above.
- `simulation/build_world.py` writes the model folders and `simulation/worlds/ddroid_water_point.sdf`. It refuses to write a world in which any prop other than a collar has a colour the drink camera would read as a collar tag.
- `simulation/run_sim.py` moves the cattle, water slices, switch markers, and lamps in Gazebo, and reads `drink_cam`.
- `ros2_ws/src/ddroid_water_point` is the ROS 2 package that publishes that state and accepts commands.
- `tools/render_intake_clip.py` writes `media/intake_demo.mp4` (needs Pillow and `ffmpeg`).
- `tools/build_guide.py` writes `docs/DDROID_how_the_project_works.pdf` (needs reportlab).
- `tools/snapshot_world.py` saves headless camera frames, see section 4.
- `tools/windows/` holds PowerShell helpers that screenshot the Gazebo window from the Windows side.

Regenerate the world after a geometry change:

```bash
python3 simulation/build_world.py
```
