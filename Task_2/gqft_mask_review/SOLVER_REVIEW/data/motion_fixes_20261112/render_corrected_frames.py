"""Stage/render a new mesh-height recording; never overwrite the source frames.

Only unambiguous measured floor support is accepted. Original logged vertical
motion was lost, so the new agent_y is explicitly mesh-reconstructed geometry,
not a recovered original sensor log. Run --prepare-only without Habitat-Sim.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def prepare(poses_file,audit_file,target_height=1.2):
    audit=json.loads(audit_file.read_text())
    if hashlib.sha256(poses_file.read_bytes()).hexdigest()!=audit['poses_sha256']:
        raise ValueError('Height audit refers to a different pose file')
    with np.load(poses_file,allow_pickle=False) as z:data={k:z[k].copy() for k in z.files}
    rows=audit['frames']
    if len(rows)!=len(data['pose']):raise ValueError('Audit/pose frame counts disagree')
    bad=[i for i,r in enumerate(rows) if r['status']!='measured' or r['floor_y'] is None]
    if bad:
        raise ValueError(f'{len(bad)} frames have uncertain/changing support; inspect the audit before re-rendering. First indices: {bad[:12]}')
    floors=np.array([r['floor_y'] for r in rows],dtype=np.float64)
    if not np.isfinite(floors).all() or target_height<=0:raise ValueError('Invalid height plan')
    physical=json.loads(str(data['physical'].item()))
    physical['camera_position_agent']=[0.,float(target_height),0.]
    physical['mesh_floor_offset_applied']=True
    physical['camera_height_reference']='Measured local mesh support; per-frame agent_y'
    data.update(agent_y=floors,camera_y=floors+target_height,local_floor_y=floors,
                floor_y=np.array(floors[0]),physical=np.array(json.dumps(physical)),
                height_provenance=np.array('mesh-reconstructed counterfactual; original world-Y trace was not retained'))
    return data,physical


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--poses-file',type=Path,required=True)
    parser.add_argument('--audit-file',type=Path,required=True)
    parser.add_argument('--out-root',type=Path,required=True)
    parser.add_argument('--scene-root',type=Path,default=Path('/data/robotics/toshith/HSGM_public/data/scene_datasets'))
    parser.add_argument('--target-height',type=float,default=1.2)
    parser.add_argument('--gpu-logical',type=int,default=0)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--limit',type=int,default=0,help='Smoke render only; a limited render is explicitly incomplete')
    args=parser.parse_args()
    project=Path('/data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda')
    if project not in args.out_root.resolve().parents:
        raise ValueError('Server output must remain inside the authorized GQFT project')
    data,physical=prepare(args.poses_file,args.audit_file,args.target_height)
    out=args.out_root/'frames'/args.poses_file.stem
    poses_out=args.out_root/'poses'/args.poses_file.name
    if out.exists() or poses_out.exists():raise FileExistsError('Use a fresh output root; original evidence is preserved')
    out.mkdir(parents=True);poses_out.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(poses_out,**data)
    status={'episode':int(data['episode_id']),'original_poses_sha256':hashlib.sha256(args.poses_file.read_bytes()).hexdigest(),
            'audit_sha256':hashlib.sha256(args.audit_file.read_bytes()).hexdigest(),
            'target_mount_height_m':args.target_height,'frames_expected':len(data['pose']),
            'frames_rendered':0,'complete':False,'prepared_only':args.prepare_only,
            'height_source':'Mesh-reconstructed vertical trajectory; not the original lost world-Y log'}
    report=args.out_root/(args.poses_file.stem+'_render.json')
    report.write_text(json.dumps(status,indent=2)+'\n')
    if args.prepare_only:
        print('HEIGHT_PLAN_PREPARED',poses_out);return
    try:
        import habitat_sim
        import cv2
    except ImportError as error:
        raise RuntimeError('Height plan is prepared. Re-rendering needs the existing Habitat-Sim environment; no packages were installed.') from error
    cfg=habitat_sim.SimulatorConfiguration();cfg.scene_id=str(args.scene_root/str(data['scene'].item()))
    cfg.gpu_device_id=args.gpu_logical
    sensor=habitat_sim.SensorSpec();sensor.uuid='rgb';sensor.sensor_type=habitat_sim.SensorType.COLOR
    sensor.resolution=physical['resolution'];sensor.position=physical['camera_position_agent']
    sensor.orientation=[math.radians(a) for a in physical['camera_orientation_deg']]
    sensor.parameters['hfov']=str(physical['hfov_deg'])
    agent=habitat_sim.agent.AgentConfiguration();agent.sensor_specifications=[sensor]
    agent.height=physical['agent_height_m'];agent.radius=physical['agent_radius_m']
    sim=habitat_sim.Simulator(habitat_sim.Configuration(cfg,[agent]))
    state=habitat_sim.AgentState()
    try:
        count=min(len(data['pose']),args.limit or len(data['pose']))
        for i,(x,z,yaw) in enumerate(data['pose'][:count]):
            state.position=np.array([x,data['agent_y'][i],z],dtype=np.float32)
            state.rotation=habitat_sim.utils.common.quat_from_angle_axis(
                math.atan2(-math.cos(yaw),-math.sin(yaw)),np.array([0.,1.,0.]))
            sim.get_agent(0).set_state(state)
            rgb=sim.get_sensor_observations()['rgb'][:,:,:3]
            if not cv2.imwrite(str(out/f'{i:05d}.png'),rgb[:,:,::-1]):raise RuntimeError('Failed to save RGB')
            status['frames_rendered']=i+1
        status['complete']=status['frames_rendered']==status['frames_expected']
        report.write_text(json.dumps(status,indent=2)+'\n')
    finally:sim.close()
    print('CORRECTED_RENDER',json.dumps(status))


if __name__=='__main__':main()
