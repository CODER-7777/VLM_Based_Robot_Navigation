#!/usr/bin/env python3
"""
Generate a publication/presentation-grade SVG comparison table for Task 1:
Simulator Selection (Genesis + MuJoCo vs Isaac Sim, Unreal/Unity, Habitat).
"""
import os
import subprocess
from pathlib import Path

SVG_CONTENT = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1240 730" width="1240" height="730" style="background:#ffffff; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <!-- Drop shadows -->
    <filter id="card-shadow" x="-5%" y="-3%" width="110%" height="108%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="6" stdDeviation="12" flood-color="#0f172a" flood-opacity="0.06"/>
      <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#0f172a" flood-opacity="0.04"/>
    </filter>
    <filter id="badge-shadow" x="-10%" y="-10%" width="120%" height="130%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#0f172a" flood-opacity="0.08"/>
    </filter>

    <!-- Gradients -->
    <linearGradient id="genesis-col-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#EFF6FF" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#EFF6FF" stop-opacity="0.4"/>
    </linearGradient>
    <linearGradient id="mujoco-col-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#F0FDF4" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="#F0FDF4" stop-opacity="0.45"/>
    </linearGradient>
    <linearGradient id="footer-grad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#F8FAFC"/>
      <stop offset="50%" stop-color="#F1F5F9"/>
      <stop offset="100%" stop-color="#F8FAFC"/>
    </linearGradient>

    <!-- Reusable Icons -->
    <!-- Green Check -->
    <g id="icon-check">
      <circle cx="12" cy="12" r="10" fill="#DCFCE7"/>
      <circle cx="12" cy="12" r="10" stroke="#16A34A" stroke-width="1.5" fill="none"/>
      <path d="M7.5 12.5L10.5 15.5L16.5 8.5" stroke="#15803D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    </g>

    <!-- Red Cross -->
    <g id="icon-cross">
      <circle cx="12" cy="12" r="10" fill="#FEE2E2"/>
      <circle cx="12" cy="12" r="10" stroke="#DC2626" stroke-width="1.5" fill="none"/>
      <path d="M8.5 8.5L15.5 15.5M15.5 8.5L8.5 15.5" stroke="#B91C1C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </g>

    <!-- Amber Warning -->
    <g id="icon-warning">
      <circle cx="12" cy="12" r="10" fill="#FEF3C7"/>
      <circle cx="12" cy="12" r="10" stroke="#D97706" stroke-width="1.5" fill="none"/>
      <path d="M12 7.5V12.5M12 15.5V16" stroke="#B45309" stroke-width="2" stroke-linecap="round"/>
    </g>
  </defs>

  <style>
    .title-main { font-size: 23px; font-weight: 800; fill: #0F172A; letter-spacing: -0.4px; }
    .title-sub { font-size: 13.5px; fill: #475569; font-weight: 500; }
    .tag-text { font-size: 10.5px; font-weight: 700; letter-spacing: 0.6px; text-transform: uppercase; }

    .th-title { font-size: 15px; font-weight: 700; fill: #0F172A; }
    .th-subtitle { font-size: 11px; font-weight: 500; fill: #64748B; }

    .crit-title { font-size: 13.5px; font-weight: 700; fill: #1E293B; }
    .crit-sub { font-size: 11px; fill: #64748B; font-weight: 400; }

    .val-primary { font-size: 12.5px; font-weight: 700; fill: #0F172A; }
    .val-secondary { font-size: 10.5px; fill: #64748B; font-weight: 500; }

    .callout-title { font-size: 12.5px; font-weight: 800; fill: #1E293B; letter-spacing: 0.3px; }
    .callout-body { font-size: 12px; fill: #334155; font-weight: 500; line-height: 1.4; }
  </style>

  <!-- Container Box -->
  <rect x="25" y="20" width="1190" height="690" rx="16" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1.5" filter="url(#card-shadow)"/>

  <!-- ================= HEADER SECTION ================= -->
  <!-- Tag -->
  <rect x="50" y="42" width="195" height="24" rx="12" fill="#EEF2FF" stroke="#C7D2FE" stroke-width="1"/>
  <text x="147" y="58" text-anchor="middle" class="tag-text" fill="#4338CA">TASK 1 EVALUATION MATRIX</text>

  <!-- Title & Subtitle -->
  <text x="50" y="92" class="title-main">Simulation Platform Trade-Off &amp; Selection Analysis</text>
  <text x="50" y="114" class="title-sub">Hardware Constraint: Laptop RTX 3050 (4 GB VRAM) • Target: Unitree Go2 Locomotion in Photorealistic Scenes</text>

  <!-- Spec / Budget Indicator Badge on Right -->
  <rect x="990" y="42" width="200" height="64" rx="10" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1"/>
  <text x="1005" y="63" font-size="11px" font-weight="700" fill="#64748B" text-transform="uppercase" letter-spacing="0.5px">BUDGET ENFORCEMENT</text>
  <text x="1005" y="82" font-size="14px" font-weight="800" fill="#0F172A">4 GB VRAM Ceiling</text>
  <text x="1005" y="97" font-size="11px" font-weight="500" fill="#059669">Strict zero-OOM constraint</text>

  <!-- ================= TABLE GRID ================= -->
  <!-- Column Background Highlights for Genesis & MuJoCo -->
  <!-- Genesis Column Highlight -->
  <rect x="270" y="130" width="180" height="425" rx="10" fill="url(#genesis-col-grad)" stroke="#3B82F6" stroke-width="1.8" stroke-dasharray="0"/>
  <!-- MuJoCo Column Highlight -->
  <rect x="1010" y="130" width="180" height="425" rx="10" fill="url(#mujoco-col-grad)" stroke="#10B981" stroke-width="1.8" stroke-dasharray="0"/>

  <!-- Table Header Bar Background -->
  <rect x="45" y="130" width="1150" height="72" rx="10" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1"/>
  <!-- Redraw header portion over highlight columns so it layers properly -->
  <path d="M 270 140 Q 270 130 280 130 L 440 130 Q 450 130 450 140 L 450 202 L 270 202 Z" fill="#EFF6FF"/>
  <path d="M 1010 140 Q 1010 130 1020 130 L 1180 130 Q 1190 130 1190 140 L 1190 202 L 1010 202 Z" fill="#F0FDF4"/>

  <!-- Horizontal Grid Lines -->
  <line x1="45" y1="202" x2="1195" y2="202" stroke="#CBD5E1" stroke-width="1.5"/>
  <line x1="45" y1="273" x2="1195" y2="273" stroke="#E2E8F0" stroke-width="1"/>
  <line x1="45" y1="344" x2="1195" y2="344" stroke="#E2E8F0" stroke-width="1"/>
  <line x1="45" y1="415" x2="1195" y2="415" stroke="#E2E8F0" stroke-width="1"/>
  <line x1="45" y1="486" x2="1195" y2="486" stroke="#E2E8F0" stroke-width="1"/>
  <line x1="45" y1="555" x2="1195" y2="555" stroke="#CBD5E1" stroke-width="1.5"/>

  <!-- Vertical Divider Lines (subtle) -->
  <line x1="265" y1="130" x2="265" y2="555" stroke="#E2E8F0" stroke-width="1"/>
  <line x1="455" y1="130" x2="455" y2="555" stroke="#E2E8F0" stroke-width="1"/>
  <line x1="640" y1="130" x2="640" y2="555" stroke="#E2E8F0" stroke-width="1"/>
  <line x1="825" y1="130" x2="825" y2="555" stroke="#E2E8F0" stroke-width="1"/>
  <line x1="1005" y1="130" x2="1005" y2="555" stroke="#E2E8F0" stroke-width="1"/>

  <!-- ================= COLUMN HEADERS ================= -->
  <!-- Col 0: Criterion -->
  <text x="65" y="162" class="th-title">Evaluation Criterion</text>
  <text x="65" y="180" class="th-subtitle">5 Architectural Axes</text>

  <!-- Col 1: Genesis (Selected: Visuals) -->
  <rect x="290" y="140" width="140" height="20" rx="10" fill="#2563EB" filter="url(#badge-shadow)"/>
  <text x="360" y="154" text-anchor="middle" font-size="10px" font-weight="800" fill="#FFFFFF" letter-spacing="0.5px">★ SELECTED : VISUAL</text>
  <text x="360" y="179" text-anchor="middle" class="th-title" fill="#1E40AF">Genesis</text>
  <text x="360" y="195" text-anchor="middle" class="th-subtitle" fill="#3B82F6">Decoupled Physics &amp; RayTracer</text>

  <!-- Col 2: Isaac Sim -->
  <text x="547" y="166" text-anchor="middle" class="th-title">Isaac Sim</text>
  <text x="547" y="184" text-anchor="middle" class="th-subtitle">Omniverse / PhysX 5</text>

  <!-- Col 3: Unreal / Unity -->
  <text x="732" y="166" text-anchor="middle" class="th-title">Unreal / Unity</text>
  <text x="732" y="184" text-anchor="middle" class="th-subtitle">Game Engine Pipelines</text>

  <!-- Col 4: AI Habitat -->
  <text x="915" y="166" text-anchor="middle" class="th-title">AI Habitat</text>
  <text x="915" y="184" text-anchor="middle" class="th-subtitle">Habitat-Sim / Matterport</text>

  <!-- Col 5: MuJoCo (Selected: Locomotion) -->
  <rect x="1030" y="140" width="140" height="20" rx="10" fill="#059669" filter="url(#badge-shadow)"/>
  <text x="1100" y="154" text-anchor="middle" font-size="10px" font-weight="800" fill="#FFFFFF" letter-spacing="0.5px">★ SELECTED : PHYSICS</text>
  <text x="1100" y="179" text-anchor="middle" class="th-title" fill="#065F46">MuJoCo</text>
  <text x="1100" y="195" text-anchor="middle" class="th-subtitle" fill="#059669">DeepMind Contact Engine</text>


  <!-- ================= ROW 1: Quadruped Physics ================= -->
  <!-- Crit Name -->
  <text x="65" y="232" class="crit-title">Quadruped Physics</text>
  <text x="65" y="249" class="crit-sub">Contact stability &amp; Go2 model</text>

  <!-- Genesis -->
  <use href="#icon-check" x="285" y="226"/>
  <text x="315" y="233" class="val-primary" fill="#1E3A8A">Excellent</text>
  <text x="315" y="248" class="val-secondary">Fast rigid-body, Go2 URDF</text>

  <!-- Isaac Sim -->
  <use href="#icon-check" x="475" y="226"/>
  <text x="505" y="233" class="val-primary">Excellent</text>
  <text x="505" y="248" class="val-secondary">PhysX 5 GPU pipeline</text>

  <!-- Unreal / Unity -->
  <use href="#icon-warning" x="660" y="226"/>
  <text x="690" y="233" class="val-primary">Hard to Bridge</text>
  <text x="690" y="248" class="val-secondary">High IPC / sync latency</text>

  <!-- Habitat -->
  <use href="#icon-cross" x="845" y="226"/>
  <text x="875" y="233" class="val-primary">Weak Contact</text>
  <text x="875" y="248" class="val-secondary">Not tuned for legged robots</text>

  <!-- MuJoCo -->
  <use href="#icon-check" x="1025" y="226"/>
  <text x="1055" y="233" class="val-primary" fill="#064E3B">Best-in-Class</text>
  <text x="1055" y="248" class="val-secondary">Convex contact dynamics</text>


  <!-- ================= ROW 2: Visual Realism ================= -->
  <!-- Crit Name -->
  <text x="65" y="303" class="crit-title">Visual Realism</text>
  <text x="65" y="320" class="crit-sub">PBR lighting &amp; textures</text>

  <!-- Genesis -->
  <use href="#icon-check" x="285" y="297"/>
  <text x="315" y="304" class="val-primary" fill="#1E3A8A">Path Tracing</text>
  <text x="315" y="319" class="val-secondary">Native raytracer backend</text>

  <!-- Isaac Sim -->
  <use href="#icon-check" x="475" y="297"/>
  <text x="505" y="304" class="val-primary">Very High</text>
  <text x="505" y="319" class="val-secondary">Full RTX raytracing</text>

  <!-- Unreal / Unity -->
  <use href="#icon-check" x="660" y="297"/>
  <text x="690" y="304" class="val-primary">Very High</text>
  <text x="690" y="319" class="val-secondary">Lumen / Nanite assets</text>

  <!-- Habitat -->
  <use href="#icon-check" x="845" y="297"/>
  <text x="875" y="304" class="val-primary">High</text>
  <text x="875" y="319" class="val-secondary">Scanned Matterport scenes</text>

  <!-- MuJoCo -->
  <use href="#icon-cross" x="1025" y="297"/>
  <text x="1055" y="304" class="val-primary">Low</text>
  <text x="1055" y="319" class="val-secondary">Basic OpenGL rasterizer</text>


  <!-- ================= ROW 3: Hardware Fit (RTX 3050, 4 GB) ================= -->
  <!-- Crit Name -->
  <text x="65" y="374" class="crit-title">RTX 3050 Fit (4 GB)</text>
  <text x="65" y="391" class="crit-sub">Memory ceiling compliance</text>

  <!-- Genesis -->
  <use href="#icon-check" x="285" y="368"/>
  <text x="315" y="375" class="val-primary" fill="#1E3A8A">Runs Smoothly</text>
  <text x="315" y="390" class="val-secondary">Lightweight preview mode</text>

  <!-- Isaac Sim -->
  <use href="#icon-cross" x="475" y="368"/>
  <text x="505" y="375" class="val-primary" fill="#B91C1C">OOM Crash</text>
  <text x="505" y="390" class="val-secondary">Hard min: &#8805; 16 GB VRAM</text>

  <!-- Unreal / Unity -->
  <use href="#icon-cross" x="660" y="368"/>
  <text x="690" y="375" class="val-primary" fill="#B91C1C">&gt;100 GB Disk</text>
  <text x="690" y="390" class="val-secondary">Heavy VRAM / storage tax</text>

  <!-- Habitat -->
  <use href="#icon-check" x="845" y="368"/>
  <text x="875" y="375" class="val-primary">Yes</text>
  <text x="875" y="390" class="val-secondary">Moderate RAM/VRAM load</text>

  <!-- MuJoCo -->
  <use href="#icon-check" x="1025" y="368"/>
  <text x="1055" y="375" class="val-primary" fill="#064E3B">Highly Efficient</text>
  <text x="1055" y="390" class="val-secondary">&lt; 1 GB total footprint</text>


  <!-- ================= ROW 4: RL-Ready Python API ================= -->
  <!-- Crit Name -->
  <text x="65" y="445" class="crit-title">RL Python API</text>
  <text x="65" y="462" class="crit-sub">PyTorch &amp; policy loop ease</text>

  <!-- Genesis -->
  <use href="#icon-check" x="285" y="439"/>
  <text x="315" y="446" class="val-primary" fill="#1E3A8A">Native &amp; Direct</text>
  <text x="315" y="461" class="val-secondary">Zero IPC; PyTorch tensors</text>

  <!-- Isaac Sim -->
  <use href="#icon-warning" x="475" y="439"/>
  <text x="505" y="446" class="val-primary">Heavy Stack</text>
  <text x="505" y="461" class="val-secondary">Omniverse runtime layers</text>

  <!-- Unreal / Unity -->
  <use href="#icon-cross" x="660" y="439"/>
  <text x="690" y="446" class="val-primary">Complex Bridge</text>
  <text x="690" y="461" class="val-secondary">Requires custom sockets</text>

  <!-- Habitat -->
  <use href="#icon-warning" x="845" y="439"/>
  <text x="875" y="446" class="val-primary">Medium</text>
  <text x="875" y="461" class="val-secondary">Custom Gym wrappers</text>

  <!-- MuJoCo -->
  <use href="#icon-check" x="1025" y="439"/>
  <text x="1055" y="446" class="val-primary" fill="#064E3B">Native &amp; Direct</text>
  <text x="1055" y="461" class="val-secondary">Gymnasium / MJX support</text>


  <!-- ================= ROW 5: Setup &amp; Deployment ================= -->
  <!-- Crit Name -->
  <text x="65" y="516" class="crit-title">Setup Effort</text>
  <text x="65" y="533" class="crit-sub">Installation &amp; dependencies</text>

  <!-- Genesis -->
  <use href="#icon-check" x="285" y="510"/>
  <text x="315" y="517" class="val-primary" fill="#1E3A8A">pip install</text>
  <text x="315" y="532" class="val-secondary">Single command setup</text>

  <!-- Isaac Sim -->
  <use href="#icon-cross" x="475" y="510"/>
  <text x="505" y="517" class="val-primary">Very High</text>
  <text x="505" y="532" class="val-secondary">NVIDIA Omniverse app</text>

  <!-- Unreal / Unity -->
  <use href="#icon-cross" x="660" y="510"/>
  <text x="690" y="517" class="val-primary">Very High</text>
  <text x="690" y="532" class="val-secondary">Gigabyte SDK downloads</text>

  <!-- Habitat -->
  <use href="#icon-warning" x="845" y="510"/>
  <text x="875" y="517" class="val-primary">Medium</text>
  <text x="875" y="532" class="val-secondary">Conda &amp; C++ builds</text>

  <!-- MuJoCo -->
  <use href="#icon-check" x="1025" y="510"/>
  <text x="1055" y="517" class="val-primary" fill="#064E3B">pip install</text>
  <text x="1055" y="532" class="val-secondary">Fast Python wheel</text>


  <!-- ================= FOOTER / DECISION CALLOUT ================= -->
  <rect x="45" y="575" width="1150" height="110" rx="12" fill="url(#footer-grad)" stroke="#CBD5E1" stroke-width="1.2"/>

  <!-- Left Accent Ribbon -->
  <path d="M 45 587 Q 45 575 57 575 L 57 685 Q 45 685 45 673 Z" fill="#2563EB"/>

  <!-- Callout Header -->
  <rect x="70" y="587" width="165" height="22" rx="6" fill="#DBEAFE"/>
  <text x="78" y="602" font-size="10.5px" font-weight="800" fill="#1D4ED8" letter-spacing="0.5px">ARCHITECTURAL DECISION</text>
  <text x="250" y="603" class="callout-title">Complementary Dual-Simulator Architecture</text>

  <!-- Two Pill Summaries -->
  <!-- Box 1: Genesis -->
  <g transform="translate(70, 618)">
    <rect x="0" y="0" width="520" height="52" rx="8" fill="#FFFFFF" stroke="#BFDBFE" stroke-width="1"/>
    <circle cx="26" cy="26" r="14" fill="#DBEAFE"/>
    <!-- Visual / 3D camera vector icon -->
    <path d="M18 20V29C18 30 18.8 30.8 19.8 30.8H32.2C33.2 30.8 34 30 34 29V20C34 19 33.2 18.2 32.2 18.2H29.8L28.6 16.5H23.4L22.2 18.2H19.8C18.8 18.2 18 19 18 20Z" fill="none" stroke="#1E40AF" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="26" cy="24.5" r="2.8" fill="none" stroke="#1E40AF" stroke-width="1.5"/>
    <text x="50" y="21" font-size="12px" font-weight="700" fill="#1E40AF">Genesis — Chosen for Photorealistic Environment Simulation</text>
    <text x="50" y="38" font-size="11px" font-weight="500" fill="#475569">Loads 3D office (.glb) with decoupled physics plane; fits strictly within 4 GB VRAM.</text>
  </g>

  <!-- Box 2: MuJoCo -->
  <g transform="translate(620, 618)">
    <rect x="0" y="0" width="555" height="52" rx="8" fill="#FFFFFF" stroke="#A7F3D0" stroke-width="1"/>
    <circle cx="26" cy="26" r="14" fill="#D1FAE5"/>
    <!-- Quadruped leg / joint linkage vector icon -->
    <circle cx="26" cy="18" r="2" fill="none" stroke="#065F46" stroke-width="1.6"/>
    <path d="M26 20L22 25.5L27 29.5L29 32" fill="none" stroke="#065F46" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="22" cy="25.5" r="1.4" fill="#065F46"/>
    <circle cx="27" cy="29.5" r="1.4" fill="#065F46"/>
    <text x="50" y="21" font-size="12px" font-weight="700" fill="#065F46">MuJoCo — Chosen for Locomotion Contact Dynamics &amp; Sim-to-Real</text>
    <text x="50" y="38" font-size="11px" font-weight="500" fill="#475569">Gold-standard foot contacts for SvanM2 quadruped MoE policy training (Task 3).</text>
  </g>

</svg>
'''

def main():
    root = Path("/home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation")
    diagrams_dir = root / "docs" / "mid_evaluation" / "diagrams"
    assets_dir = root / "docs" / "mid_evaluation" / "presentation" / "assets"

    diagrams_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    svg_dest1 = diagrams_dir / "task1_simulator_comparison.svg"
    svg_dest2 = assets_dir / "task1_simulator_comparison.svg"

    with open(svg_dest1, "w", encoding="utf-8") as f:
        f.write(SVG_CONTENT)
    with open(svg_dest2, "w", encoding="utf-8") as f:
        f.write(SVG_CONTENT)
    print(f"Written SVG to {svg_dest1} and {svg_dest2}")

    # Render PNG using headless chrome
    png_dest1 = diagrams_dir / "task1_simulator_comparison.png"
    png_dest2 = assets_dir / "task1_simulator_comparison.png"
    try:
        cmd = [
            "/usr/bin/google-chrome",
            "--headless",
            "--disable-gpu",
            "--force-device-scale-factor=2",
            "--window-size=1260,760",
            f"--screenshot={png_dest1}",
            f"file://{svg_dest1}"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            import shutil
            shutil.copyfile(png_dest1, png_dest2)
            print(f"Rendered PNG to {png_dest1} and {png_dest2}")
        else:
            print(f"Chrome screenshot returned code {res.returncode}: {res.stderr}")
    except Exception as e:
        print(f"Could not render PNG: {e}")

if __name__ == "__main__":
    main()
