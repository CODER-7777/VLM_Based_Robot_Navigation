"""Build an offline intervention comparison from saved, frozen predictions."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z'


def build():
    runs=[('original','Original RGB / original solver',OLD,'../trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z'),
          ('center','Original RGB / central floor',ROOT/'original_rgb_center','original_rgb_center'),
          ('height','Reconstructed-height RGB / central floor',ROOT/'height_corrected_center','height_corrected_center')]
    payload={}
    for key,label,root,link in runs:
        manifest=json.loads((root/'manifest.json').read_text())
        episodes={}
        for e in manifest['episodes']:
            data=json.loads((root/e['data']).read_text())
            episodes[str(e['episode'])]={'segments':[
                {'id':s['id'],'pairs':s['pairs'],'metrics':{a:p['metrics']['mean_ground_error_m']*100 for a,p in s['predictions'].items()}}
                for s in data['segments']]}
        payload[key]={'label':label,'path':link,'episodes':episodes}
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GQFT intervention comparison</title><style>
*{box-sizing:border-box}body{margin:0;background:#111b26;color:#eaf1f7;font:15px system-ui,sans-serif}main{max-width:1600px;margin:auto;padding:24px}h1{font-size:30px;margin:8px 0}p{line-height:1.6}a{color:#8cddff}label{max-width:100%;display:inline-flex;flex-direction:column;gap:6px;margin:6px 15px 12px 0}select{background:#233749;color:#eef6fb;border:1px solid #526c82;border-radius:6px;padding:9px;font:inherit;max-width:100%}.note,.panel{background:#1b2b3a;border:1px solid #3c5367;border-radius:9px;padding:16px;margin:16px 0}.views{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.view{min-width:0;background:#1b2b3a;padding:12px;border-radius:9px}.view img{width:100%;height:auto;background:#fff}.view h2{font-size:17px}.metric{font-size:22px;font-weight:bold;margin:14px 0}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:600px}td,th{text-align:left;padding:10px;border-bottom:1px solid #405365}button{font:inherit;background:none;border:0;color:#8cddff;cursor:pointer}.warn{color:#ffd399}@media(max-width:950px){.views{grid-template-columns:1fr}main{padding:14px}}
</style><main><h1>GQFT: compare each intervention</h1>
<p>Select a separate experiment, then an episode, trajectory and model. Predictions use their own heading. No fitted scale or alignment.</p>
<div class="panel"><label class="experiment-picker">Experiment<select id="experiment"><option value="original">A · Original RGB: spatial selection</option><option value="height">B · Camera-height reconstruction (separate)</option></select></label><p id="experiment-scope"></p></div>
<div class="note" id="experiment-note"></div>
<p><a href="README.md">Implementation, protocols and limitations</a> · <a href="original_rgb_center/index.html">Original-RGB gallery</a> · <a href="height_corrected_center/index.html">Separate camera-height experiment gallery</a></p>
<div class="panel"><label>Episode<select id="episode"></select></label><label>Trajectory<select id="segment"></select></label><label>Model<select id="model"><option value="solver_learned_weights">Solver + learned weights</option><option value="solver_residual">Solver + correction</option><option value="yaw_local_reference">Yaw-local neural reference</option></select></label><p id="scope"></p></div>
<div class="views" id="views"></div>
<section class="panel"><h2 id="cohort-title"></h2><p>Mean full-episode ground error after the initial origin, in centimetres. Lower is better. Results belong to the selected experiment and model.</p><div class="scroll"><table><thead><tr id="cohort-head"></tr></thead><tbody id="cohort"></tbody></table></div></section>
<p class="warn" id="height-caveat" hidden>Separate reconstructed-data experiment: only629,753,1285,1395,1481 have complete floor-support plans. Other episodes remain unresolved. The new vertical paths follow estimated mesh support; they do not recover the lost original world-Y logs. These results do not replace the original-data benchmark.</p>
</main><script>const D=PAYLOAD, $=id=>document.getElementById(id);window.__comparisonErrors=[];addEventListener('error',e=>window.__comparisonErrors.push(e.message||'Resource error'));
for(const ep of Object.keys(D.center.episodes)){let o=new Option(ep+(ep==='837'?' · locked-test scene':''),ep);$('episode').add(o)}
function segments(){const prev=$('segment').value;$('segment').replaceChildren();for(const s of D.center.episodes[$('episode').value].segments)$('segment').add(new Option(s.id==='full'?'Full episode':s.id,s.id));if([...$('segment').options].some(o=>o.value===prev))$('segment').value=prev;draw()}
function metric(run,ep,seg,model){return D[run].episodes[ep]?.segments.find(s=>s.id===seg)?.metrics[model]}
function draw(){const ep=$('episode').value,seg=$('segment').value,model=$('model').value,experiment=$('experiment').value,isHeight=experiment==='height',runs=isHeight?['center','height']:['original','center'];$('views').replaceChildren();
$('experiment-scope').textContent=isHeight?'Experiment B changes the rendered vertical path only. The central-floor rule and checkpoint weights are held fixed.':'Experiment A compares spatial selection on the same original RGB and poses. This is the default comparison.';
$('experiment-note').textContent=isHeight?'Separate camera-height reconstruction experiment. Model height and sensor mount remain 1.2 m. Agent world-Y follows estimated mesh floor support; RGB and SEA-RAFT flow are newly generated. This is reconstructed data, not a recovered original pose log. Its scores stay separate from the original-data benchmark.':'Original-data experiment. Central floor lowers learned-weight H24 validation ADE from 15.45 to 4.65 px (float32, 104 windows, one validation house). The history gate still fails and full-episode results are mixed, including a regression on 629. No settings are selected on locked-test 837.';
$('height-caveat').hidden=!isHeight;
$('cohort-title').textContent=isHeight?'Experiment B results · five reconstructed-height recordings':'Experiment A results · ten original recordings';
$('cohort-head').replaceChildren();for(const title of ['Episode',...runs.map(k=>D[k].label)]){const th=document.createElement('th');th.textContent=title;$('cohort-head').append(th)}
for(const key of runs){const run=D[key],card=document.createElement('article');card.className='view';card.dataset.run=key;const title=document.createElement('h2');title.textContent=run.label;card.append(title);const val=metric(key,ep,seg,model);if(val===undefined){const p=document.createElement('p');p.textContent='Not rerendered: floor-support audit is uncertain.';card.append(p)}else{let p=document.createElement('p');p.className='metric';p.textContent=val.toFixed(2)+' cm mean ground error';card.append(p);const a=document.createElement('a');a.target='_blank';a.href=run.path+'/ep'+ep+'/'+seg+'/'+model+'_overlay.png';const im=document.createElement('img');im.src=a.href;im.alt=run.label+' trajectory overlay for episode'+ep+' '+seg;a.append(im);card.append(a);const link=document.createElement('a');link.href=run.path+'/index.html';link.textContent='Open interactive gallery';link.target='_blank';card.append(link)}$('views').append(card)}
$('scope').textContent='Episode '+ep+' / '+seg+' · '+(ep==='837'?'Locked-test visualization only; no parameter selection. ':'Frozen recorded-episode diagnostic. ')+(seg==='full'?'Heading is integrated continuously; context uses24-pair chunks.':'Independent leg reset, with full leg trajectory.');
$('cohort').replaceChildren();for(const id of Object.keys(D[isHeight?'height':'center'].episodes)){const row=document.createElement('tr');let td=document.createElement('td'),b=document.createElement('button');b.textContent=id;b.onclick=()=>{$('episode').value=id;segments()};td.append(b);row.append(td);for(const key of runs){td=document.createElement('td');const val=metric(key,id,'full',model);td.textContent=val===undefined?'Uncertain support':val.toFixed(2);row.append(td)}$('cohort').append(row)}
window.COMPARISON_STATE={experiment,episode:ep,segment:seg,model};}
function selectExperiment(){ $('experiment').value=location.hash==='#height'?'height':'original';draw() }
$('experiment').onchange=()=>{location.hash=$('experiment').value};addEventListener('hashchange',selectExperiment);
$('episode').onchange=segments;$('segment').onchange=draw;$('model').onchange=draw;$('episode').value='629';$('experiment').value=location.hash==='#height'?'height':'original';segments();
</script></html>'''
    (ROOT/'comparison.html').write_text(html.replace('PAYLOAD',json.dumps(payload,separators=(',',':')).replace('</','<\\/')))
    print('COMPARISON_BUILT',len(payload['center']['episodes']),'episodes')


if __name__=='__main__':build()
