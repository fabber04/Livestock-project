"""Write docs/DDROID_how_the_project_works.pdf."""

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "DDROID_how_the_project_works.pdf")

INK = colors.HexColor("#1c241c")
GREEN = colors.HexColor("#1f4d32")
GREEN_SOFT = colors.HexColor("#e7f0ea")
RULE = colors.HexColor("#c5d2c8")
CODE_BG = colors.HexColor("#f4f6f4")
MUTED = colors.HexColor("#4d5a50")
WHITE = colors.white


def styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(
        "CoverKicker", fontName="Times-Bold", fontSize=9, leading=12,
        textColor=GREEN, tracking=0.6, spaceAfter=4,
    ))
    base.add(ParagraphStyle(
        "CoverTitle", fontName="Times-Bold", fontSize=22, leading=26,
        textColor=INK, spaceAfter=6,
    ))
    base.add(ParagraphStyle(
        "CoverSub", fontName="Times-Italic", fontSize=11, leading=15,
        textColor=MUTED, spaceAfter=8,
    ))
    base.add(ParagraphStyle(
        "H1", fontName="Times-Bold", fontSize=14, leading=18,
        textColor=GREEN, spaceBefore=12, spaceAfter=4,
    ))
    base.add(ParagraphStyle(
        "Body", fontName="Times-Roman", fontSize=10.5, leading=14.5,
        textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6,
    ))
    base.add(ParagraphStyle(
        "BulletBody", fontName="Times-Roman", fontSize=10.5, leading=14,
        textColor=INK, alignment=TA_LEFT,
    ))
    base.add(ParagraphStyle(
        "Cell", fontName="Times-Roman", fontSize=9, leading=12, textColor=INK,
    ))
    base.add(ParagraphStyle(
        "CellHead", fontName="Times-Bold", fontSize=9, leading=12, textColor=WHITE,
    ))
    base.add(ParagraphStyle(
        "Mono", fontName="Courier", fontSize=8, leading=10.5, textColor=INK,
    ))
    base.add(ParagraphStyle(
        "FooterNote", fontName="Times-Italic", fontSize=9, leading=12,
        textColor=MUTED, spaceBefore=4,
    ))
    return base


S = styles()


def P(text):
    return Paragraph(text, S["Body"])


def H(text):
    return Paragraph(text, S["H1"])


def bullets(items):
    flow = []
    for item in items:
        flow.append(ListItem(Paragraph(item, S["BulletBody"]), leftIndent=8))
    return ListFlowable(flow, bulletType="bullet", start="•", leftIndent=14, bulletFontName="Times-Roman", bulletFontSize=10, spaceBefore=1, spaceAfter=6)


def table(headers, rows, col_widths):
    head = [Paragraph(h, S["CellHead"]) for h in headers]
    body = [[Paragraph(str(cell), S["Cell"]) for cell in row] for row in rows]
    data = [head] + body
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7faf8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f7faf8"), WHITE]),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.3, RULE),
    ]))
    return tbl


def code(text):
    return Preformatted(text.rstrip() + "\n", S["Mono"])


# Names and roles as listed in docs/DDROID_SRS.pdf.
TEAM = (
    ("Tapiwa Chigome", "Project Manager"),
    ("Fabilous Lashid", "Software Engineer"),
    ("Tanatswa Bernard Nyautore", "Systems Engineer"),
    ("Tinotenda Gozi", "Network Engineer"),
    ("Praise Muzvonda", "Programmer 1"),
    ("Nickson Gondwe", "Programmer 2"),
    ("Claris Chinanga", "Test Programmer"),
    ("Divine Pezari", "Database Administrator"),
    ("Lionel Tadiwanashe Tiugari", "AI/ML Engineer"),
    ("Keith Tawananyasha Mutabvuri", "Chief Security Officer"),
)


def decorate(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(GREEN)
    canvas.rect(0, height - 11 * mm, width, 11 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Times-Bold", 8.5)
    canvas.drawString(16 * mm, height - 7 * mm, "DDROID   Smart Livestock Watering and Monitoring")
    canvas.setFillColor(colors.HexColor("#5c6b60"))
    canvas.setFont("Times-Roman", 8.5)
    canvas.drawString(16 * mm, 8 * mm, "DDROID Project Team, Group 4  |  NUST BSc Hons Computer Science, Second Year Group Project")
    canvas.drawRightString(width - 16 * mm, 8 * mm, str(doc.page))
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(16 * mm, 12 * mm, width - 16 * mm, 12 * mm)
    canvas.restoreState()


def build():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc = SimpleDocTemplate(
        OUT, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=18 * mm, bottomMargin=16 * mm,
        title="How the DDROID project works",
        author="DDROID Project Team (Group 4), NUST",
    )
    usable = A4[0] - 32 * mm
    story = []

    story.append(Paragraph("HOW THE PROJECT WORKS", S["CoverKicker"]))
    story.append(Paragraph("DDROID livestock water point", S["CoverTitle"]))
    story.append(Paragraph(
        "A stationary controller fills a drinking trough, latches faults, and records how much water each collared cow drank. Gazebo is the yard. ROS 2 carries status and operator commands.",
        S["CoverSub"],
    ))
    story.append(Paragraph(
        "DDROID Project Team, Group 4 &nbsp;&nbsp; National University of Science and Technology, "
        "BSc Hons Computer Science, Second Year Group Project &nbsp;&nbsp; 22 October 2026",
        S["FooterNote"],
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN, spaceAfter=6))
    half = (len(TEAM) + 1) // 2
    story.append(table(
        ["Team member", "Role", "Team member", "Role"],
        [
            [*TEAM[index], *(TEAM[index + half] if index + half < len(TEAM) else ("", ""))]
            for index in range(half)
        ],
        [50 * mm, 36 * mm, 56 * mm, usable - 142 * mm],
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(H("1. What the system is"))
    story.append(P(
        "DDROID is a prototype of a smart livestock water point. One machine sits beside a storage tank and a concrete trough. Float switches tell it whether the trough is low, full, or over the safety line, and whether the storage tank still has water. A low-voltage pump moves water from the tank into the trough. Cattle drink from the trough when the pump is off."
    ))
    story.append(P(
        "The controller is an ESP32-style state machine: STOPPED, IDLE, REFILLING, MANUAL, and FAULT. It does not depend on a dashboard. If the link to an operator is lost, the machine on the bench still owns the pump. ROS 2 only publishes that state and accepts commands. Gazebo draws the same numbers as moving water, lamps, and cattle."
    ))
    story.append(P(
        "A second function sits on top of the watering cycle. Each animal wears a collar. A camera at the trough reads the collar colour of the cows that are drinking, and the litres that left the trough are shared across those collars. The same collar position is the GPS fix."
    ))

    story.append(H("2. How a run is organised"))
    story.append(P("Three programs cooperate. They share one clock of 0.1 second steps."))
    story.append(bullets([
        "<b>Plant and controller</b> (<font face='Courier' size='9'>simulation/ddroid_control.py</font>). The plant holds the two water volumes and moves them. The controller reads the switches and decides whether the pump may run.",
        "<b>Herd ledger</b> (<font face='Courier' size='9'>simulation/ddroid_track.py</font>). After each step it takes the litres just drunk and credits them to the collars the camera picked. It also stores each collar’s x, y.",
        "<b>View</b> (<font face='Courier' size='9'>simulation/run_sim.py</font>). If Gazebo is running, this moves the water slices, lamps, markers, and cattle, and reads the trough-camera image.",
    ]))
    story.append(P(
        "The supervised story in <font face='Courier' size='9'>simulation/ddroid_demo.py</font> calls the controller, then the plant, then the herd ledger, then the view. The ROS 2 node does the same work and publishes the result. Headless runs skip the view. The litre totals are still recorded."
    ))

    story.append(H("3. The water plant"))
    story.append(P(
        "There are two vessels. The storage tank holds 18 litres and starts at 12.3 litres. The trough holds 10 litres and starts at 1.2 litres, which is below the low switch, so the first arm starts a refill. A top-up command sets the tank to 14.0 litres."
    ))
    story.append(P(
        "When the controller asks for the pump, and the high-cutoff switch is dry, water moves from the tank to the trough at 0.40 litres per second. The move stops early if the tank is empty, the trough is full to its capacity, or the level reaches the cutoff. Reaching the cutoff also drops pump drive on that same step, even if software still asks for the pump."
    ))
    story.append(P(
        "When the pump is off and the trough is not empty, the herd drinks at 0.32 litres per second. That single rate is the whole herd, not one cow. The amount removed on a step is saved as <font face='Courier' size='9'>last_drunk_l</font>. While the pump is on, that value is zero, so no cow is credited."
    ))

    story.append(H("4. Float switches"))
    story.append(P(
        "Switch levels are fractions of each vessel. The names match the states the controller reports. The high cutoff is separate from the high switch: it is a hardware interlock, and it is not debounced."
    ))
    story.append(table(
        ["Switch", "Vessel", "Threshold", "Litres", "Meaning when wet"],
        [
            ["Trough low", "Trough", "30%", "3.0 L", "Above LOW"],
            ["Trough high", "Trough", "75%", "7.5 L", "FULL, if low is also wet"],
            ["Trough cutoff", "Trough", "92%", "9.2 L", "HIGH CUTOFF, immediate"],
            ["Supply low", "Tank", "20%", "3.6 L", "Supply AVAILABLE"],
        ],
        [28 * mm, 22 * mm, 24 * mm, 22 * mm, usable - 96 * mm],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(P("The debounced trough state is one of four words:"))
    story.append(bullets([
        "<b>LOW</b> when the low switch is dry.",
        "<b>ADEQUATE</b> when the low switch is wet and the high switch is dry. Drinking through this band does not start the pump.",
        "<b>FULL</b> when both trough switches are wet. A refill stops and the mode becomes IDLE.",
        "<b>SENSOR FAULT</b> when the high switch is wet and the low switch is dry. That combination is impossible for a real water surface, so it latches a fault.",
    ]))
    story.append(P(
        "Low, high, and supply changes are accepted only after two samples taken one second apart. A single splash does not change the state. The cutoff switch is read every step and latches HIGH CUTOFF immediately. In Gazebo each vessel is drawn as 16 horizontal slices, so the visible surface steps with the litres."
    ))

    story.append(H("5. The controller"))
    story.append(P(
        "The machine starts in STOPPED with the pump off. <font face='Courier' size='9'>arm</font> is accepted only from STOPPED, and only when the inputs are safe: cutoff dry, supply available, no sensor fault, and no latched fault. If the trough is LOW, arm enters REFILLING and the pump runs. Otherwise arm enters IDLE and the pump stays off."
    ))
    story.append(P(
        "REFILLING runs until the trough state is FULL, then returns to IDLE and stops the pump. If a refill lasts 60 seconds it latches PUMP TIMEOUT. From IDLE, the next time the debounced state is LOW, and the inputs are still safe, the pump starts again by itself. ADEQUATE never starts a refill."
    ))
    story.append(P(
        "<font face='Courier' size='9'>manual</font> is also only from STOPPED, with the same safety checks, and it is refused if the trough is already FULL. MANUAL runs the pump for at most 15 seconds, or until FULL, and then returns to STOPPED rather than IDLE. <font face='Courier' size='9'>stop</font> from a normal mode returns to STOPPED and clears the run timers. From FAULT it only forces the pump off; the fault stays latched."
    ))
    story.append(P(
        "<font face='Courier' size='9'>acknowledge</font> marks a fault as seen. It does not clear it. <font face='Courier' size='9'>reset</font> is accepted only in FAULT, and only after the cause has gone:"
    ))
    story.append(bullets([
        "LOW SUPPLY cannot be reset while the supply switch is still dry.",
        "SENSOR FAULT cannot be reset while the high switch is wet and the low switch is dry.",
        "HIGH CUTOFF cannot be reset while the cutoff switch is still wet.",
    ]))
    story.append(P("A successful reset returns the machine to STOPPED with the pump off. Another arm is required before it will idle or refill."))

    story.append(H("6. Faults"))
    story.append(table(
        ["Fault", "When it latches", "Pump"],
        [
            ["HIGH CUTOFF", "Cutoff switch is wet. Same step, no debounce.", "Drive removed immediately"],
            ["LOW SUPPLY", "Supply switch is dry, after debounce.", "Off"],
            ["SENSOR FAULT", "High wet and low dry, after debounce.", "Off"],
            ["PUMP TIMEOUT", "REFILLING has run for 60 seconds.", "Off"],
        ],
        [32 * mm, 78 * mm, usable - 110 * mm],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(P(
        "Any fault forces the software pump request off. The plant applies a second check: even if something outside the state machine forces the pump, a wet cutoff removes hardware drive and clamps the trough at the cutoff level."
    ))

    story.append(H("7. The yard"))
    story.append(P(
        "The Gazebo world is <font face='Courier' size='9'>simulation/worlds/ddroid_water_point.sdf</font>. Props are not written out in full inside that file. Each prop is a model under <font face='Courier' size='9'>simulation/models</font>, and the world places it with an include of the form <font face='Courier' size='9'>model://name</font>. <font face='Courier' size='9'>scripts/launch_gui.sh</font> adds each group folder to <font face='Courier' size='9'>GZ_SIM_RESOURCE_PATH</font>, which is how Gazebo finds them; Gazebo 10 resolves a plain relative path from the directory it was started in, not from the world file."
    ))
    story.append(table(
        ["Folder", "What it holds"],
        [
            ["Trees", "A flat-topped acacia, used for the shade tree in the kraal and four outside it."],
            ["Cattle", "One rounded cow model per coat. Each includes that animal’s collar."],
            ["Kraal", "A gum-pole post, three rail lengths for the three-rail fence, and a gate leaf."],
            ["Yard", "Grass, the dirt pad, trampled mud at the trough, the gate track, rocks, and grass tufts."],
            ["Water", "Storage tank, trough, plinth, pipe, and one water-slice model per vessel."],
            ["Controls", "Pump, controller cabinet, solar panel, pump and mode lamps, and float-switch markers."],
            ["Sign", "The status board under a small roof, on two posts."],
            ["Cameras", "The drink camera on a post at the east end of the trough."],
        ],
        [28 * mm, usable - 28 * mm],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(P(
        "<font face='Courier' size='9'>python3 simulation/build_world.py</font> rewrites both the model folders and the world. Geometry numbers live in <font face='Courier' size='9'>ddroid_scene.py</font>, so the drawing and the controller stay on the same trough. The builder refuses to write a world in which any prop other than a collar has a colour the drink camera would take for a collar tag."
    ))
    story.append(P(
        "An overview camera looks down on the kraal from the south-east. A sign at the south gate shows mode, pump, trough state and litres, supply state and litres, whether the herd is drinking, and the fault. A second text board beside the drink camera lists litres and the collar position for C1 to C5. The mode lamp sits on top of the controller cabinet beside the pump, and the pump lamp sits above the pump. Both are glowing spheres that are parked underground when they are off, and moved into place when they are on."
    ))

    story.append(H("8. Collars, the camera, and GPS"))
    story.append(P(
        "Nine animals wear collars. Five drink (C1 to C5). Four walk closed paths inside the kraal (W1 to W4) and stay clear of the trough. The collar is a band and a coloured plate on the right side of the neck, plus a small puck on top. Nothing is pierced or implanted. Each plate has its own saturated colour so it can be told apart from hides, dirt, concrete, and water."
    ))
    story.append(P(
        "The drink camera stands at the east end of the trough and looks west along the south lip. Its view is a box around collar height at that lip. While the herd is drinking, two of the five cows stand in that box. The pair changes every 6 seconds, rotating through the herd, so the totals come out different. Cows that are waiting stand back at their rest poses. The walkers keep moving the whole time."
    ))
    story.append(P(
        "GPS for every animal is the world position of that collar plate, in metres. It is published even when the animal is not drinking. On the board and on <font face='Courier' size='9'>/ddroid/gps</font> the form is <font face='Courier' size='9'>cow_1:0.27,-0.23</font>."
    ))

    story.append(H("9. How intake is measured"))
    story.append(P(
        "There is no flow meter on each mouth. Intake is the drop in the trough, shared across the collars that are actually at the lip."
    ))
    story.append(P(
        "Each 0.1 second step, if the pump is off and the trough still has water, the plant removes up to 0.32 × 0.1 litres and stores that exact drop. The herd ledger then chooses who was drinking:"
    ))
    story.append(bullets([
        "The latest drink-camera frame is scanned for collar colours. A colour counts when enough pixels are close to that tag and clearly saturated, so grey concrete and brown hides are ignored.",
        "A cow is credited only if that colour was seen <b>and</b> the collar is inside the camera’s view box. A colour reported for an animal elsewhere in the kraal is ignored.",
        "The step’s litres are divided equally by the number of collars that pass both checks.",
        "If the camera frame is missing, or none of its colours match a collar at the lip, the litres are shared by every collar that is physically inside the view. The log then says <font face='Courier' size='9'>tag</font> instead of <font face='Courier' size='9'>camera</font>.",
    ]))
    story.append(P(
        "Two cows at the lip for one second therefore each receive 0.16 litres. The running total is <font face='Courier' size='9'>/ddroid/intake</font>, for example <font face='Courier' size='9'>cow_1:1.500,cow_2:0.540,...</font>, including the walkers at 0. A top-down clip of this behaviour is <font face='Courier' size='9'>media/intake_demo.mp4</font>. Regenerate it with <font face='Courier' size='9'>python tools/render_intake_clip.py</font>."
    ))

    story.append(H("10. The supervised demonstration"))
    story.append(P(
        "<font face='Courier' size='9'>ddroid_demo.py</font> drives one full story from controller events, not from a fixed script of seconds. Debounce and pump timing can change without breaking the sequence. The steps are:"
    ))
    story.append(bullets([
        "Startup is STOPPED and the pump is off. The trough is already LOW.",
        "Arm starts REFILLING. The refill runs until FULL, then the mode is IDLE.",
        "The herd drinks through ADEQUATE. The pump stays off. The next LOW starts another refill.",
        "That second refill crosses the supply-low switch and latches LOW SUPPLY. Reset is rejected while the supply is still low.",
        "The operator tops the tank up to 14 litres. After the supply switch is wet, reset returns STOPPED and arm enters IDLE.",
        "The trough is refilled again.",
        "A safety drill forces the pump on past the high switch. The independent cutoff latches HIGH CUTOFF and removes pump drive.",
        "After the cutoff dries, reset returns STOPPED and arm leaves the machine IDLE. The pump stays off until the trough is LOW again.",
    ]))
    story.append(P(
        "<font face='Courier' size='9'>python3 test_control.py</font> runs that story without Gazebo and checks the event order, the rejected reset, both faults, and the per-cow split of the litres."
    ))

    story.append(H("11. ROS 2"))
    story.append(P(
        "The package <font face='Courier' size='9'>ddroid_water_point</font> does not reimplement the state machine. It imports the simulation modules and publishes their state. Two executables are installed: <font face='Courier' size='9'>ddroid_demo</font> runs the story, and <font face='Courier' size='9'>ddroid_controller</font> waits for operator commands. Pass <font face='Courier' size='9'>--gazebo</font> to either one to drive a Gazebo session that is already running on the <font face='Courier' size='9'>ddroid</font> partition."
    ))
    story.append(table(
        ["Topic", "Type", "Contents"],
        [
            ["/ddroid/status", "String", "One line: mode, pump, both vessels, fault"],
            ["/ddroid/mode", "String", "STOPPED, IDLE, REFILLING, MANUAL, or FAULT"],
            ["/ddroid/pump", "Bool", "True while hardware pump drive is on"],
            ["/ddroid/fault", "String", "Latched fault, or empty"],
            ["/ddroid/trough_state", "String", "LOW, ADEQUATE, FULL, or SENSOR FAULT"],
            ["/ddroid/supply_state", "String", "AVAILABLE or LOW"],
            ["/ddroid/trough_litres", "Float32", "Trough volume"],
            ["/ddroid/supply_litres", "Float32", "Tank volume"],
            ["/ddroid/intake", "String", "Litres credited to each collar"],
            ["/ddroid/gps", "String", "Collar x, y in metres for each animal"],
            ["/ddroid/command", "String", "arm, stop, reset, acknowledge, manual, topup"],
        ],
        [42 * mm, 22 * mm, usable - 64 * mm],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(P(
        "Commands are accepted only by the controller node, not during the scripted demonstration. <font face='Courier' size='9'>topup</font> sets the tank to 14 litres. Unknown text is rejected with a short reason."
    ))

    story.append(H("12. How to run it"))
    story.append(P(
        "This copy runs on Windows with WSL2. The guest is Ubuntu 26.04, Gazebo is Jetty (<font face='Courier' size='9'>gz sim</font> 10), and ROS 2 is Lyrical. Gazebo uses the NVIDIA GeForce GTX 1650 through WSLg. The launch script selects that adapter so the Intel chip is left unused. Install steps for a new machine are in the repository README."
    ))
    story.append(Paragraph("Controller check, from simulation/ inside Ubuntu:", S["Body"]))
    story.append(code("cd simulation\npython3 test_control.py"))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("Open the yard and leave that terminal running:", S["Body"]))
    story.append(code("bash scripts/launch_gui.sh"))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("In a second terminal, from the repository root, run the story into that window:", S["Body"]))
    story.append(code("bash scripts/run_ros_demo.sh --gazebo"))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("Omit --gazebo for the same story with no window. Watch the middleware from a third terminal:", S["Body"]))
    story.append(code(
        "source /opt/ros/lyrical/setup.bash\n"
        "source ros2_ws/install/setup.bash\n"
        "ros2 topic echo /ddroid/status"
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("Operator commands, with Gazebo already running:", S["Body"]))
    story.append(code(
        "source /opt/ros/lyrical/setup.bash\n"
        "source ros2_ws/install/setup.bash\n"
        "export GZ_PARTITION=ddroid\n"
        "export DDROID_SIM=\"$PWD/simulation\"\n"
        "ros2 run ddroid_water_point ddroid_controller --gazebo"
    ))
    story.append(Spacer(1, 1.5 * mm))
    story.append(code("ros2 topic pub --once /ddroid/command std_msgs/msg/String \"{data: arm}\""))
    story.append(Spacer(1, 2 * mm))
    story.append(P("<font face='Courier' size='9'>bash scripts/verify_ros.sh</font> rebuilds the package, reruns the controller checks, and prints one status message."))

    story.append(H("13. Where the code lives"))
    story.append(table(
        ["File", "Role"],
        [
            ["simulation/ddroid_scene.py", "Litres, switch levels, poses, collar colours, camera view."],
            ["simulation/ddroid_control.py", "Plant and the five-mode state machine."],
            ["simulation/ddroid_track.py", "Camera colour match, intake ledger, GPS."],
            ["simulation/ddroid_demo.py", "The supervised watering story."],
            ["simulation/run_sim.py", "Moves Gazebo and reads the drink camera."],
            ["simulation/build_world.py", "Writes the model folders and the world."],
            ["simulation/test_control.py", "Headless checks of the story and the intake split."],
            ["ros2_ws/.../demo_node.py", "Publishes state and accepts commands."],
            ["scripts/", "Install, launch, demo, and verify shell scripts."],
            ["tools/render_intake_clip.py", "Writes media/intake_demo.mp4."],
            ["tools/build_guide.py", "Writes this guide."],
            ["tools/snapshot_world.py", "Saves one headless frame from each camera."],
            ["docs/DDROID_SRS.pdf", "The group requirements specification."],
        ],
        [62 * mm, usable - 62 * mm],
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=0.6, color=RULE, spaceBefore=2, spaceAfter=4))
    story.append(Paragraph(
        "The watering rules are the device. The camera and the GPS collar explain which animal drank. Both use the same litres, so the trough level and the sum of the credited intakes stay in step.",
        S["FooterNote"],
    ))

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    print(OUT)


if __name__ == "__main__":
    build()
