"""Verify downloaded episode figures against hashes and the earlier frozen run."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    root = args.run.resolve()
    lab = Path(__file__).resolve().parent
    manifest = json.loads((root/'ARTIFACT_SHA256.json').read_text())
    for name, expected in manifest.items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, name
    provenance = json.loads((root/'provenance.json').read_text())
    pilot = Path(provenance['pilot']).name
    previous = json.loads((lab/'pilot_results'/pilot/'validation_20261019T104120Z/provenance.json').read_text())
    assert provenance['physical_gpu'] == 7 and provenance['history'] == 24
    for arm in ('reference', 'masked_only', 'yaw_local_only', 'masked_yaw_local'):
        assert provenance['checkpoints'][arm]['sha256'] == previous['arms'][arm]['checkpoints']['best.pt']['sha256'], arm
    assert provenance['checkpoints']['pretrained_yaw']['sha256'] == '40729f0f537c28e5b07565aba01133bb594c7781cc59eedf90bc3fafa939ee8d'
    comparisons = {}
    for leg in (0, 2, 3, 4):
        folder = root/f'leg{leg:02d}'
        result = json.loads((folder/'predictions.json').read_text())
        assert result['episode'] == 629 and result['leg'] == leg and result['history'] == 24
        assert len(result['reference_uv_px']) == 25 and len(result['predictions']) == 5
        reference = next((lab/'ep629'/f'leg{leg:02d}').glob('*/review.json'))
        old = json.loads(reference.read_text())['metrics']['unmasked']
        new = result['metrics']['pretrained_yaw']
        differences = {key: new[key]-old[key] for key in ('mean_ground_error_m','endpoint_ground_error_m','mean_pixel_error_px','endpoint_pixel_error_px')}
        assert abs(differences['mean_ground_error_m']) < 1e-5, differences
        assert abs(differences['endpoint_ground_error_m']) < 1e-5, differences
        assert abs(differences['mean_pixel_error_px']) < .01, differences
        assert abs(differences['endpoint_pixel_error_px']) < .01, differences
        comparisons[str(leg)] = differences
        assert len(list(folder.glob('*.png'))) == 10
    assert len(list(root.rglob('*.png'))) == 41
    evidence = {'artifact_hashes_verified': len(manifest), 'trained_checkpoint_hashes_match_validation': True,
                'original_checkpoint_reproduces_earlier_four_windows': True,
                'original_metric_differences': comparisons, 'png_count': 41, 'legs': [0,2,3,4]}
    (root/'verification.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
