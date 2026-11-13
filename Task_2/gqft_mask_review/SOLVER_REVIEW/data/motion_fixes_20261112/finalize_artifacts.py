"""Verify intervention separation and freeze an inventory of local artifacts."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before=json.loads((OLD/'manifest.json').read_text())
    checks={};views=0
    for name in ['original_rgb_center','height_corrected_center']:
        run=ROOT/name;manifest=json.loads((run/'manifest.json').read_text())
        for arm,c in manifest['checkpoints'].items():
            assert c['sha256']==before['checkpoints'][arm]['sha256']
        for ep in manifest['episodes']:
            p=run/ep['data'];record=json.loads(p.read_text())
            assert sha(p)==ep['sha256']
            poses=run/'inputs/poses'/Path(record['poses_path']).name
            assert sha(poses)==record['poses_sha256']
            original=json.loads((OLD/ep['data']).read_text())
            if name=='original_rgb_center':
                assert record['flow_cache_sha256']==original['flow_cache_sha256']
                for a,b in zip(record['segments'],original['segments']):
                    assert a['reference']==b['reference']
                    assert a['predictions']['yaw_local_reference']==b['predictions']['yaw_local_reference']
            else:
                assert record['flow_cache_sha256']!=original['flow_cache_sha256']
                assert record['vertical_reference']=='mesh_reconstructed'
                for a,b in zip(record['segments'],original['segments']):
                    assert np.allclose(a['reference']['ground_m'],b['reference']['ground_m'],atol=1e-10,rtol=0)
                    assert a['reference']['yaw_rad']==b['reference']['yaw_rad']
            views+=len(record['segments'])
        v=json.loads((run/'verification.json').read_text())
        assert v['checks']['metrics_recomputed_from_saved_paths'] and v['checks']['all_rendered_pngs_decode']
        assert not v['checks']['browser_interaction_checks']['errors']
        checks[name]='Checkpoint/pose hashes, exact original reference/neural control, flow identity, metrics, PNG and UI verified'
    assert json.loads((ROOT/'comparison_verification.json').read_text())['passed']
    assert json.loads((ROOT/'height_dataset_verification.json').read_text())['passed']
    cpu=json.loads((ROOT/'cpu_verification.json').read_text());assert cpu['passed']==cpu['total']==18
    checks.update(trajectory_views=views,trajectory_pngs=1105,synthetic_cpu_checks=18,
                  height_data_frames=2880,training_performed=False,
                  scope='Artifact and intervention verification; does not certify generalization or pass history gate')
    (ROOT/'verification.json').write_text(json.dumps(checks,indent=2)+'\n')
    inventory={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*'))
               if p.is_file() and p.name not in {'ARTIFACT_SHA256.json'} and '__pycache__' not in p.parts}
    (ROOT/'ARTIFACT_SHA256.json').write_text(json.dumps(inventory,indent=2)+'\n')
    print(json.dumps({'passed':True,'views':views,'artifact_hashes':len(inventory)}))


if __name__=='__main__':main()
