"""Check an unchanged legacy replay before producing height counterfactuals."""
import json
import math
import os
from pathlib import Path

import cv2
import habitat_sim
import numpy as np


def main():
    project=Path('/data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda')
    out=project/'gqft_mask_review/motion_fixes_20261112/legacy_replay_smoke'
    out.mkdir(parents=True,exist_ok=False)
    poses=Path('/data/robotics/toshith/flowvo_compare/poses/b10_A_drivefix_idx3_20260829_114756.npz')
    z=np.load(poses,allow_pickle=False)
    physical=json.loads(str(z['physical'].item()))
    cfg=habitat_sim.SimulatorConfiguration()
    cfg.scene_id='/data/robotics/toshith/HSGM_public/data/scene_datasets/'+str(z['scene'].item())
    cfg.gpu_device_id=0
    sensor=habitat_sim.SensorSpec();sensor.uuid='rgb';sensor.sensor_type=habitat_sim.SensorType.COLOR
    sensor.resolution=physical['resolution'];sensor.position=physical['camera_position_agent']
    sensor.orientation=[math.radians(a) for a in physical['camera_orientation_deg']]
    sensor.parameters['hfov']=str(physical['hfov_deg'])
    ac=habitat_sim.agent.AgentConfiguration();ac.sensor_specifications=[sensor]
    ac.height=physical['agent_height_m'];ac.radius=physical['agent_radius_m']
    sim=habitat_sim.Simulator(habitat_sim.Configuration(cfg,[ac]))
    rows=[]
    try:
        for i in (0,139,337):
            x,zz,yaw=z['pose'][i];state=habitat_sim.AgentState()
            state.position=np.array([x,float(z['floor_y']),zz],dtype=np.float32)
            state.rotation=habitat_sim.utils.common.quat_from_angle_axis(
                math.atan2(-math.cos(yaw),-math.sin(yaw)),np.array([0.,1.,0.]))
            sim.get_agent(0).set_state(state)
            rgb=sim.get_sensor_observations()['rgb'][:,:,:3]
            cv2.imwrite(str(out/('%05d.png'%i)),rgb[:,:,::-1])
            original=cv2.imread('/data/robotics/toshith/flowvo_compare/frames/'+poses.stem+('/%05d.png'%i))[:,:,::-1]
            rows.append({'frame':i,'mean_absolute_rgb_error':float(np.abs(rgb.astype(float)-original).mean()),
                         'rgb_correlation':float(np.corrcoef(rgb.ravel(),original.ravel())[0,1]),
                         'sensor_world_position':list(map(float,sim.get_agent(0).get_state().sensor_states['rgb'].position))})
    finally:sim.close()
    result={'episode':629,'physical_gpu':os.environ.get('CUDA_VISIBLE_DEVICES'),
            'changed_camera_height':False,'frames':rows,
            'pass':all(r['rgb_correlation']>.98 and r['mean_absolute_rgb_error']<5 for r in rows)}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
