"""Verify the rendered transforms against depth planes and assemble review views."""
from pathlib import Path
import hashlib
import json
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'placed'
result = json.loads((OUT / 'placement_results.json').read_text())
planes = json.loads((ROOT / 'surface_planes.json').read_text())
vertices = np.load(ROOT / 'assets/normalized_vertices.npy')
checks = []
for item in result['objects']:
    q = item['rotation_xyzw']
    rotation = trimesh.transformations.quaternion_matrix([q[3], *q[:3]])[:3, :3]
    assert np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6)
    assert abs(np.linalg.det(rotation) - 1) < 1e-6
    points = vertices @ rotation.T + np.array(item['object_translation'])
    contacts = {}
    for name in ['seat', 'back']:
        plane = planes[item['object_id']][name]
        distances = points @ np.array(plane['normal']) + plane['offset']
        contacts[name] = {'minimum_m': float(distances.min()),
                          'body_2percent_clearance_m': float(np.quantile(distances, .02))}
        # Loose strap tips may enter the coarse soft cushion, not the main body.
        assert distances.min() > -.04
        assert abs(np.quantile(distances, .02) - (.001 if name == 'seat' else .002)) < 1e-5
    checks.append({'object_id': item['object_id'], 'depth_surface_contact': contacts,
                   'rotation_orthonormal': True, 'view_status': 'front and side previews inspected; awaiting user review'})

board = Image.new('RGB', (2048, 2152), 'white')
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 28)
for i, (filename, title) in enumerate([
    ('bag_brown_sofa_close_detail.png', 'Brown chair: lower seat cushion'),
    ('bag_pink_sofa_close_detail.png', 'Pink chair: against backrest'),
    ('bag_brown_sofa_side_detail.png', 'Brown chair: side/contact view'),
    ('bag_pink_sofa_side_detail.png', 'Pink chair: side/contact view'),
]):
    x, y = (i % 2)*1024, (i // 2)*1076
    ImageDraw.Draw(board).text((x+16, y+10), title, font=font, fill='black')
    board.paste(Image.open(OUT / filename).convert('RGB'), (x, y+52))
board.save(ROOT / 'replacement_preview.jpg', quality=95)
original = ROOT.parents[1] / 'rxr_28_goal_images/goal_images_28/04_val_seen_SN83YJsR3w2_path12519'
baseline = all(hashlib.sha256((original / f'goal_heading_{h:03d}.png').read_bytes()).digest()
               == hashlib.sha256((OUT / f'before_{h:03d}.png').read_bytes()).digest() for h in [0, 90, 180, 270])
assert baseline
report = {
    'status': 'revised candidate, not user-approved',
    'user_pose_preference': 'Lean against the back cushion',
    'confirmed_previous_error': 'The original brown support point was on an armrest, approximately 19 cm above the seat; corrected using overhead depth.',
    'model': 'WV_ArtDev / SmallpolyArt real backpack photogrammetry scan',
    'height_m': .40,
    'model_triangles': json.loads((ROOT / 'assets/cleanup_report.json').read_text())['retained_triangles'],
    'original_goal_baselines_unchanged': baseline,
    'placements': checks,
    'physical_settling_simulated': False,
    'new_contact_shadows_rendered': False,
    'dashboard_updated': False,
}
(ROOT / 'verification.json').write_text(json.dumps(report, indent=2)+'\n')
nav = json.loads((OUT / 'navigation_results.json').read_text())
(ROOT / 'scenario.json').write_text(json.dumps({
    'status': 'revised candidate, awaiting user visual review',
    'scene': 'SN83YJsR3w2', 'source_path_id': 12519,
    'asset': 'assets/canvas_backpack_baked_clean_40cm.glb',
    'objects': result['objects'], 'standing_goals': nav['goals'],
    'source_guide_length_m': 47.31053818616118,
}, indent=2)+'\n')
parent = ROOT.parent
old = json.loads((parent / 'verification.json').read_text())
old.update(status='superseded after user rejected model appearance and placement',
           confirmed_error='brown bag support point was on armrest, not lower seat', latest_revision='revision_02')
(parent / 'verification.json').write_text(json.dumps(old, indent=2)+'\n')
(parent / 'latest_revision.json').write_text(json.dumps({
    'revision': 'revision_02', 'preview': 'revision_02/replacement_preview.jpg',
    'scenario': 'revision_02/scenario.json', 'status': 'candidate pending user review',
}, indent=2)+'\n')
print('Both revised transforms checked; original baseline preserved; front/side review sheet saved.')
