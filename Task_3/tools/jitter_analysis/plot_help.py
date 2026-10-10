"""Plain-English reading help shared by generated and existing dashboards.

Presentation only: never changes traces, metrics or simulation settings.
"""
import html
import json
import os
from pathlib import Path
import re


def box(image, content):
    return (f'<aside class="plot-help" id="help-{Path(image).stem}" style="background:#f1f6fc;border-left:4px solid #1760a5;'
            f'padding:16px;margin:12px 0 24px;line-height:1.6"><strong>How to read this plot — simple English</strong>{content}</aside>')


def reading_intro(m, s, page_dir):
    vx = m["command_vector"][0] if "command_vector" in m else m["vx"]
    stand, ramp = m["stand"], m["ramp"]
    full = stand + ramp
    schedule = (f'For the first {stand:g} seconds the requested speed is zero. '
                f'From {stand:g} to {full:g} seconds it gradually rises to {vx:g} m/s '
                f'({vx*100:g} cm/s), then stays at that speed until the run stops.')
    if ramp == 0:
        schedule = f'The requested speed is zero until {stand:g} seconds, then {vx:g} m/s until the run stops.'
    if "command_vector" in m:
        schedule = (f'For the first {stand:g} seconds all speed requests are zero. '
                    f'Over the next {ramp:g} seconds they ramp to '
                    f'[vx, vy, yaw rate] = {html.escape(str(m["command_vector"]))} '
                    '(m/s, m/s, rad/s), then stay constant until the run stops.')
    marker = ('There is no stair-contact line in this run.' if s["first_stair_contact_s"] is None
              else f'The red vertical dotted line marks the first loaded foot/stair contact at {s["first_stair_contact_s"]:.3f} simulation seconds.')
    outcome = {
        "flat_completed": "The flat-ground test finished its time limit without triggering a failure stop. You still need to check speed, direction and shaking.",
        "timeout_incomplete": "The stair test reached its time limit without completing the staircase.",
        "lane_exit": "A foot stayed outside the stair lane long enough to trigger a stop.",
        "tip": "The body stayed tilted beyond 60 degrees long enough to trigger a stop.",
        "low_body": "The body stayed too close to the surface underneath it, triggering a stop.",
        "traversed": "All four feet reached the top region while the recorded balance and lane checks were satisfied.",
        "error": "The recording stopped with an execution error; check status.json.",
    }.get(s["outcome"], "Read status.json for the recorded outcome.")
    guide = os.path.relpath(Path(__file__).resolve().parents[2] / "notes/15_HOW_TO_READ_THE_PLOTS.md", Path(page_dir).resolve())
    return ('<aside id="reading-help-intro" style="background:#eef3fa;padding:18px;margin:18px 0;line-height:1.6">'
            '<h2>Start here</h2><p><b>command vx = the forward speed we ask the robot to achieve.</b> '
            + schedule + ' It is a request, not a measured result.</p>'
            '<p>We hold the request steady so we can compare policies under the same task. '
            'The policy still changes its twelve joint actions to move the legs and respond to the robot\'s state.</p>'
            f'<p><b>Outcome:</b> {html.escape(outcome)} {marker}</p>'
            '<p>Most horizontal axes show simulation time in seconds. The foot-path and frequency plots use different axes, explained below. '
            f'<a href="{html.escape(guide, quote=True)}">Saved reading guide</a></p></aside>')


def plot_explanation(image, m=None, s=None, metrics=None):
    if image == "01_motion.png":
        content = '''<p><b>Start with the second panel: the speed graph.</b></p>
<table><tr><th>Line</th><th>Meaning</th></tr>
<tr><td>Black: command vx</td><td>The requested forward speed. 0.30 m/s means “walk forward at 30 cm every second.”</td></tr>
<tr><td>Blue: body-frame vx</td><td>The measured speed along the robot body's own forward direction. Compare this with the black request.</td></tr>
<tr><td>Orange: world vx</td><td>The measured speed along the scene's fixed x direction, which is the staircase direction in these tests.</td></tr></table>
<p>If blue is 0.15 while black is 0.30, the robot is moving forward at half the requested speed at that moment. A brief blue peak near black does not establish good average tracking. Blue/orange dips and peaks can come from stepping, impacts or instability; this plot alone does not prove motor jitter.</p>
<p>If the robot turns, its own “forward” can point away from the staircase. For example, moving at 0.30 m/s along its body direction while facing 90 degrees away can give almost zero speed along world x. The heading and lateral plots help explain a gap between blue and orange.</p>
<table><tr><th>Panel, from top to bottom</th><th>What to read</th><th>What to ask</th></tr>
<tr><td>1. Progress</td><td>base x is body position in the scene, in metres. Starting at −1.5 means 1.5 m before the first riser, not negative speed.</td><td>Does it keep moving toward the top, stall, or move back? Base position alone does not prove all feet climbed.</td></tr>
<tr><td>2. Speed</td><td>Black request versus blue/orange measured speeds.</td><td>Is actual speed near the request for most of the moving interval?</td></tr>
<tr><td>3. Height</td><td>world z is body height above the scene reference. The other line subtracts the terrain height under the body's x/y. They overlap on flat ground at z=0.</td><td>Does the body stay above the terrain? 0.34 m means 34 cm. Read the small axis range before judging the size of a wobble. The surface-under-body line can jump at a stair edge.</td></tr>
<tr><td>4. Angles</td><td>tilt means leaning away from upright; heading means the direction the robot faces. Both are degrees.</td><td>Is it leaning/falling, or turning while staying upright? Those are different problems. Requested yaw rate is zero here, so continuing heading drift is unwanted.</td></tr>
<tr><td>5. Lateral offset</td><td>How far sideways the body is from the lane center, in metres.</td><td>Is it drifting sideways despite zero sideways command?</td></tr></table>'''
        if metrics:
            phase = metrics.get("phases", {}).get("motion_all")
            if phase and phase["mean_vx_body"] is not None:
                end = phase["start_s"] + phase["duration_s"]
                content += (f'<p><b>This run:</b> during {phase["start_s"]:.2f}–{end:.2f} s, '
                            f'mean body-forward speed is <b>{phase["mean_vx_body"]:.3f} m/s</b> '
                            f'for a <b>{(m["command_vector"][0] if "command_vector" in m else m["vx"]):.2f} m/s</b> forward request. Maximum tilt over the whole run is '
                            f'{metrics["max_tilt_deg"]:.2f}°; ending heading is {metrics["final_yaw_deg"]:.2f}°. '
                            'These describe this recorded run, not a general success rate.</p>')
        return box(image, content)
    descriptions = {
        "02_angles.png": '''<p>Each small graph is one joint: FL/FR = front-left/front-right; RL/RR = rear-left/rear-right. Columns are hip, thigh and calf. Horizontal axis: time. Vertical axis: angle in degrees.</p><ul><li><b>Green, requested:</b> the policy's angle request before the final joint-target limit.</li><li><b>Orange, clamped target:</b> the angle actually sent to the PD controller after that limit.</li><li><b>Blue, measured q:</b> where the joint actually is in this simulation.</li></ul><p>A green/orange gap means a limit removed part of the request. An orange/blue gap means the joint is not at its target at that moment. That can involve response time, load or contact; it does not automatically mean a damaged motor. The stairs/no-stairs comparison and torque plot help narrow it down. Negative angles are the model's coordinate convention, not “negative performance.”</p>''',
        "03_torques.png": '''<p>Torque is the turning effort applied to a joint, measured in Nm. Each panel is one joint; horizontal axis is time.</p><ul><li><b>Unlimited PD torque:</b> the effort the controller calculates from position/velocity error before limiting.</li><li><b>Applied torque:</b> the effort actually applied after limiting.</li><li><b>Gray horizontal lines:</b> the positive and negative effort limits.</li></ul><p>When calculated and applied traces separate at a boundary, torque is clipped. Overlapping traces mean no clipping there, although both colors may not be visible. Positive and negative torques turn in opposite coordinate directions; negative does not mean weak or bad. Inspect the critical collision interval, not only the whole-run average.</p>''',
        "04_contacts.png": '''<p>Colors identify FL, FR, RL and RR feet. Read the three panels together.</p><ol><li><b>Foot normal force, N:</b> force pushing between each foot and the surfaces it touches. Near zero means little/no loaded foot contact. This total can include a wall-like riser, so force alone does not prove useful upward support.</li><li><b>Riser normal force, N:</b> the foot pushing against a nearly vertical step face. Repeated peaks mean repeated loaded riser contact.</li><li><b>Clearance, m:</b> the bottom of the modeled foot above the terrain under its center. Positive means above that surface; near zero means close to it. At a step edge this height calculation can jump.</li></ol><p>Find which foot meets the riser, whether other feet are supporting the body, and whether tilt rises afterwards. Small negative clearance can reflect soft-contact penetration or the height definition; it does not by itself prove a simulation failure. Normal walking also has landing-force peaks.</p>''',
        "05_feet.png": '''<p>This is a side-view projection of each foot's path. Horizontal axis is world foot x position; vertical axis is foot-center height z, both in metres. The black outline is the staircase in stair cases. Dot color shows simulation time: follow the color bar to see earlier and later positions.</p><p>Look for a foot moving forward at low height near a riser, then lifting or retreating. The foot is a sphere of radius 2.2 cm, so its center needs roughly 12.2 cm height to clear a 10 cm flat top. Sideways motion is hidden in this projection: a drawn intersection is not proof of collision. Confirm using the named contact records and contact-force plot.</p>''',
        "06_policy.png": '''<p>These are diagnostic values calculated from the recorded trajectory. They are not the total training reward.</p><ol><li><b>Action first-difference cost:</b> how much policy actions change between successive updates. <b>Target second-difference cost:</b> how abruptly the increments of the final position targets change. Peaks mean more abrupt changes, not automatically measured shaking.</li><li><b>Saturation cost:</b> how much requested angle is removed by target limits. Zero means no angle was removed; higher values mean a larger removed request.</li><li><b>Gyro stale/fresh difference:</b> disagreement between the controller's existing angular-velocity reading and a refreshed reading of the same state. It is a discrepancy in rad/s, not a plot of measured delay.</li><li><b>Soft expert weights:</b> how much each of eight experts contributes. All contribute continuously; changing curves do not imply hard switching between experts.</li></ol><p>Costs here are unweighted. For example, a plotted cost of 5 with reward weight −0.01 would contribute −0.05 before any reward-manager timestep scaling. We did not train in these evaluation runs. Read costs alongside measured motion and task outcome; a lower cost alone is not a successful gait.</p>''',
        "07_spectra.png": '''<p>This plot shows <b>how fast the signal repeats</b>, not when an event happened. Horizontal axis is frequency in Hz: 10 Hz means ten cycles per second. Vertical axis shows signal power at each frequency; the scale is logarithmic, so equal vertical spacing represents multiplication.</p><p>Left: measured joint motion sampled at 200 Hz, with the 8–30 Hz band highlighted. Right: target angles at 50 Hz policy updates, with the 8–20 Hz band highlighted. Blue/orange distinguish approach and the interval after first contact when those phases are available. On a flat run there is no after-contact phase.</p><p>More power in the highlighted band means more rapid motion there. RMS summarizes its typical size in degrees; it is not the maximum joint angle or the full walking swing. Compare the same band and phase between runs. The two panels use different bands and their amplitudes are not an equal-band comparison. Impacts can also add rapid signal components.</p>''',
        "08_first_contact.png": '''<p>This zooms in on the first foot meeting a step. Red vertical line = first loaded contact. The six panels show foot height, foot forward position, contact force, body angles, contacting-leg joint angles and torque.</p><p>In the foot-height panel, blue is the measured foot center. Orange is a <b>static geometry check</b>: freeze the recorded body pose and set joints to their current targets. It is not a prediction of where the moving robot will go. The black horizontal height is the first step top plus foot radius.</p><p>Ask: was the foot high enough before reaching the riser? Did the target ask for lift? Did measured movement follow it? Was target/torque limiting active at that instant? Did the body begin to lean or turn after the collision? A low first touch does not prove the policy can never recover and climb.</p>''',
        "09_flat_comparison.png": '''<p>Two runs use the same saved policy, commands, starting pose and observation mode. Stair collisions are enabled in one and disabled in the flat comparison. Horizontal zero is the first stair-contact time in the stair run, not the simulation start.</p><p>Top: forward body position. Middle: body tilt. Bottom: target second-difference cost. Follow where flat/stair curves begin to separate. This controlled comparison tests the stair geometry's effect on the whole feedback loop. It does not alone identify whether policy responses, actuators or contact parameters are responsible.</p>''',
        "paired_starts.png": '''<p>Each colored line connects the original and candidate results for the <b>same starting pose</b>. Start 0 is centered; start 1 uses −3 cm sideways and −0.02 rad yaw; start 2 uses +3 cm and +0.02 rad. Dashed black is the arithmetic mean of those three cases.</p><p>Columns: measured rapid joint motion, forward speed error, and fraction of joint-samples whose targets were limited. For these three quantities, a lower number is usually desirable, but only alongside useful walking and stair traversal. A line going up toward the candidate means that quantity worsened for that start. Top row uses existing viewer timing; bottom uses refreshed observations. All numbers use the same 4–8 s early-motion interval. Three poses do not establish statistical reliability or a general success rate.</p>''',
    }
    return box(image, descriptions[image]) if image in descriptions else ""


def refresh_page(path):
    """Add/update explanations in place without rerunning any experiment or plot."""
    path = Path(path)
    text = path.read_text()
    m = s = metrics = None
    if (path.parent / "manifest.json").exists():
        m = json.loads((path.parent / "manifest.json").read_text())
        s = json.loads((path.parent / "status.json").read_text())
        metrics = json.loads((path.parent / "metrics.json").read_text())
        if s["first_stair_contact_s"] is None:
            text = text.replace('; red dotted = first foot/stair contact', '; no stair contact recorded')
        text = text.replace('<p>Fresh scripted simulation, not a replay of the screen recording. First foot/stair contact is the red dotted line. A completed run can contain a task failure.</p>',
                            '<p>This page shows a fresh scripted simulation. The outcome and reading guide above explain whether a task failure occurred.</p>')
        text = re.sub(r'<aside id="reading-help-intro".*?</aside>', '', text, flags=re.S)
        text = re.sub(r'(</h1>)', lambda match: match[0] + reading_intro(m, s, path.parent), text, count=1)
    text = re.sub(r'<aside(?: class="plot-help")? id="help-[^"]+".*?</aside>', '', text, flags=re.S)
    pattern = r'(<a href="([^"]+\.png)"><img\b[^>]*></a>)'
    text = re.sub(pattern, lambda match: plot_explanation(match[2], m, s, metrics) + match[1], text)
    if '.plot-help table' not in text:
        text = text.replace('</style>', '.plot-help table{border-collapse:collapse;width:100%;margin:12px 0}.plot-help td,.plot-help th{border:1px solid #bdcddd;padding:8px;text-align:left}</style>', 1)
    path.write_text(text)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("root", type=Path)
    a = p.parse_args()
    pages = [a.root] if a.root.is_file() else sorted(a.root.rglob("index.html"))
    for page in pages: refresh_page(page)
    print(f"Added plain-English reading help to {len(pages)} existing dashboard pages; no simulations rerun.")
