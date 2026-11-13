"""Regenerate solver PNGs/HTML from versioned predictions and keyframes, CPU only.

No trained models, flow caches, external datasets or network access are used.
Existing PNGs are retained by the rendering helper. Source manifests describe the
original artifacts; font/library versions can change regenerated PNG byte hashes.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

LAB=Path(__file__).resolve().parent
OLD='trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z'
CONTROL='motion_fixes_20261112'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection',choices=['review','source','all'],default='review')
    parser.add_argument('--max-episodes',type=int,default=0,help='Partial smoke render into --smoke-out; never rewrites a run manifest')
    parser.add_argument('--smoke-out',type=Path)
    args=parser.parse_args()
    if args.max_episodes and (args.max_episodes<1 or args.smoke_out is None):
        parser.error('A positive --max-episodes requires a separate --smoke-out')
    roots=[]
    if args.collection in {'review','all'}:roots.append(LAB/'SOLVER_REVIEW/data')
    if args.collection in {'source','all'}:roots.append(LAB)
    for root in roots:
        for rel in [OLD,CONTROL+'/original_rgb_center',CONTROL+'/height_corrected_center']:
            run=root/rel
            if args.max_episodes:
                import shutil
                manifest=json.loads((run/'manifest.json').read_text());selected=manifest['episodes'][:args.max_episodes]
                dest=args.smoke_out.resolve()/('review' if root!=LAB else 'source')/Path(rel).name
                dest.mkdir(parents=True,exist_ok=False)
                for item in selected:
                    folder=run/('ep'+str(item['episode']))
                    target=dest/folder.name
                    for f in folder.rglob('*'):
                        if f.is_file() and f.suffix in {'.json','.jpg'}:
                            p=target/f.relative_to(folder);p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,p)
                manifest['episodes']=selected;manifest['expected_episode_count']=len(selected)
                manifest['expected_leg_count']=sum(e['legs'] for e in selected)
                (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');run=dest
            subprocess.run([sys.executable,'-B',str(LAB/'render_all_episode_overlays.py'),'--run',str(run)],check=True)
    print('Solver review rendering complete; all camera/pose/prediction inputs were preserved.')


if __name__=='__main__':main()
