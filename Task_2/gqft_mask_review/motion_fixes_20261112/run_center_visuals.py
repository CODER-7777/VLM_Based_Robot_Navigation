"""Produce frozen center-control predictions, verifying legacy cache reuse."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
OLD=PROJECT/'gqft_mask_review/episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z'
PILOT=PROJECT/'gqft_mask_review/ground_pilots/20261111T220751Z_gpu4'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name,data):
    out=ROOT/name
    subprocess.run([sys.executable,'-B',str(ROOT/'infer_all_episode_overlays.py'),
                    '--project',str(PROJECT),'--pilot',str(PILOT),'--source',str(ROOT/'source'),
                    '--out',str(out),'--data-root',str(data),'--device','cuda',
                    '--solver-control','center','--context-mode','chunked'],check=True)
    return out


def main():
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='4':raise RuntimeError('Only approved GPU4')
    original_data=Path('/data/robotics/toshith/flowvo_compare')
    old_manifest=json.loads((OLD/'manifest.json').read_text())
    weights_sha=sha(Path(old_manifest['flow_frontend']['weights']))
    assert weights_sha==old_manifest['flow_frontend']['weights_sha256']
    cache_root=PROJECT/'gqft_mask_review/full_episode_flow_cache_v2';cache_root.mkdir(exist_ok=True)
    receipts=[]
    # No cache migration is performed for corrected RGB. Original cache hashes
    # and corresponding pose hashes must match the completed original gallery.
    for e in old_manifest['episodes']:
        r=json.loads((OLD/e['data']).read_text());pose=Path(r['poses_path'])
        assert pose.parent==original_data/'poses' and sha(pose)==r['poses_sha256']
        source=PROJECT/'gqft_mask_review/full_episode_flow_cache_v1'/(pose.stem+'.npz')
        assert sha(source)==r['flow_cache_sha256']
        identity=hashlib.sha256((str(original_data.resolve())+sha(pose)+weights_sha).encode()).hexdigest()[:20]
        target=cache_root/(pose.stem+'_'+identity+'.npz')
        if not target.exists():os.link(source,target)
        assert sha(target)==r['flow_cache_sha256']
        receipts.append({'episode':e['episode'],'cache_sha256':sha(target),'pose_sha256':sha(pose),
                         'source':str(source),'target':str(target),'original_RGB_only':True})
    (ROOT/'original_cache_reuse.json').write_text(json.dumps(receipts,indent=2)+'\n')
    manifest={str(p.relative_to(ROOT/'source')):sha(p) for p in sorted((ROOT/'source').rglob('*.py'))}
    manifest['infer_all_episode_overlays.py']=sha(ROOT/'infer_all_episode_overlays.py')
    (ROOT/'VISUAL_SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    run('original_rgb_center',original_data)
    status=json.loads((ROOT/'height_render_status.json').read_text())
    if status['status']!='completed_safe_subset':raise RuntimeError('Height rendering is incomplete')
    run('height_corrected_center',ROOT/'height_corrected_v1')


if __name__=='__main__':main()
