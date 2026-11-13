"""Verify complete new frame sets and pose contracts, without GPU or writes to originals."""
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=Path(__file__).resolve().parent
    corrected=root/'height_corrected_v1'
    status=json.loads((root/'height_render_status.json').read_text())
    assert status['status']=='completed_safe_subset'
    rows=[]
    inputs=root/'height_corrected_center/inputs/poses';inputs.mkdir(parents=True,exist_ok=True)
    for p in sorted((corrected/'poses').glob('*.npz')):
        original=Path('/data/robotics/toshith/flowvo_compare/poses')/p.name
        with np.load(p,allow_pickle=False) as z,np.load(original,allow_pickle=False) as before:
            n=len(z['pose']);ep=int(z['episode_id'])
            frames=sorted((corrected/'frames'/p.stem).glob('*.png'))
            assert len(frames)==n and [f.name for f in frames]==['%05d.png'%i for i in range(n)]
            assert np.array_equal(z['pose'],before['pose']) and np.array_equal(z['leg_start'],before['leg_start'])
            assert np.isfinite(z['agent_y']).all() and np.allclose(z['agent_y'],z['local_floor_y'])
            assert np.allclose(z['camera_y']-z['local_floor_y'],1.2)
            a=json.loads(str(z['physical'].item()));b=json.loads(str(before['physical'].item()))
            for key in ['resolution','hfov_deg','camera_orientation_deg','agent_height_m','agent_radius_m']:
                assert a[key]==b[key]
            audit=json.loads((root/'height_audit_habitat'/('ep%d_height_audit.json'%ep)).read_text())
            assert sha(original)==audit['poses_sha256']
            assert all(item['status']=='measured' for item in audit['frames'])
            assert np.allclose(z['local_floor_y'],[item['floor_y'] for item in audit['frames']])
            render=json.loads((corrected/(p.stem+'_render.json')).read_text())
            assert render['complete'] and render['frames_rendered']==n
            shutil.copy2(p,inputs/p.name)
            rows.append({'episode':ep,'frames':n,'original_poses_sha256':sha(original),
                         'corrected_poses_sha256':sha(p),'render':render,
                         'checked':'Frame coverage, preserved X/Z/yaw/legs/camera intrinsics, finite support, 1.2m estimated clearance'})
    assert sorted(r['episode'] for r in rows)==sorted(status['completed'])
    # Snapshot original poses for the original-RGB intervention, too.
    original_inputs=root/'original_rgb_center/inputs/poses';original_inputs.mkdir(parents=True,exist_ok=True)
    for p in Path('/data/robotics/toshith/flowvo_compare/poses').glob('b10_A_drivefix_idx*.npz'):
        shutil.copy2(p,original_inputs/p.name)
    result={'passed':True,'episodes':len(rows),'frames':sum(r['frames'] for r in rows),
            'rows':rows,'scope':'Reconstructed-support consistency; not semantic floor certification'}
    (root/'height_dataset_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'episodes':len(rows),'frames':result['frames']}))


if __name__=='__main__':main()
