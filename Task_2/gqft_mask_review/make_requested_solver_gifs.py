"""Animate saved original-run trajectory drawing; no inference or new poses."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw

from render_all_episode_overlays import clip,font

LAB=Path(__file__).resolve().parent
ROOT=LAB/'SOLVER_REVIEW'
SOURCE=ROOT/'data/trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z'
OUT=ROOT/'gifs_original_solver'
CASES=[(478,'leg03'),(753,'leg11'),(837,'leg00'),(837,'leg08')]
COLORS={'reference':'#ed119a','solver_residual':'#ff941f','solver_learned_weights':'#8058ee'}
W=960;CANVAS=810;TOP=88;BOTTOM=76


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def track(draw,t,limit,color):
    uv=np.asarray(t['uv_px']);visible=np.asarray(t['positive_depth']);inside=np.asarray(t['in_canvas'])
    prefix=np.logical_and.accumulate(inside)
    for i in range(1,limit+1):
        if not visible[i-1:i+1].all():continue
        segment=clip(uv[i-1],uv[i],W,CANVAS)
        if segment is None:continue
        a,b=[np.asarray(p)+[0,TOP] for p in segment]
        if prefix[i]:draw.line([tuple(a),tuple(b)],fill=color,width=4)
        else:
            delta=b-a;length=np.linalg.norm(delta)
            if length:
                for begin in np.arange(0,length,12):
                    x=a+delta*(begin/length);y=a+delta*(min(begin+7,length)/length)
                    draw.line([tuple(x),tuple(y)],fill=color,width=4)
    if visible[limit] and np.all(uv[limit]>=0) and np.all(uv[limit]<=[W,CANVAS]):
        x,y=uv[limit]+[0,TOP]
        draw.ellipse([x-5,y-5,x+5,y+5],fill=color)


def main():
    if OUT.exists():raise FileExistsError('Preserve prior GIFs; use a fresh folder for a new run')
    OUT.mkdir()
    manifest=json.loads((SOURCE/'manifest.json').read_text())
    receipts=[];cards=[]
    for ep,leg in CASES:
        record=SOURCE/f'ep{ep}/predictions.json';data=json.loads(record.read_text())
        expected=next(e['sha256'] for e in manifest['episodes'] if e['episode']==ep)
        assert sha(record)==expected
        s=next(x for x in data['segments'] if x['id']==leg);n=s['pairs']
        base=Image.new('RGB',(W,TOP+CANVAS+BOTTOM),'white');draw=ImageDraw.Draw(base)
        draw.rectangle([0,0,W,TOP-1],fill='#142838')
        draw.text((16,10),f'Episode {ep} / {leg} / {n} flow pairs',font=font(23,True),fill='white')
        for x,key,label in [(16,'reference','Reference'),(230,'solver_residual','Solver + correction'),(570,'solver_learned_weights','Solver + learned weights')]:
            draw.line([(x,61),(x+29,61)],fill=COLORS[key],width=5)
            draw.text((x+40,48),label,font=font(17,True),fill='white')
        with Image.open(SOURCE/s['background']) as image:
            base.paste(image.convert('RGB').resize((960,540),Image.Resampling.LANCZOS),(0,TOP))
        draw.line([(0,TOP+540),(W,TOP+540)],fill='#9aa8b4')
        draw.text((14,TOP+550),'Virtual query canvas',font=font(15),fill='#62717e')
        # Reserve exact trace colors, with a shared photo palette for every frame.
        sampled=base.quantize(colors=248,method=Image.Quantize.MEDIANCUT)
        palette=sampled.getpalette()[:248*3]
        for c in list(COLORS.values())+['#ffffff','#142838','#26394b','#9aa8b4','#62717e']:
            palette.extend(tuple(bytes.fromhex(c[1:])))
        palette_image=Image.new('P',(1,1));palette_image.putpalette(palette)
        frames=[]
        for i in range(n+1):
            frame=base.copy();d=ImageDraw.Draw(frame)
            track(d,s['reference'],i,COLORS['reference'])
            for arm in ['solver_residual','solver_learned_weights']:track(d,s['predictions'][arm],i,COLORS[arm])
            x,y=np.asarray(s['reference']['uv_px'][0])+[0,TOP]
            d.rectangle([x-4,y-4,x+4,y+4],fill='white',outline='#142838',width=2)
            d.text((16,TOP+CANVAS+9),f'Path point {i} / {n}   |   Drawing playback: fixed first camera frame',font=font(18),fill='#26394b')
            d.text((16,TOP+CANVAS+39),'Original solver run; no height reconstruction. Dashed = after first canvas exit.',font=font(15),fill='#26394b')
            frames.append(frame.quantize(palette=palette_image,dither=Image.Dither.NONE))
        name=f'ep{ep}_{leg}_solver_correction_and_learned_weights'
        path=OUT/(name+'.gif');durations=[80]*len(frames);durations[0]=600;durations[-1]=1800
        frames[0].save(path,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True,disposal=1)
        frames[-1].convert('RGB').save(OUT/(name+'_final.png'))
        decoded_count=0;total_duration=0
        with Image.open(path) as gif:
            assert gif.info.get('loop')==0
            for k in range(gif.n_frames):
                gif.seek(k);gif.load();total_duration+=gif.info.get('duration',0);decoded_count+=1
                if k==0:assert np.array_equal(np.array(gif.convert('RGB')),np.array(frames[0].convert('RGB')))
            assert decoded_count==len(frames)
            assert np.array_equal(np.array(gif.convert('RGB')),np.array(frames[-1].convert('RGB')))
            assert total_duration==sum(durations)
        receipt={'episode':ep,'leg':leg,'flow_pairs':n,'gif':path.name,'sha256':sha(path),
                 'size_bytes':path.stat().st_size,'frames_verified':decoded_count,'duration_ms':total_duration,
                 'source_predictions':str(record.relative_to(ROOT)),'predictions_sha256':sha(record),
                 'background_sha256':sha(SOURCE/s['background']),
                 'models':['solver_residual','solver_learned_weights'],'reference_visible':True,
                 'source':'Original frozen solver run before central-floor/height experiments',
                 'animation':'Reveal saved path point i at each GIF frame; fixed first camera image; no new inference',
                 'locked_test_scene_diagnostic_only':ep==837}
        receipts.append(receipt)
        cards.append(f'<article><h2>Episode {ep} · {leg}</h2><p>{n} pairs · {total_duration/1000:.1f}s looping drawing</p><a href="{path.name}"><img src="{path.name}" alt="Solver paths drawing for episode {ep} {leg}"></a><p><a href="{path.name}" download>Download GIF</a> · <a href="{name}_final.png">Final PNG</a></p></article>')
        print('GIF_SAVED',path.name,decoded_count,'frames',round(path.stat().st_size/2**20,2),'MiB',flush=True)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Original solver drawing GIFs</title><style>*{box-sizing:border-box}body{background:#101b26;color:#edf4fa;font:16px system-ui,sans-serif;margin:0}main{max-width:1500px;margin:auto;padding:22px}p{line-height:1.5}a{color:#94ddff}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}article{background:#1b2c3c;padding:16px;border-radius:10px;min-width:0}img{width:100%;height:auto}@media(max-width:850px){.grid{grid-template-columns:1fr}}</style><main><h1>Original solver paths · drawing GIFs</h1><p>Orange: solver + correction. Purple: solver + learned weights. Pink: reference. The cyan neural model is omitted. Each GIF reveals the saved trajectories over the fixed first camera image. This is drawing playback, not moving-camera video. Original run before the height experiment.</p><p><a href="../START_HERE.html">Back to solver review</a></p><div class="grid">CARDS</div></main></html>'''
    (OUT/'index.html').write_text(page.replace('CARDS',''.join(cards)))
    (OUT/'manifest.json').write_text(json.dumps({'gifs':receipts,'all_frames_decode':True,
        'first_and_final_frames_match_rendered_paths':True,'training_performed':False,
        'new_inference_performed':False},indent=2)+'\n')
    (OUT/'README.md').write_text('# Original solver drawing GIFs\n\nOpen index.html. The four requested cases are478/leg03,753/leg11,837/leg00 and837/leg08.\n\nOnly the two solver predictions are displayed, with the pink reference for comparison. The camera image is fixed while saved trajectory points are revealed. Original checkpoint predictions and coordinates are unchanged; these are not height-experiment images. All GIF frames decode, loop durations and first/final rendered frames are verified.\n\nEpisode837 remains a locked-test-scene visualization; these GIFs do not select or fit any model settings. No training or inference ran.\n')


if __name__=='__main__':main()
