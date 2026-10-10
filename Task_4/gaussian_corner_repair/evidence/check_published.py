"""Test Reference view and RGB-D on an isolated CPU physics instance.

The live user's navigation state is never changed by the test actions.
"""
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.error import HTTPError
import os,json,subprocess,time,io
import numpy as np
from PIL import Image
W=Path('/data/robotics/toshith/rxr_author/refined/split_visuals');O=W/'corner_v2'
test_port=8782
def get(path,port=test_port):
 with urlopen(f'http://127.0.0.1:{port}'+path,timeout=60) as r:return r.read()
def action(name):
 request=Request(f'http://127.0.0.1:{test_port}/action',data=json.dumps({'action':name}).encode(),headers={'Content-Type':'application/json'})
 with urlopen(request,timeout=15) as r:return json.load(r)
live_before=json.loads(get('/state',8778))
resume=json.loads((W/'resume_pose.json').read_text())
assert np.allclose(live_before['c2w_raw_gl'],resume['c2w_raw_gl'],atol=1e-6),'Live camera was not preserved at publication'
env=dict(os.environ,CUDA_VISIBLE_DEVICES='4',MAGNUM_LOG='quiet',HABITAT_SIM_LOG='quiet',PHYSICS_DEMO_PORT=str(test_port),PHYSICS_VALIDATION_FILE='corner_v2/test_physics_validation.json')
with (O/'isolated_ui_test.log').open('w') as log:
 process=subprocess.Popen(['/home/guest-isl/rishabh/VLA-paper/.navida-env/bin/python','-u',str(W/'physics_corner_server.py')],cwd=str(W),env=env,stdout=log,stderr=log)
try:
 for _ in range(30):
  try:initial=json.loads(get('/state'));break
  except Exception:
   if process.poll() is not None:raise RuntimeError('Isolated physics test exited')
   time.sleep(.3)
 else:raise TimeoutError('Isolated test startup failed')
 left=action('left');assert not np.allclose(left['c2w_raw_gl'],initial['c2w_raw_gl'])
 state=action('reference')
 source=np.array(json.loads((W.parent/'toaster_selected/placement.json').read_text())['camera']['c2w'])
 error=float(np.abs(np.array(state['c2w_raw_gl'])-source).max());assert error<1e-5
 assert state['width']==800 and state['height']==640
 frame=state['frame_id'];rgb=get('/frame.jpg?frame_id='+str(frame));depth_data=get('/depth.npz?frame_id='+str(frame))
 depth=np.load(io.BytesIO(depth_data));assert Image.open(io.BytesIO(rgb)).size==(800,640)
 assert depth['depth_m'].shape==(640,800)
 assert np.allclose(depth['K'],state['K']) and np.allclose(depth['c2w_raw_gl'],state['c2w_raw_gl'])
 assert int(depth['frame_id'])==frame
 assert np.isnan(depth['depth_m'][~depth['valid']]).all()
 assert np.isfinite(depth['depth_m'][depth['valid']]).all()
 try:get('/depth.npz?frame_id='+str(initial['frame_id']));raise AssertionError('Stale frame accepted')
 except HTTPError as e:assert e.code==409
 info=json.loads(get('/render-info'))
 (O/'previews/reference_published.jpg').write_bytes(rgb)
 (O/'previews/reference_depth_published.png').write_bytes(get('/depth.png?frame_id='+str(frame)))
 live_after=json.loads(get('/state',8778));preserved=np.allclose(live_before['c2w_raw_gl'],live_after['c2w_raw_gl']) and live_before['frame_id']==live_after['frame_id']
 assert preserved,'Test changed live camera'
 report={'live_pose_preserved_on_publication':True,'live_pose_unchanged_by_isolated_test':True,'reference_button_passed':True,'reference_camera_max_error':error,'rgb_depth_pose_intrinsics_frame_agree':True,'stale_frame_rejected':True,'invalid_depth_is_nan':True,'resolution':[800,640],'reference_valid_depth_fraction':float(depth['valid'].mean()),'reference_cuda_raster_ms':info['cuda_raster_ms'],'reference_rpc_scope':'CUDA timer excludes image encoding and transfer'}
 (O/'published_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
finally:
 process.terminate()
 try:process.wait(timeout=5)
 except subprocess.TimeoutExpired:process.kill();process.wait()
