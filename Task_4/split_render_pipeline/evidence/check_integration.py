"""Meaningful camera synchronization, depth-unit and navigation API checks."""
import json,io,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import numpy as np
from PIL import Image
ROOT='http://127.0.0.1:8778'
OUT=Path(__file__).resolve().parent
def get(path):
 with urlopen(ROOT+path,timeout=60) as response:return response.read()
def act(action):
 with urlopen(Request(ROOT+'/action',data=json.dumps({'action':action}).encode(),headers={'Content-Type':'application/json'}),timeout=30) as response:return json.load(response)
initial=json.loads(get('/state'));frame=initial['frame_id']
rgb=get('/frame.jpg?frame_id='+str(frame));im=Image.open(io.BytesIO(rgb));assert im.size==(400,320)
depth=np.load(io.BytesIO(get('/depth.npz?frame_id='+str(frame))))
assert depth['depth_m'].shape==(320,400)
assert int(depth['frame_id'])==frame
assert np.allclose(depth['c2w_raw_gl'],initial['c2w_raw_gl'],atol=1e-7)
assert np.allclose(depth['K'],initial['K'])
assert np.isnan(depth['depth_m'][~depth['valid']]).all()
assert np.isfinite(depth['depth_m'][depth['valid']]).all()
assert (depth['depth_m'][depth['valid']]>.05).all()
left=act('left');assert left['frame_id']==frame+1
assert np.allclose(left['agent_position_habitat'],initial['agent_position_habitat'])
assert not np.allclose(np.asarray(left['c2w_raw_gl'])[:3,:3],np.asarray(initial['c2w_raw_gl'])[:3,:3])
restored=act('right');assert restored['frame_id']==frame+2
assert np.allclose(restored['c2w_raw_gl'],initial['c2w_raw_gl'],atol=1e-5)
try:get('/depth.npz?frame_id='+str(frame));raise AssertionError('Stale pose was accepted')
except HTTPError as exc:assert exc.code==409
begin=time.perf_counter();render=json.loads(get('/render-info'));roundtrip=(time.perf_counter()-begin)*1000
metrics=json.loads(get('/metrics'))
assert metrics['physics']['habitat_renderer_created'] is False
assert metrics['physics']['visual_sensors']==0
assert metrics['physics']['counter_wall_probe_blocked'] is True
report={'rgb_resolution':list(im.size),'initial_frame':frame,'restored_frame':restored['frame_id'],'pose_restored_after_left_right':True,'stale_frame_rejected':True,'rgb_depth_camera_synchronized':True,'depth_invalid_pixels_are_nan':True,'valid_depth_fraction':float(depth['valid'].mean()),'depth_definition':str(depth['depth_definition']),'warm_cuda_raster_ms_400x320':render['cuda_raster_ms'],'render_info_rpc_with_encoding_ms':roundtrip,'camera_transform_max_error':metrics['physics']['camera_transform_max_error'],'physics_has_no_visual_sensors':True,'counter_wall_collision_probe_passed':True}
(OUT/'integration.json').write_text(json.dumps(report,indent=2))
(OUT.parent/'images').mkdir(exist_ok=True)
(OUT.parent/'images/gaussian_rgb.jpg').write_bytes(get('/frame.jpg'))
(OUT.parent/'images/gaussian_depth.png').write_bytes(get('/depth.png'))
print(json.dumps(report,indent=2))
