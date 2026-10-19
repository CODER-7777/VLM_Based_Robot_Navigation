"""Static 3D placement review; run in the server's existing Habitat environment."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
import habitat_sim as hs
import magnum as mn
from habitat_sim.utils.common import quat_from_magnum

ap=argparse.ArgumentParser()
ap.add_argument('--out',type=Path,required=True)
ap.add_argument('--placements',type=Path)
ap.add_argument('--scenario',type=Path)
args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
cfg=hs.SimulatorConfiguration()
cfg.scene_id='/data/robotics/toshith/vln_baselines/data/scene_datasets/mp3d/VFuaQ6m2Qom/VFuaQ6m2Qom.glb'
cfg.gpu_device_id=0;cfg.enable_physics=True
sensors=[]
for name,kind in [('rgb',hs.SensorType.COLOR),('depth',hs.SensorType.DEPTH)]:
    s=hs.SensorSpec();s.uuid=name;s.sensor_type=kind;s.resolution=[768,768]
    s.position=[0,0,0];s.parameters['hfov']='75';sensors.append(s)
ac=hs.agent.AgentConfiguration();ac.sensor_specifications=sensors
sim=hs.Simulator(hs.Configuration(cfg,[ac]));agent=sim.initialize_agent(0)
manifest=[]
try:
    if args.placements:
        placements=json.loads(args.placements.read_text())
        for i,item in enumerate(placements):
            tm=sim.get_object_template_manager();a=tm.create_new_template('toiletry_'+str(i),False)
            a.render_asset_handle=str((args.placements.parent/item['asset']).resolve())
            a.collision_asset_handle=a.render_asset_handle
            a.orient_up=mn.Vector3(0,1,0);a.orient_front=mn.Vector3(0,0,-1)
            a.compute_COM_from_shape=False;a.com=mn.Vector3(0,0,0)
            a.requires_lighting=False
            handle=tm.register_template(a)
            oid=sim.add_object_by_handle(tm.get_template_handle_by_ID(handle),light_setup_key=hs.gfx.NO_LIGHT_KEY)
            sim.set_object_motion_type(hs.physics.MotionType.KINEMATIC,oid)
            q=item.get('rotation_xyzw',[0,0,0,1])
            sim.set_rotation(mn.Quaternion(mn.Vector3(*q[:3]),q[3]),oid)
            sim.set_translation(mn.Vector3(*item['translation']),oid)
            sim.set_object_motion_type(hs.physics.MotionType.STATIC,oid)
            sim.set_object_semantic_id(6100+i,oid)
    cameras=[
        ('sink_front',[-18.5,1.55,-6.25],[-19.9,.98,-6.68]),
        ('sink_side',[-18.6,1.55,-7.3],[-19.9,.98,-6.68]),
        ('vanity_front',[-18.15,1.55,-4.8],[-19.85,.9,-4.7]),
        ('vanity_side',[-18.9,1.55,-3.5],[-19.85,.9,-4.7]),
    ]
    for name,eye,target in cameras:
        st=hs.AgentState();st.position=np.array(eye,dtype=np.float32)
        mat=mn.Matrix4.look_at(mn.Vector3(*eye),mn.Vector3(*target),mn.Vector3.y_axis())
        st.rotation=quat_from_magnum(mn.Quaternion.from_matrix(mat.rotation()))
        agent.set_state(st,reset_sensors=True)
        obs=sim.get_sensor_observations()
        Image.fromarray(obs['rgb'][:,:,:3]).save(args.out/(name+'.png'))
        np.save(args.out/(name+'_depth.npy'),obs['depth'])
        manifest.append(dict(name=name,eye=eye,target=target,hfov_degrees=75,resolution=[768,768],
                         camera_to_world=np.asarray(agent.scene_node.absolute_transformation()).tolist()))
    if sim.pathfinder.is_loaded:
        snaps=[]
        for name,eye,target in cameras:
            p=sim.pathfinder.snap_point(np.array(eye,dtype=np.float32))
            snaps.append(dict(name=name,camera_eye=eye,nearest_navmesh_point=np.asarray(p).tolist()))
        (args.out/'navmesh_probe.json').write_text(json.dumps(snaps,indent=2))
        if args.scenario:
            scenario=json.loads(args.scenario.read_text());nodes=[]
            for v,raw in zip(scenario['path'],scenario['positions_mp3d']):
                floor=np.array([raw[0],raw[2]-1.5,-raw[1]],dtype=np.float32)
                snapped=sim.pathfinder.snap_point(floor)
                nodes.append(dict(viewpoint=v,requested_floor=floor.tolist(),snapped_floor=np.asarray(snapped).tolist(),snap_distance_m=float(np.linalg.norm(snapped-floor))))
            edges=[]
            for i,(a,b) in enumerate(zip(nodes,nodes[1:])):
                query=hs.ShortestPath();query.requested_start=np.array(a['snapped_floor'],dtype=np.float32)
                query.requested_end=np.array(b['snapped_floor'],dtype=np.float32)
                found=bool(sim.pathfinder.find_path(query))
                edges.append(dict(index=i,start=a['viewpoint'],end=b['viewpoint'],found=found,
                    geodesic_m=float(query.geodesic_distance) if found else None,
                    points=[np.asarray(p).tolist() for p in query.points] if found else []))
            report=dict(nodes=nodes,edges=edges,all_adjacent_pairs_connected=all(e['found'] for e in edges),
                geodesic_edge_sum_m=sum(e['geodesic_m'] for e in edges) if all(e['found'] for e in edges) else None,
                warning='Independent floor snapping and edge connectivity only. Not a rolled-out episode, manipulation test, or continuous forbidden-room audit.')
            (args.out/'route_navmesh_check.json').write_text(json.dumps(report,indent=2))
    (args.out/'cameras.json').write_text(json.dumps(manifest,indent=2))
    print('COMPLETE',len(manifest),flush=True)
finally:
    sim.close()
