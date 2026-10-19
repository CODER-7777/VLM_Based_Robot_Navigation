"""Render four static RGB views at each original RxR goal panorama; no actions/policy."""
import argparse,json,math,os,hashlib,time
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image
import habitat_sim
from habitat_sim.utils.common import quat_from_angle_axis
ap=argparse.ArgumentParser();ap.add_argument('--inputs',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
ROOT=Path(args.out);ROOT.mkdir(parents=True,exist_ok=True)
SCENES=Path('/data/robotics/toshith/vln_baselines/data/scene_datasets/mp3d')
items=json.loads(Path(args.inputs).read_text());grouped=defaultdict(list)
for r in items:grouped[r['scan']].append(r)
results=[]
for scene,routes in grouped.items():
 cfg=habitat_sim.SimulatorConfiguration();cfg.scene_id=str(SCENES/scene/(scene+'.glb'));cfg.gpu_device_id=0
 sensor=habitat_sim.SensorSpec();sensor.uuid='rgb';sensor.sensor_type=habitat_sim.SensorType.COLOR;sensor.resolution=[512,512];sensor.position=[0,0,0];sensor.parameters['hfov']='90'
 ac=habitat_sim.agent.AgentConfiguration();ac.sensor_specifications=[sensor]
 print('LOAD',scene,flush=True)
 sim=None
 try:
  sim=habitat_sim.Simulator(habitat_sim.Configuration(cfg,[ac]));agent=sim.initialize_agent(0)
  for r in routes:
   folder=ROOT/f"{r['review_index']:02d}_{r['split']}_{scene}_path{r['path_id']}";folder.mkdir(exist_ok=True)
   raw=r['goal_position_mp3d'];eye=[raw[0],raw[2],-raw[1]]
   result=dict(r,goal_camera_eye_habitat=eye,scene_asset=cfg.scene_id,views=[],render_method='Static Habitat RGB from original GLB at original goal panorama camera center; zero sensor offset; no agent navigation, no policy, no added objects.',camera_hfov_degrees=90,sensor_resolution=[512,512],physical_gpu=0)
   for degrees in [0,90,180,270]:
    state=habitat_sim.AgentState();state.position=np.array(eye,dtype=np.float32);state.rotation=quat_from_angle_axis(-math.radians(degrees),np.array([0,1,0],dtype=np.float32));agent.set_state(state,reset_sensors=True)
    rgb=sim.get_sensor_observations()['rgb'];image=Image.fromarray(rgb[:,:,:3]);filename=f'goal_heading_{degrees:03d}.png';image.save(folder/filename)
    result['views'].append({'heading_degrees_mp3d':degrees,'path':str((folder/filename).relative_to(ROOT)),'sha256':hashlib.sha256((folder/filename).read_bytes()).hexdigest(),'pixel_mean':float(rgb[:,:,:3].mean()),'pixel_std':float(rgb[:,:,:3].std())})
   (folder/'goal_metadata.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));results.append(result)
   (ROOT/'render_manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
   print('DONE',r['review_index'],scene,r['path_id'],flush=True)
 except Exception as e:
  print('ERROR',scene,type(e).__name__,str(e),flush=True);raise
 finally:
  if sim is not None:sim.close()
print('COMPLETE',len(results),'routes',sum(len(x['views']) for x in results),'images',flush=True)
