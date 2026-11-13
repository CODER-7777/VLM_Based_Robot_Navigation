"""Render downloaded episode predictions to PNGs and a self-contained HTML gallery.

This script performs no inference, network access or training. It is safe to rerun
as additional completed episodes arrive; existing prediction files are preserved.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
COLORS = {'ground_truth':'#ed119a','yaw_local_reference':'#00bcd4',
          'solver_residual':'#ff941f','solver_learned_weights':'#8058ee'}
LABELS = {'yaw_local_reference':'Yaw-local reference','solver_residual':'Solver + correction',
          'solver_learned_weights':'Solver + learned weights'}
ARMS = list(LABELS)


def font(size, bold=False):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)


def clip(a,b,width,height):
    x,y=a;dx,dy=b[0]-x,b[1]-y;lo,hi=0.,1.
    for p,q in [(-dx,x),(dx,width-x),(-dy,y),(dy,height-y)]:
        if p==0:
            if q<0:return None
        elif p<0:
            lo=max(lo,q/p)
        else:
            hi=min(hi,q/p)
    if lo>hi:return None
    return ((x+lo*dx,y+lo*dy),(x+hi*dx,y+hi*dy))


def line(draw,trajectory,scale,offset,width,height,color):
    uv=np.asarray(trajectory['uv_px']);visible=np.asarray(trajectory['positive_depth'])
    inside=np.asarray(trajectory['in_canvas']);prefix=np.logical_and.accumulate(inside)
    for i in range(1,len(uv)):
        if not visible[i-1:i+1].all():continue
        clipped=clip(uv[i-1]*scale,uv[i]*scale,width,height)
        if clipped is None:continue
        a,b=[tuple(np.asarray(v)+offset) for v in clipped]
        if prefix[i]:draw.line([a,b],fill=color,width=3)
        else:
            a,b=np.asarray(a),np.asarray(b);delta=b-a;length=np.linalg.norm(delta)
            if length>0:
                for start in np.arange(0,length,8):
                    u=a+delta*(start/length);v=a+delta*(min(start+4,length)/length)
                    draw.line([tuple(u),tuple(v)],fill=color,width=3)
    if len(uv) and visible[-1] and np.all(uv[-1]*scale >= 0) and np.all(uv[-1]*scale <= [width,height]):
        x,y=uv[-1]*scale+offset
        draw.line([(x-5,y-5),(x+5,y+5)],fill=color,width=3)
        draw.line([(x-5,y+5),(x+5,y-5)],fill=color,width=3)


def overlay(root,episode,segment,arm=None,all_models=False):
    width=640;scale=width/960;canvas=int(810*scale);top=46;footer=64
    out=Image.new('RGB',(width,top+canvas+footer),'white');d=ImageDraw.Draw(out)
    photo=Image.open(root/segment['background']).convert('RGB').resize((width,int(540*scale)),Image.Resampling.LANCZOS)
    out.paste(photo,(0,top));d.rectangle([0,0,width,top],fill='#142838')
    title=f"Episode {episode} / {segment['id']} / {segment['pairs']} pairs"
    d.text((12,7),title,font=font(17,True),fill='white')
    d.text((12,27),LABELS.get(arm,'All models' if all_models else 'Recorded ground truth'),font=font(12),fill='#e4edf5')
    d.line([(0,top+540*scale),(width,top+540*scale)],fill='#9aa8b4',width=1)
    line(d,segment['reference'],scale,np.array([0,top]),width,canvas,COLORS['ground_truth'])
    chosen=ARMS if all_models else ([arm] if arm else [])
    for key in chosen:line(d,segment['predictions'][key],scale,np.array([0,top]),width,canvas,COLORS[key])
    d.ellipse([width/2-4,top+canvas-5,width/2+4,top+canvas+3],fill='white',outline='#122634',width=2)
    d.text((12,top+canvas+8),'Pink = ground truth. X = endpoint. Start = bottom centre.',font=font(12),fill='#26394b')
    if arm:
        m=segment['predictions'][arm]['metrics']
        d.text((12,top+canvas+29),f"Ground mean {m['mean_ground_error_m']*100:.1f} cm / end {m['endpoint_ground_error_m']*100:.1f} cm",font=font(13,True),fill='#172d40')
    else:d.text((12,top+canvas+29),'Dashed = after the first canvas exit. Ground view shows the full path.',font=font(11),fill='#26394b')
    return out


def ground_plot(path,episode,segment):
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.7))
    gt=np.asarray(segment['reference']['ground_m'])
    axes[0].plot(gt[:,1],gt[:,0],color=COLORS['ground_truth'],lw=2.8,label='Recorded ground truth')
    axes[0].scatter(*gt[-1,[1,0]],color=COLORS['ground_truth'],marker='X',s=55,zorder=4)
    for arm in ARMS:
        p=segment['predictions'][arm];g=np.asarray(p['ground_m'])
        axes[0].plot(g[:,1],g[:,0],color=COLORS[arm],lw=1.9,label=LABELS[arm])
        axes[0].scatter(*g[-1,[1,0]],color=COLORS[arm],marker='X',s=45,zorder=4)
        axes[1].plot(np.arange(1,len(g)),p['metrics']['ground_error_cm'][1:],color=COLORS[arm],label=LABELS[arm])
    axes[0].scatter(0,0,c='white',edgecolors='black',marker='s',s=35,zorder=5)
    axes[0].set(xlabel='Left (m)',ylabel='Forward (m)',title='Complete ground path; X = endpoint')
    axes[0].set_aspect('equal',adjustable='datalim')
    axes[1].set(xlabel='Frame after start',ylabel='Position error (cm)',title='Ground error against recorded poses')
    for boundary in segment['chunk_boundaries']:axes[1].axvline(boundary,c='#999999',alpha=.14,lw=.7)
    for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=7,loc='best')
    fig.suptitle(f"Episode {episode} / {segment['id']} / full {segment['pairs']}-pair trajectory",fontsize=12)
    fig.tight_layout();fig.savefig(path,dpi=120);plt.close(fig)


def build(root):
    os.environ['MPLCONFIGDIR']=str(root/'matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    manifest=json.loads((root/'manifest.json').read_text())
    if manifest.get('solver_control')=='center':
        LABELS.update(solver_residual='Central floor + correction',
                      solver_learned_weights='Central floor + learned weights')
    payload={'manifest':manifest,'episodes':{}}
    records=[];images=[]
    for ep in manifest['episodes']:
        record=json.loads((root/ep['data']).read_text());eid=ep['episode']
        assert hashlib.sha256((root/ep['data']).read_bytes()).hexdigest()==ep['sha256']
        for segment in record['segments']:
            folder=root/f'ep{eid}'/segment['id'];folder.mkdir(exist_ok=True)
            if not (folder/'comparison.png').exists():
                panels=[overlay(root,eid,segment)]+[overlay(root,eid,segment,arm) for arm in ARMS]
                sheet=Image.new('RGB',(1280,panels[0].height*2),'white')
                for index,panel in enumerate(panels):sheet.paste(panel,((index%2)*640,(index//2)*panel.height))
                sheet.save(folder/'comparison.png',compress_level=5)
            for arm in ARMS:
                target=folder/(arm+'_overlay.png')
                if not target.exists():overlay(root,eid,segment,arm).save(target,compress_level=5)
                images.append(target)
            if not (folder/'ground_paths.png').exists():ground_plot(folder/'ground_paths.png',eid,segment)
            images.extend([folder/'comparison.png',folder/'ground_paths.png'])
            segment['image_data']='data:image/jpeg;base64,'+base64.b64encode((root/segment['background']).read_bytes()).decode()
            for arm in ARMS:
                m=segment['predictions'][arm]['metrics']
                records.append({'episode':eid,'segment':segment['id'],'model':arm,'pairs':segment['pairs'],
                                **{k:v for k,v in m.items() if k!='ground_error_cm'}})
        # One readable contact sheet per episode, including every leg.
        overview=root/f'ep{eid}'/'START_HERE_overview.png'
        if not overview.exists():
            legs=[s for s in record['segments'] if s['id']!='full'];cols=min(4,len(legs));rows=math.ceil(len(legs)/cols)
            thumb=(384,390);sheet=Image.new('RGB',(cols*thumb[0],rows*thumb[1]+44),'#e9eef3')
            ImageDraw.Draw(sheet).text((12,10),f'Episode {eid}: every leg / pink ground truth, cyan reference, orange correction, violet learned weights',font=font(13,True),fill='#142838')
            for i,segment in enumerate(legs):
                panel=overlay(root,eid,segment,all_models=True);panel.thumbnail(thumb,Image.Resampling.LANCZOS)
                sheet.paste(panel,((i%cols)*thumb[0],44+(i//cols)*thumb[1]))
            sheet.save(overview,compress_level=5)
        images.append(overview)
        payload['episodes'][str(eid)]=record
        print('RENDERED',eid,len(record['segments']),'views',flush=True)
    template=(HERE/'all_episode_gallery.html').read_text()
    is_height=any(r.get('vertical_reference')=='mesh_reconstructed' for r in payload['episodes'].values())
    if is_height:
        template=template.replace('<h1>See where each model goes</h1>',
            '<h1>Separate experiment: camera-height reconstruction</h1>')
        template=template.replace('<title>GQFT · All episode trajectories</title>',
            '<title>GQFT · Separate camera-height experiment</title>')
        template=template.replace('<main>', '<main><section class="panel"><strong>Reconstructed-data experiment</strong>'
            '<p>Model height and camera mount remain 1.2 m. Agent world-Y follows estimated mesh floor support. '
            'These are separately rendered inputs with newly computed flow; the original recordings are preserved. '
            'This is not recovery of the original vertical pose logs, and these scores do not replace the original-data benchmark.</p>'
            '<a href="../comparison.html#height">Open the separate experiment comparison</a> · '
            '<a href="../comparison.html#original">Return to the original-RGB experiment</a></section>',1)
    if manifest.get('experiment_note'):
        import html
        template=template.replace('<main>', '<main><p class="controls">'+
                                  html.escape(manifest['experiment_note'])+'</p>',1)
    content=json.dumps(payload,separators=(',',':'),allow_nan=False).replace('</','<\\/')
    assert '/* DATA */' in template
    (root/'index.html').write_text(template.replace('/* DATA */','window.EPISODE_DATA='+content+';'))
    (root/'metrics.json').write_text(json.dumps(records,indent=2)+'\n')
    verification={'episodes_rendered':len(payload['episodes']),
                  'legs_rendered':sum(len(r['segments'])-1 for r in payload['episodes'].values()),
                  'full_episode_views':len(payload['episodes']),'png_images':len(images),
                  'all_expected_episodes':len(payload['episodes'])==manifest['expected_episode_count'],
                  'all_expected_legs':sum(len(r['segments'])-1 for r in payload['episodes'].values())==manifest['expected_leg_count'],
                  'prediction_file_hashes_verified':True,'inference_performed_locally':False,
                  'scope':'Frozen model trajectories; includes full recordings and per-leg resets; no fitted alignment',
                  'gallery_bytes':(root/'index.html').stat().st_size}
    (root/'render_verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps(verification,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args();build(args.run.resolve())
