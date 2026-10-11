#!/usr/bin/env python3
"""Build independent RL background and code-derived MoE architecture diagrams."""
from build_gqft_svg import start, box, text, save
import re
import math


def path(parts, d, dashed=False):
    # Explicit arrow polygons also render in ImageMagick's SVG rasterizer.
    parts.append(f'<path d="{d}" fill="none" stroke="#087f8c" stroke-width="3"' +
                 (' stroke-dasharray="8 6"' if dashed else '') + '/>')
    tokens = re.findall(r'[MHV]|-?[0-9.]+', d)
    points = []
    i = 0
    x = y = 0
    while i < len(tokens):
        command = tokens[i]
        if command == 'M':
            x, y = float(tokens[i+1]), float(tokens[i+2]); i += 3
        elif command == 'H':
            x = float(tokens[i+1]); i += 2
        elif command == 'V':
            y = float(tokens[i+1]); i += 2
        else:
            raise ValueError(d)
        points.append((x,y))
    px,py = points[-2]
    theta = math.atan2(y-py,x-px)
    ux,uy = math.cos(theta),math.sin(theta)
    ax,ay = x-12*ux+6*uy,y-12*uy-6*ux
    bx,by = x-12*ux-6*uy,y-12*uy+6*ux
    parts.append(f'<polygon points="{x},{y} {ax},{ay} {bx},{by}" fill="#087f8c"/>')


def rl_loop():
    p = start(1800, 810, 'Task 3 | Reinforcement learning for locomotion',
              'Training: interact with the simulator, measure rewards, update the policy')
    box(p, 55, 195, 345, 165, 'Robot observations',
        ['Joint state + body motion', 'Velocity command + history', 'What the policy observes'])
    box(p, 485, 195, 345, 165, 'Policy / actor',
        ['Maps observations to actions', 'Our student uses MoE features', '12 joint-target actions'], accent=True)
    box(p, 915, 195, 345, 165, 'Actuator + simulation',
        ['Scale / clamp joint targets', 'Coupled PD + torque limits', 'Robot motion and contacts'])
    box(p, 1345, 195, 400, 165, 'Evaluate the transition',
        ['Next robot observation', 'Tracking / stability rewards', 'Smoothness costs + termination'])
    for a,b in [(400,485),(830,915),(1260,1345)]: path(p,f'M {a+5} 278 H {b-6}')
    path(p,'M 1545 365 V 425 H 227 V 366')
    text(p,650,415,['Next observation closes the control loop'],22)
    box(p, 630, 505, 540, 150, 'Learner — training only',
        ['Use collected transitions to update weights', 'MoE-CTS also uses teacher/student losses', 'Optimize rewards; validate actual motion'], accent=True)
    path(p,'M 1545 431 V 580 H 1176',dashed=True)
    path(p,'M 630 580 H 445 V 150 H 657 V 189',dashed=True)
    text(p,55,731,['Deployment: observation → fixed learned policy → PD control. No online weight update is shown.'],24)
    text(p,55,773,['Lower reward costs alone do not establish better tracking, lower physical jitter or stair completion.'],22)
    save(p,'task3_rl_background.svg')


def moe_architecture():
    p = start(1800, 960, 'Task 3 | Student MoE architecture',
              'Code-derived inference graph: eight latent experts blended before one shared actor')
    box(p,55,390,310,165,'Observation history',
        ['5 frames × 45 features', 'Oldest → newest', 'Flattened input: 225-D'])
    box(p,440,200,410,175,'Expert feature branch',
        ['MLP: 225 → 512 → 256 → 2048', 'Grouped 1×1 Conv, groups = 8', '8 expert vectors × 32 features'])
    box(p,440,530,410,165,'Gating branch',
        ['MLP: 225 → 512 → 256 → 8', 'Softmax → weights w1...w8', 'Weights sum to one'],accent=True)
    path(p,'M 370 473 H 400 V 287 H 434')
    path(p,'M 400 473 V 613 H 434')
    box(p,940,390,345,185,'Weighted latent blend',
        ['z = sum_i wi * Ei(history)', 'L2-normalize blended vector', 'Output: 32-D latent'],accent=True)
    path(p,'M 856 287 H 903 V 448 H 934')
    path(p,'M 856 613 H 903 V 523 H 934')
    box(p,1370,390,375,185,'Shared actor',
        ['32-D latent + latest 45-D obs', '77 → 512 → 256 → 128 → 12', 'Output: 12 joint actions'])
    path(p,'M 1291 473 H 1364')
    path(p,'M 210 561 V 747 H 1557 V 581',dashed=True)
    text(p,610,734,['Latest observation bypass: 45 features'],22)
    box(p,1370,720,375,200,'Control execution',
        ['Hip target: ±0.735 rad', 'Calf upper: -0.88776 rad', 'Coupled PD + torque limits', 'Policy 50 Hz; PD 200 Hz'])
    path(p,'M 1761 473 H 1775 V 832 H 1751')
    text(p,55,835,['All experts contribute through soft weights; no hard one-expert selection.'],23)
    text(p,55,877,['Expert roles are learned features; walking/turning/stair identities are not established.'],22)
    text(p,55,923,['Source: svanm2_moe_stair_sim/checkpoint_policy.py and controller.py.'],21)
    save(p,'task3_moe_architecture.svg')


def contract_table():
    p = start(1600, 980, 'Task 3 | Hardware-contract corrections',
              'Simulator mismatches, corresponding corrections and implementation status')
    p.append('<rect x="55" y="160" width="1490" height="75" rx="12" fill="#12243a"/>')
    text(p,80,208,['Historical simulator mismatch'],28,'#ffffff',True)
    text(p,790,208,['Correction'],28,'#ffffff',True)
    rows = [
        (['Calf upper target: +0.50000 rad'],
         ['Correct upper target: -0.88776 rad', 'Difference: 1.38776 rad / 79.5 degrees'],
         'Present in current controller', '#007d79'),
        (['Hip targets: ±1.0472 rad'],
         ['Restore tighter hip targets: ±0.735 rad', 'Verify the full per-leg thigh bounds'],
         'Hip correction present in current controller', '#007d79'),
        (['Command shaping differed', 'from the deployed operator'],
         ['Reproduce deadzone, shared input budget,', 'slew and release in the audit simulator'],
         'Verified in audit; current-viewer parity incomplete', '#a15b08'),
        (['Sensor, reset and timing', 'conventions were inconsistent'],
         ['Refresh observations; clear full simulation', 'state; separate policy/PD rates and delay'],
         'Verified in audit; current viewer partly implements', '#a15b08'),
        (['Short pre-stair runs were used', 'as stair-performance evidence'],
         ['Check foot contact and full traversal;', 'retain stalls, lane exits and tips'],
         'Documented audit criteria; protocols kept separate', '#a15b08')]
    for i,(left,right,status,color) in enumerate(rows):
        y = 235 + i*126
        p.append(f'<rect x="55" y="{y}" width="1490" height="126" fill="{"#f4f7fb" if i%2==0 else "#ffffff"}"/>')
        p.append(f'<path d="M 55 {y+126} H 1545" stroke="#d7e0e9" stroke-width="1"/>')
        text(p,80,y+43,left,27,'#12243a',i<2)
        text(p,790,y+38,right,25,'#12243a')
        text(p,790,y+105,[status],19,color,True)
    p.append('<path d="M 760 160 V 865" stroke="#d7e0e9" stroke-width="1"/>')
    text(p,55,918,['Software target corrections; physical joint stops and firmware limits were not changed.'],24,'#526477')
    text(p,55,956,['Source: hardware-contract audit and current SvanM2 controller.'],21,'#526477')
    save(p,'task3_hardware_contract_table.svg')


def analysis_architecture():
    p = start(1800, 850, 'Task 3 | Analysis architecture',
              'Passive recording → contact-aligned diagnosis → controlled comparison')
    box(p,55,190,340,185,'Run + record',
        ['Interactive or scripted run', 'Each reset → separate attempt', 'Checkpoint / settings manifest', 'Policy and physics traces'])
    box(p,485,190,355,185,'Align observations',
        ['Commands + actual motion', 'Requested / clamped targets', 'Joint angles + torque', 'Foot contacts / first impact'])
    box(p,930,190,350,185,'Dashboard analysis',
        ['Approach / impact / ascent', 'Target vs measured motion', 'RMS + tracking + tilt', 'Saturation + foot support'],accent=True)
    box(p,1370,190,375,185,'Identify the mismatch',
        ['Bounds / observation contract', 'Impact-recovery response', 'Tracking / heading loss', 'Candidate cause, not proof'])
    for a,b in [(395,485),(840,930),(1280,1370)]: path(p,f'M {a+5} 283 H {b-6}')
    box(p,1370,490,375,185,'One-factor comparison',
        ['Same start and command', 'Fixed weights / bounds / gains', 'Change one setting only', 'Retain all successes / failures'],accent=True)
    path(p,'M 1557 381 V 484')
    box(p,730,490,545,185,'Judge improvement',
        ['Lower oscillation + preserved tracking', 'Heading / tilt / clipping / foot support', 'Full-foot stair traversal criteria', 'Keep hardware validation separate'])
    path(p,'M 1364 580 H 1281')
    path(p,'M 1002 681 V 730 H 225 V 381',dashed=True)
    text(p,55,783,['Interactive runs locate failure events; matched trials test whether an intervention improves them.'],24)
    text(p,55,823,['Recorded operator runs and controlled A/B results are reported separately.'],22)
    save(p,'analysis_architecture_flowchart.svg')


if __name__ == '__main__':
    rl_loop()
    moe_architecture()
    contract_table()
    analysis_architecture()
    print('Generated RL background, MoE architecture and correction-table SVGs.')
