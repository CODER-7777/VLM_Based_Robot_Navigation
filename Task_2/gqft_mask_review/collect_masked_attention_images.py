"""Collect historical masked-attention images without new inference or edits."""
import hashlib
import html
import json
from pathlib import Path
import shutil

LAB=Path(__file__).resolve().parent
ROOT=LAB/'SOLVER_REVIEW/masked_attention'
TRAINED='trained_episode_overlays/20261019T101035Z_431613/20261019T123632Z'


def main():
    if ROOT.exists():raise FileExistsError('Preserve the prior masked-attention collection')
    ROOT.mkdir();data=ROOT/'data';data.mkdir();items=[]
    for name in ['ep629','isolations','soft_attention',TRAINED]:
        for p in sorted((LAB/name).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                rel=p.relative_to(LAB);out=data/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
                sha=hashlib.sha256(p.read_bytes()).hexdigest();assert hashlib.sha256(out.read_bytes()).hexdigest()==sha
                items.append({'file':str(out.relative_to(ROOT)),'source':str(p.relative_to(LAB)),'sha256':sha})
    for name in ['ISOLATION_RESULTS.md','SOFT_ATTENTION_RESULTS.md','isolate_masking.py','probe_soft_attention.py','soft_attention_plan.json']:
        shutil.copy2(LAB/name,data/name)
    rows=[]
    for leg in ['leg00','leg02','leg03','leg04']:
        root='data/'+TRAINED+'/'+leg
        for filename,label in [('attention_comparison.png','Learned attention maps'),('mask_reliability.png','Mask reliability / support'),('masked_only_overlay.png','Trained soft-mask trajectory')]:
            src=root+'/'+filename;assert (ROOT/src).is_file()
            rows.append(f'<article><h3>Episode629 · {leg} · {label}</h3><a href="{src}"><img loading="lazy" src="{src}" alt="{label} {leg}"></a></article>')
    for src,label in [('data/isolations/20261015_gpu2_pooling_v2/neighbour_support.png','Why late masks discard useful neighbouring evidence'),
                      ('data/isolations/20261015_gpu2_pooling_v2/validation/pooling_ablation.png','Hard-mask pooling isolation: validation'),
                      ('data/soft_attention/20261015_gpu2_v1/validation/soft_attention_comparison.png','Frozen soft-attention validation comparison')]:
        rows.append(f'<article><h3>{label}</h3><a href="{src}"><img loading="lazy" src="{src}" alt="{label}"></a></article>')
    links=[]
    for item in items:
        if item['file'].endswith('.png'):
            src=item['file'];links.append(f'<li><a href="{html.escape(src)}">{html.escape(src)}</a></li>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GQFT masked attention images</title><style>*{box-sizing:border-box}body{background:#101b26;color:#edf4fa;font:16px system-ui,sans-serif;margin:0}main{max-width:1500px;margin:auto;padding:22px}p{line-height:1.6}a{color:#94ddff}.notice,article{background:#1b2c3c;border:1px solid #435b70;padding:16px;border-radius:9px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}article{min-width:0}img{width:100%;height:auto;background:white}li{margin:8px 0;overflow-wrap:anywhere}@media(max-width:850px){.grid{grid-template-columns:1fr}}</style><main><h1>Masked-attention images · historical experiments</h1><p>62 PNGs from the October neural masking studies. These are different from the November geometric solver's central-floor pixel selection and from camera-height reconstruction.</p><div class="notice"><strong>Three experiments remain separate.</strong><p>1. Frozen hard masks (13 October): reject late CNN pooling cells, affecting both attention and max branches.<br>2. Frozen soft reliability (15 October): retain the original max branch; validation gains are tiny and uncertain.<br>3. Trained soft-mask pilot (19 October): confidence/ground reliability with first24 flow pairs of episode629 legs0/2/3/4. These are short windows, not complete legs. The mask-only pilot regressed H24 ADE12.46→12.83px; mask+yaw-local regressed versus yaw-local11.35→11.81px.</p></div><p><a href="../START_HERE.html">Back to solver review</a> · <a href="data/TRAINED/index.html">Original trained-mask interactive gallery</a> · <a href="data/ISOLATION_RESULTS.md">Hard-mask isolation report</a> · <a href="data/SOFT_ATTENTION_RESULTS.md">Frozen soft-attention report</a></p><h2>Attention, reliability and masked trajectory images</h2><div class="grid">CARDS</div><h2>Every masked-attention PNG</h2><ul>LINKS</ul></main></html>'''
    (ROOT/'index.html').write_text(page.replace('data/TRAINED/', 'data/'+TRAINED+'/').replace('CARDS',''.join(rows)).replace('LINKS',''.join(links)))
    (ROOT/'COPY_MANIFEST.json').write_text(json.dumps({'files':items,'pngs':len(links),'images_regenerated':False},indent=2)+'\n')
    (ROOT/'README.md').write_text('# Masked-attention images\n\nOpen index.html. All62 existing PNGs are copied without modification, with source hashes. Historical hard-mask, frozen soft-attention, and trained soft-mask experiments are labelled separately. These are not the central-floor solver results or height reconstructions. No inference or training was performed.\n')
    print('MASKED_ATTENTION_GALLERY',len(links),'PNGs',ROOT/'index.html')


if __name__=='__main__':main()
