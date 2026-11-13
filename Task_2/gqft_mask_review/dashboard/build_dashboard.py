"""Build one offline HTML dashboard from preserved predictions; no inference."""
import base64
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
PILOT = '20261019T101035Z_431613'
VISUAL = LAB/'trained_episode_overlays'/PILOT/'20261019T123632Z'
VALIDATION = LAB/'pilot_results'/PILOT/'validation_20261019T104120Z'


def main():
    provenance = json.loads((VISUAL/'provenance.json').read_text())
    payload = {'provenance': provenance, 'legs': {}, 'validation': {},
               'training': {}, 'pilot': PILOT, 'visualization_run': VISUAL.name}
    source_files = [VISUAL/'provenance.json']
    for leg in (0, 2, 3, 4):
        folder = VISUAL/f'leg{leg:02d}'
        path = folder/'predictions.json'
        record = json.loads(path.read_text())
        source_files.append(path)
        record['images'] = {}
        for frame in (0, 12, 23):
            path = HERE/'assets'/f'leg{leg:02d}'/f'frame_{frame:02d}.png'
            source_files.append(path)
            record['images'][str(frame)] = 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
        record['attention'] = {}
        with np.load(folder/'attention_maps.npz', allow_pickle=False) as maps:
            for arm in provenance['checkpoints']:
                record['attention'][arm] = {}
                for key in ('attention_weights', 'feature_reliability', 'feature_valid_coverage', 'ground_prior_coverage'):
                    name = f'{arm}__{key}'
                    if name in maps:
                        array = maps[name][:, 0]
                        assert array.shape == (24, 6, 10), (name, array.shape)
                        record['attention'][arm][key] = np.round(array, 7).tolist()
        p = np.asarray(record['reference_displacement_m'])
        pitch = np.deg2rad(provenance['camera']['pitch_down_deg'])
        record['reference_ground'] = np.column_stack([-np.sin(pitch)*p[:, 1]+np.cos(pitch)*p[:, 2], -p[:, 0]]).tolist()
        for arm, prediction in record['predictions'].items():
            ground = np.linalg.norm(np.asarray(prediction['ground'])-record['reference_ground'], axis=1)*100
            pixel = np.linalg.norm(np.asarray(prediction['uv_px'])-record['reference_uv_px'], axis=1)
            prediction['ground_error_cm'] = ground.tolist()
            prediction['pixel_error_px'] = pixel.tolist()
            assert abs(ground[1:].mean()/100-record['metrics'][arm]['mean_ground_error_m']) < 1e-10
        payload['legs'][str(leg)] = record
    for arm in provenance['checkpoints']:
        path = VALIDATION/f'{arm}.json'
        payload['validation'][arm] = json.loads(path.read_text())
        source_files.append(path)
        if arm != 'pretrained_yaw':
            path = VALIDATION.parent/arm/'metrics.jsonl'
            payload['training'][arm] = [x for line in path.read_text().splitlines()
                                       if (x := json.loads(line)).get('kind') == 'val']
            source_files.append(path)
    template = (HERE/'template.html').read_text()
    html = template.replace('/* APP_CSS */', (HERE/'app.css').read_text())
    html = html.replace('/* APP_DATA */', 'window.GQFT_DATA = '+json.dumps(payload, separators=(',', ':'), allow_nan=False).replace('</', '<\\/')+';')
    html = html.replace('/* APP_JS */', (HERE/'app.js').read_text())
    assert all(marker not in html for marker in ('/* APP_CSS */', '/* APP_DATA */', '/* APP_JS */'))
    output = LAB/'dashboard.html'
    output.write_text(html)
    (HERE/'build_manifest.json').write_text(json.dumps({
        'output': str(output.relative_to(LAB)), 'bytes': output.stat().st_size,
        'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'sources': {str(path.relative_to(LAB)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
        'episode': 629, 'legs': [0, 2, 3, 4], 'models': list(provenance['checkpoints']),
        'training_or_inference_performed': False}, indent=2)+'\n')
    print(f'Built {output} ({output.stat().st_size:,} bytes); all data and images embedded.')


if __name__ == '__main__':
    main()
