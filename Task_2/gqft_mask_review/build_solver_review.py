"""Collect the November solver evidence into a portable, non-destructive review."""
from __future__ import annotations
import csv
import hashlib
import html
import json
import os
from pathlib import Path
import shutil

LAB=Path(__file__).resolve().parent
OUT=LAB/'SOLVER_REVIEW'
PILOT='20261111T220751Z_gpu4'
OLD=f'trained_episode_overlays/{PILOT}/all_episodes_20261111T223221Z'
NEW='motion_fixes_20261112'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):return json.loads(path.read_text())


def csv_write(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    if OUT.exists():raise FileExistsError('Review folder already exists; preserve it before making a new snapshot')
    OUT.mkdir();data=OUT/'data';data.mkdir()
    provenance=[]
    def copy(source,target):
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        a=digest(source);assert digest(target)==a
        provenance.append({'file':str(target.relative_to(OUT)),'source':str(source.relative_to(LAB.parent)),
                           'sha256':a,'bytes':source.stat().st_size})
    def tree(source,target):
        for p in sorted(source.rglob('*')):
            if p.is_file() and not any(x in {'__pycache__','.cache','cache','matplotlib'} for x in p.relative_to(source).parts):
                copy(p,target/p.relative_to(source))
    for name in [OLD,NEW,f'training/{PILOT}','ground_geometry_20261109','root_cause_20261112','research_20261104']:
        print('COLLECT',name,flush=True);tree(LAB/name,data/name)
    for name in ['CURRENT_STATUS.md','GQFT_APPROACHES_AND_RESEARCH.md','GQFT_APPROACHES_AND_RESEARCH.docx',
                 'GQFT_APPROACHES_AND_RESEARCH.pdf','all_episode_gallery.html','render_all_episode_overlays.py',
                 'infer_all_episode_overlays.py','sync_all_episode_overlays.py','verify_all_episode_gallery.py']:
        copy(LAB/name,data/name)
    copy(LAB/'dashboard/browser_cdp.py',data/'dashboard/browser_cdp.py')
    # Make the active-code references in the experiment report work offline.
    source=LAB/NEW/'source'
    tree(source,OUT/'gqft_algorithm_sharing_vivekananda')
    copy(LAB.parent/'gqft_algorithm_sharing_vivekananda/AGENTS.md',OUT/'gqft_algorithm_sharing_vivekananda/AGENTS.md')
    images=LAB.parent/'images_for_analysis'
    if images.exists():tree(images,OUT/'user_review_images')
    highlights=OUT/'highlights';highlights.mkdir()
    analyses=OUT/'analysis';analyses.mkdir()
    h24=read(data/NEW/'trained_center_h24.json')
    full=read(data/NEW/'full_sequence_validation.json')
    gate=read(data/NEW/'center_history_gate.json')
    os.environ['MPLCONFIGDIR']=str(OUT/'plot_cache')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    keys=['yaw_local_reference__unchanged','solver_residual__unchanged','solver_residual__center',
          'solver_learned_weights__unchanged','solver_learned_weights__center']
    labels=['Neural reference','Solver + correction','Central floor + correction','Solver + learned weights','Central floor + learned weights']
    rows=[{'method':label,'ade_px':h24['results'][key]['metrics']['ade_px'],
           'ground_error_m':h24['results'][key]['metrics']['mean_ground_err_m'],
           'protocol':'H24/reference30, float32,104 windows,26 sequences,one validation house'} for key,label in zip(keys,labels)]
    csv_write(analyses/'h24_validation.csv',rows)
    fig,ax=plt.subplots(figsize=(10,5));bars=ax.barh(labels,[x['ade_px'] for x in rows],color=['#00a1bc','#da7616','#e5a556','#7660c8','#488c77'])
    ax.invert_yaxis();ax.set(xlabel='Validation ADE (pixels; lower is better)',xlim=(0,19),title='Strongest validated intervention: central-floor solver weights')
    for b,row in zip(bars,rows):ax.text(b.get_width()+.2,b.get_y()+b.get_height()/2,f"{row['ade_px']:.2f}",va='center')
    fig.text(.01,.01,'Same frozen checkpoints. Float32,104 overlapping windows,one house. History acceptance still fails; generalization unproven.',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(highlights/'01_validation_ade.png',dpi=150);fig.savefig(highlights/'01_validation_ade.pdf');plt.close(fig)
    labels2={'neural_chunked':'Neural / chunked','neural_sliding':'Neural / sliding','solver_joint':'Original floor solver',
             'solver_center':'Central floor solver','solver_split':'Far-ray yaw + central translation','quality_fused':'Residual-based quality fusion'}
    rows2=[{'method':v,'ground_error_cm':100*full['summary'][k]['mean_ground_error_m'],
            'endpoint_yaw_error_deg':full['summary'][k]['endpoint_yaw_error_deg'],
            'protocol':'48 observed pairs,context24,float32,26 validation sequences'} for k,v in labels2.items()]
    csv_write(analyses/'full_sequence_controls.csv',rows2)
    fig,ax=plt.subplots(figsize=(10,5));bars=ax.barh([r['method'] for r in rows2],[r['ground_error_cm'] for r in rows2],color=['#319db6','#319db6','#d9903d','#488c77','#a37bba','#a37bba'])
    ax.invert_yaxis();ax.set(xlabel='Mean ground error (cm; lower is better)',xlim=(0,16),title='Full-sequence validation: central floor improves20/26 sequences')
    for b,row in zip(bars,rows2):ax.text(b.get_width()+.15,b.get_y()+b.get_height()/2,f"{row['ground_error_cm']:.2f}",va='center')
    fig.text(.01,.01,'Separate protocol:48 observed pairs,context24,26 sequences,one validation house. Sliding/far-ray/fusion are not promoted.',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(highlights/'02_full_sequence_controls.png',dpi=150);fig.savefig(highlights/'02_full_sequence_controls.pdf');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.7));grows=[]
    for key,label in [('solver_residual','Central floor + correction'),('solver_learned_weights','Central floor + learned weights')]:
        histories=gate['results'][key]['histories'];ax.plot([r['history'] for r in histories],[r['signature_ambiguity'] for r in histories],marker='o',label=label)
        grows.extend({'model':key,'history':r['history'],'ambiguity':r['signature_ambiguity'],
                      'cosine_near_queries':r['signature_close_pairs'],'eligible_queries':r['signature_cross_sequence_eligible']} for r in histories)
    ax.axhline(.05,c='#b53f3f',ls='--',label='Original acceptance limit0.05');ax.set(xlabel='Observed history (flow pairs)',ylabel='Ambiguity among cosine-near queries',ylim=(0,1),title='Unresolved: both central-floor hybrids fail history selection')
    ax.legend(fontsize=8);ax.grid(alpha=.15);fig.tight_layout();fig.savefig(highlights/'03_history_gate.png',dpi=150);fig.savefig(highlights/'03_history_gate.pdf');plt.close(fig)
    csv_write(analyses/'history_gate.csv',grows)
    recorded=[];episode_metrics={}
    for condition,folder in [('original',OLD),('central_floor',NEW+'/original_rgb_center'),('height_experiment',NEW+'/height_corrected_center')]:
        manifest=read(data/folder/'manifest.json')
        for e in manifest['episodes']:
            record=read(data/folder/e['data'])
            for s in record['segments']:
                for arm,p in s['predictions'].items():
                    row={'condition':condition,'episode':e['episode'],'segment':s['id'],'model':arm,'pairs':s['pairs'],
                         'mean_ground_error_cm':100*p['metrics']['mean_ground_error_m'],
                         'endpoint_ground_error_cm':100*p['metrics']['endpoint_ground_error_m'],
                         'scope':'Frozen recorded-episode diagnostic; not a benchmark or selection set'}
                    recorded.append(row)
                    if s['id']=='full':episode_metrics[(condition,e['episode'],arm)]=row
    csv_write(analyses/'all_recorded_trajectory_metrics.csv',recorded)
    featured=[('original',1395,'solver_learned_weights','Low-error original recording; illustrative, not a benchmark winner',OLD),
              ('original',629,'solver_learned_weights','Episode629 before the central-floor intervention',OLD),
              ('central_floor',629,'solver_learned_weights','Episode629 regression: keep this beside the gains',NEW+'/original_rgb_center'),
              ('central_floor',1285,'solver_learned_weights','Long recording improved by central-floor selection',NEW+'/original_rgb_center'),
              ('central_floor',629,'solver_residual','Height experiment control: original RGB and central floor',NEW+'/original_rgb_center'),
              ('height_experiment',629,'solver_residual','Separate height experiment: reconstructed RGB and central floor',NEW+'/height_corrected_center')]
    cards=[]
    for i,(condition,ep,arm,title,folder) in enumerate(featured,4):
        png=data/folder/f'ep{ep}/full/{arm}_overlay.png';target=highlights/f'{i:02d}_{condition}_ep{ep}_{arm}.png'
        shutil.copy2(png,target);m=episode_metrics[(condition,ep,arm)]
        cards.append(f'<article><h3>{html.escape(title)}</h3><p>Episode{ep} · {m["pairs"]} pairs · {m["mean_ground_error_cm"]:.2f}cm mean ground error</p><a href="highlights/{target.name}"><img loading="lazy" src="highlights/{target.name}" alt="{html.escape(title)}"></a></article>')
    snapshots={}
    for arm,c in read(data/OLD/'manifest.json')['checkpoints'].items():snapshots[arm]={k:c[k] for k in ['path','sha256','step','config']}
    (analyses/'CHECKPOINT_REFERENCES.json').write_text(json.dumps(snapshots,indent=2)+'\n')
    source_note='''# Solver review — start here

This is the dedicated review snapshot for the11–12 November solver work, with the9 November solver prototype retained for context. Open **START_HERE.html** or **index.html**. All copied files have independent contents and verified source hashes; original run folders remain preserved.

## Look at these first

1. `START_HERE.html`: strongest validation result, key PNGs, regressions and unresolved history gate.
2. `data/motion_fixes_20261112/comparison.html`: interactive comparison. Experiment A uses original RGB; Experiment B (`#height`) is the separately reconstructed camera-height experiment, with its own cohort and results.
3. `highlights/01_validation_ade.png`: central learned weights15.45→4.65px on104 same-house validation windows, float32. This is an intervention result, not a new checkpoint or established cross-scene improvement.
4. `highlights/02_full_sequence_controls.png`: solver ground error13.55→6.41cm over26 full validation sequences; a separate48-pair protocol.
5. `highlights/03_history_gate.png`: original history selection still fails. Read this alongside every positive result.
6. `data/training/20261111T220751Z_gpu4/REPORT.md`: completed500-step training pilot. The original matched training winner was yaw-local reference10.9558px (CUDA bfloat16); both hybrids were worse before inference controls.

## Everything included

- All1830 trajectory PNGs from the original solver gallery(725), central-floor gallery(725), and separate height gallery(380), plus gallery previews, six featured PNG copies, three new summary figures in PNG/PDF, and the19 images supplied for review.
- Full recorded predictions, metrics, keyframe images, saved original/counterfactual pose inputs, per-window validation results, gate results, height audits, verification receipts and source snapshots.
- Training reports, configs, launch/progress/evaluation logs and exact checkpoint hashes/server locations.
- Early geometric solver experiments, the earlier root-cause analysis, and the papers/implementation review.
- `analysis/all_recorded_trajectory_metrics.csv` for every model/view/condition; validation and history CSVs are separate.
- `SOURCE_COPY_MANIFEST.json`: source→copy hashes. `ALL_FILES.csv`, `PNGS.csv` and `PACKAGE_SHA256.json`: complete local inventory.

## Interpretation rules

The central-floor runtime control changes solver pixel selection; existing checkpoint weights remain frozen. Original-data and reconstructed-height scores stay separate. The height reconstructions preserve the1.2m model/sensor mount but change estimated agent elevation; they are not recovery of the original3-D logs. Only629,753,1285,1395,1481 have complete reconstructed recordings. The three named upstairs episodes remain unresolved.

All10 recorded episodes are retained for visual diagnosis, including locked-test837; none is a parameter-selection set. Featured examples include both gains and regressions, and are not an unbiased benchmark sample. Do not average different protocols or claim the history gate passed.

`data/root_cause_20261112/ROOT_CAUSE.md` is historical: its blanket upstairs grouping, inferred heights and “two thirds removed” causal claim are superseded by the qualified mesh/replay audit in `data/motion_fixes_20261112/README.md`. Absolute floor elevation alone is not clearance. Research DOCX/PDF are older exports; the Markdown has the later solver update.

Large model weight files, the complete raw RGB recordings and optical-flow caches remain at their original server locations. Exact checkpoint paths/hashes are in `analysis/CHECKPOINT_REFERENCES.json`; corrected RGB and cache locations are in the motion-fix report. They were not needed to open the plots, data or dashboards and were not redownloaded. Source run paths embedded in JSON remain provenance, not portable executable paths.
'''
    (OUT/'README.md').write_text(source_note)
    body='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GQFT solver review · start here</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101b26;color:#edf4fa;font:16px system-ui,sans-serif}main{max-width:1400px;padding:24px;margin:auto}h1{font-size:34px;margin:8px 0}h2{margin-top:30px}p{line-height:1.6}a{color:#94ddff}.intro,.box,article{background:#1a2c3c;border:1px solid #3f566a;padding:18px;border-radius:10px;margin:16px 0}.links{display:flex;gap:12px;flex-wrap:wrap}.links a{display:inline-block;padding:12px 16px;border:1px solid #597289;border-radius:7px;text-decoration:none}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}article{margin:0;min-width:0}img{width:100%;height:auto;background:white;border-radius:6px}small,.muted{color:#b7cbdc}.warn{color:#ffd594}.metric{font-size:25px;font-weight:700}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:12px;border-bottom:1px solid #4a5f72}.scroll{overflow:auto}@media(max-width:850px){.grid{grid-template-columns:1fr}main{padding:14px}h1{font-size:28px}}</style>
<main><h1>All solver work ·11–12 November</h1><p>One review folder for the dashboards, trajectory PNGs, plots, raw analysis, source and training evidence. The original run folders are preserved.</p>
<div class="links"><a href="data/motion_fixes_20261112/comparison.html">Open main dashboard</a><a href="data/motion_fixes_20261112/comparison.html#height">Separate camera-height experiment</a><a href="README.md">Folder guide</a><a href="PNGS.csv">All PNGs index</a></div>
<section class="intro"><h2>Strongest validation result, with its limits</h2><p class="metric">15.45 →4.65px ADE</p><p>Central-floor selection with the same frozen learned-weight checkpoint; float32,104 overlapping windows from26 sequences in one validation house. The original matched training pilot's best arm was the yaw-local reference at10.96px under its bfloat16 evaluation. These are separately declared comparisons.</p><p class="warn">The history gate still fails. Full-episode results are mixed, including a regression on629. This is not yet an accepted cross-scene model improvement.</p></section>
<div class="grid"><article><h3>1. Matched H24 validation</h3><a href="highlights/01_validation_ade.png"><img src="highlights/01_validation_ade.png" alt="H24 validation ADE comparison"></a><p><a href="analysis/h24_validation.csv">Raw summary CSV</a> · <a href="data/motion_fixes_20261112/trained_center_h24.json">All window results</a></p></article><article><h3>2. Full-sequence solver controls</h3><a href="highlights/02_full_sequence_controls.png"><img src="highlights/02_full_sequence_controls.png" alt="Full sequence ground error comparison"></a><p>48 observed pairs,context24. Separate from H24 scoring. <a href="analysis/full_sequence_controls.csv">Summary CSV</a></p></article><article><h3>3. Remaining history failure</h3><a href="highlights/03_history_gate.png"><img src="highlights/03_history_gate.png" alt="History ambiguity remains above acceptance limit"></a><p><a href="analysis/history_gate.csv">Gate CSV including retrieval denominators</a></p></article><article><h3>4. Keep camera-height reconstruction separate</h3><p>Model and sensor mount remain1.2m. The separate experiment changes reconstructed agent elevation and rerenders RGB with new flow. Five complete recordings are available; uncertain support remains unresolved.</p><p><a href="data/motion_fixes_20261112/comparison.html#height">Open the separate experiment</a></p><p><a href="data/motion_fixes_20261112/README.md">Full implementation and limitations</a></p></article></div>
<h2>Key trajectory PNGs: successes and regressions</h2><p>These are selected illustrations, not a benchmark sample. Click any PNG to enlarge it. Use the full galleries and CSV for all episodes and legs.</p><div class="grid">FEATURED</div>
<h2>All views and underlying evidence</h2><div class="scroll"><table><thead><tr><th>Collection</th><th>What it contains</th></tr></thead><tbody>
<tr><td><a href="data/OLD/index.html">Original trained solver gallery</a></td><td>10 episodes,133 legs,143 views,725 trajectory PNGs</td></tr>
<tr><td><a href="data/motion_fixes_20261112/original_rgb_center/index.html">Central-floor gallery · original RGB</a></td><td>10 episodes,133 legs,143 views,725 trajectory PNGs</td></tr>
<tr><td><a href="data/motion_fixes_20261112/height_corrected_center/index.html">Separate reconstructed-height gallery</a></td><td>5 episodes,70 legs,75 views,380 trajectory PNGs</td></tr>
<tr><td><a href="analysis/all_recorded_trajectory_metrics.csv">All recorded metrics</a></td><td>Every model, full recording and leg; conditions remain labelled</td></tr>
<tr><td><a href="data/training/PILOT/REPORT.md">Completed training pilot</a></td><td>Reports,configs,progress/evaluation logs,source snapshots; server checkpoint paths/hashes retained</td></tr>
<tr><td><a href="data/ground_geometry_20261109/README.md">Early geometric solver</a></td><td>Prototype code and CPU verification</td></tr>
<tr><td><a href="data/root_cause_20261112/ROOT_CAUSE.md">Earlier diagnosis · historical</a></td><td>Raw leg-error analysis; stronger causal claims are superseded by the qualified height audit</td></tr>
<tr><td><a href="data/GQFT_APPROACHES_AND_RESEARCH.md">Approaches and papers</a></td><td>Research notes,implementation review and repository snapshots</td></tr>
<tr><td><a href="user_review_images/">User review images</a></td><td>All19 supplied solver screenshots, including failures</td></tr>
<tr><td><a href="SOURCE_COPY_MANIFEST.json">Copy provenance</a> · <a href="ALL_FILES.csv">File inventory</a></td><td>Verified copies; all main dashboard/image links stay inside this folder</td></tr>
</tbody></table></div><p class="muted">Recorded episode837 is a locked-test-scene diagnostic, not a selection set. Model weights, full RGB recordings and flow caches remain at documented server paths. This review opens offline without them.</p></main></html>'''
    body=body.replace('FEATURED',''.join(cards)).replace('data/OLD/','data/'+OLD+'/').replace('data/training/PILOT/','data/training/'+PILOT+'/')
    (OUT/'START_HERE.html').write_text(body);(OUT/'index.html').write_text(body)
    (OUT/'SOURCE_COPY_MANIFEST.json').write_text(json.dumps(provenance,indent=2)+'\n')
    inventory=[]
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and 'plot_cache' not in p.relative_to(OUT).parts:
            inventory.append({'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':digest(p)})
    csv_write(OUT/'ALL_FILES.csv',inventory);csv_write(OUT/'PNGS.csv',[x for x in inventory if x['file'].endswith('.png')])
    (OUT/'PACKAGE_SHA256.json').write_text(json.dumps({x['file']:x['sha256'] for x in inventory},indent=2)+'\n')
    print(json.dumps({'folder':str(OUT),'copied_files':len(provenance),'total_files':len(inventory),
                      'trajectory_pngs':1830,'all_pngs':sum(x['file'].endswith('.png') for x in inventory),
                      'size_MiB':round(sum(x['bytes'] for x in inventory)/2**20,2)},indent=2))


if __name__=='__main__':main()
