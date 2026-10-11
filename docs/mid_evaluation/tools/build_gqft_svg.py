#!/usr/bin/env python3
"""Generate editable, independent GQFT architecture and Transformer SVGs."""
from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parents[1] / 'diagrams'
FONT = 'Arial, Liberation Sans, sans-serif'


def start(width, height, title, subtitle):
    return [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<title>{escape(title)}</title><desc>{escape(subtitle)}</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#087f8c"/></marker></defs>
<rect width="100%" height="100%" fill="white"/>
<g font-family="{FONT}">
<text x="55" y="68" font-size="36" font-weight="700" fill="#12243a">{escape(title)}</text>
<text x="55" y="110" font-size="23" fill="#526477">{escape(subtitle)}</text>''']


def text(parts, x, y, lines, size=22, color='#526477', bold=False):
    for i,line in enumerate(lines):
        parts.append(f'<text x="{x}" y="{y+i*(size+9)}" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{escape(line)}</text>')


def box(parts,x,y,w,h,title,body,accent=False,dashed=False):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{"#e6f6f4" if accent else "#eff5fd"}" stroke="{"#007d79" if accent else "#245ec7"}" stroke-width="2"'+(' stroke-dasharray="8 6"' if dashed else '')+'/>')
    text(parts,x+18,y+38,[title],24,'#12243a',True)
    text(parts,x+18,y+77,body,21)


def path(parts,d,dashed=False):
    parts.append(f'<path d="{d}" fill="none" stroke="#087f8c" stroke-width="3" marker-end="url(#arrow)"'+(' stroke-dasharray="8 6"' if dashed else '')+'/>')


def save(parts,name):
    parts.append('</g></svg>')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/name).write_text('\n'.join(parts)+'\n')


def pipeline():
    p=start(1800,950,'GQFT | Flow → temporal motion → geometric trajectory',
            'Code-derived architecture; the pixel query enters projection after the temporal encoder')
    nodes=[
        (55,190,260,'RGB frame pairs',['Frozen flow extraction','Consecutive images']),
        (380,190,280,'Frozen SEA-RAFT',['Flow + confidence','Validity / normalization']),
        (725,190,300,'CNN + spatial pooling',['Flow + x/y coordinates','Mean/max or attention/max','One 256-D token / step']),
        (1090,190,280,'Time embeddings',['Learned time positions','Tokens: [B, T, 256]']),
        (1435,190,310,'Causal Transformer',['4 layers · 8 heads','Past + current steps only','Motion states: [B,T,256]'])]
    for x,y,w,t,b in nodes:box(p,x,y,w,160,t,b,accent='Transformer' in t)
    for a,b in [(315,380),(660,725),(1025,1090),(1370,1435)]:path(p,f'M {a+4} 270 H {b-6}')
    box(p,1435,460,310,155,'Displacement MLP',['256 → 256 → 3','tanh-bounded Δx, Δy, Δz','Invalid time steps zeroed'])
    path(p,'M 1590 355 V 453')
    box(p,1090,460,280,155,'Accumulate motion',['Cumulative sum of Δxyz','Initial position = zero','Path: [B, T+1, 3]'])
    path(p,'M 1429 537 H 1376')
    box(p,725,460,300,155,'Analytic projection',['3-D path + ground anchor','Camera intrinsics / height','Pixel path: [B,Q,T+1,2]'])
    path(p,'M 1084 537 H 1031')
    box(p,380,460,280,155,'Image trajectory',['Query-anchored pixel path','ADE / FDE evaluation','Not obstacle avoidance'])
    path(p,'M 719 537 H 666')
    box(p,725,725,300,115,'Query + camera',['Pixel anchor (u,v)','Fixed-rig geometry'])
    path(p,'M 875 719 V 621')
    box(p,1435,685,310,155,'Optional yaw MLP',['256 → 128 → 1','Bounded Δyaw','Cumulative yaw output'],dashed=True)
    path(p,'M 1751 270 H 1780 V 782 H 1751',dashed=True)
    text(p,55,889,['Defaults shown; checkpoint configuration determines the actual architecture.'],21)
    text(p,55,922,['Validity/uncertainty branches omitted. Yaw is auxiliary: the shown pixel projection consumes xyz, not predicted yaw.'],20)
    save(p,'gqft_pipeline_detailed.svg')


def transformer():
    p=start(1260,1030,'GQFT | Inside the causal Transformer',
            'Temporal self-attention on pooled optical-flow features — no raw RGB or text tokens')
    box(p,55,180,350,155,'Input motion sequence',['One CNN token / flow step','Learned time embedding added','Default input: [B,T,256]'])
    p.append('<rect x="475" y="175" width="730" height="555" rx="18" fill="#f8fafc" stroke="#007d79" stroke-width="2"/>')
    text(p,500,214,['One pre-norm encoder layer × 4'],27,'#007d79',True)
    box(p,560,245,555,105,'LayerNorm → self-attention',['8 heads; future and padded keys masked'],accent=True)
    box(p,560,405,555,105,'Residual addition',['Input + dropout(attention output)'])
    box(p,560,565,555,125,'LayerNorm → feed-forward + residual',['256 → 1024 → 256, GELU','Residual addition; default dropout = 0.1'])
    path(p,'M 411 282 H 554')
    path(p,'M 837 356 V 399')
    path(p,'M 837 516 V 559')
    box(p,475,790,730,130,'Final LayerNorm → motion states',['State at step t uses valid steps 1…t only','[B,T,256] → displacement, optional yaw and log-variance heads'],accent=True)
    path(p,'M 837 736 V 784')
    text(p,55,430,['Causal attention mask'],24,'#12243a',True)
    text(p,55,464,['Rows: current step','Columns: attended steps'],19)
    for i in range(4):
        for j in range(4):
            p.append(f'<rect x="{80+j*63}" y="{520+i*63}" width="57" height="57" rx="4" fill="{"#c7ebe6" if j<=i else "#edf0f4"}"/>')
            text(p,101+j*63,557+i*63,['OK' if j<=i else 'X'],18,'#007d79' if j<=i else '#8291a2')
    text(p,55,804,['Allowed: current + earlier steps','Blocked: future steps','Padding keys also masked'],19)
    text(p,55,965,['Temporal attention selects useful history; CNN spatial attention selects useful image regions.'],21)
    text(p,55,1000,['Pixel query affects the later projection/validity branches, not these temporal motion states.'],21)
    save(p,'gqft_transformer_detail.svg')


if __name__=='__main__':
    pipeline()
    transformer()
    print('Generated two editable SVG files.')
