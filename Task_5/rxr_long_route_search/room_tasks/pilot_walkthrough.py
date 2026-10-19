"""Plan and record an authored 2m-checkpoint Habitat pilot, separate from RxR truth."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image
import habitat_sim as hs
import magnum as mn
from habitat_sim.utils.common import quat_from_angle_axis

ap=argparse.ArgumentParser();ap.add_argument('--catalog',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True);ap.add_argument('--plan-only',action='store_true')
args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
CAT=json.loads(args.catalog.read_text());SCENE=CAT['scenes']['SN83YJsR3w2']
FPS=20;SPEED=.65;EYE_HEIGHT=1.5;TURN_SPEED=60.;FOV=85.;W,H=768,512


def dump(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False))
def raw_to_hab(p):return np.array([p[0],p[2],-p[1]],dtype=np.float32)
def eye(p):return np.array(p)+[0,EYE_HEIGHT,0]
def yaw_toward(a,b):
    d=np.array(b)-a;return math.atan2(-float(d[0]),-float(d[2]))
def angle_delta(a,b):return (b-a+math.pi)%(2*math.pi)-math.pi


cfg=hs.SimulatorConfiguration();cfg.scene_id=SCENE['scene_asset'];cfg.gpu_device_id=0;cfg.enable_physics=True
sensors=[]
for name,size,fov in [('rgb',[H,W],FOV),('cube',[512,512],90)]:
    spec=hs.SensorSpec();spec.uuid=name;spec.sensor_type=hs.SensorType.COLOR
    spec.resolution=size;spec.position=[0,0,0];spec.parameters['hfov']=str(fov);sensors.append(spec)
ac=hs.agent.AgentConfiguration();ac.sensor_specifications=sensors
sim=hs.Simulator(hs.Configuration(cfg,[ac]));agent=sim.initialize_agent(0)


def set_camera(position,yaw,pitch=0):
    state=hs.AgentState();state.position=np.array(position,dtype=np.float32)
    state.rotation=quat_from_angle_axis(yaw,np.array([0,1,0]))*quat_from_angle_axis(pitch,np.array([1,0,0]))
    agent.set_state(state,reset_sensors=True)


def snap_eye_raw(vp):
    p=raw_to_hab(SCENE['panoramas'][vp]['position'])-np.array([0,EYE_HEIGHT,0])
    floor=np.array(sim.pathfinder.snap_point(p),dtype=np.float64)
    if not np.isfinite(floor).all() or np.linalg.norm(floor-p)>.7:raise RuntimeError('Poor floor snap '+vp)
    return floor


def navpath(a,b):
    request=hs.ShortestPath();request.requested_start=np.array(a,dtype=np.float32);request.requested_end=np.array(b,dtype=np.float32)
    if not sim.pathfinder.find_path(request):raise RuntimeError('Disconnected pilot leg')
    p=np.array(request.points,dtype=float)
    if np.max(np.abs(p[:,1]+3.50855))>.6:raise RuntimeError('Pilot leaves the lower floor: '+json.dumps(dict(start=np.array(a).tolist(),end=np.array(b).tolist(),min_y=float(p[:,1].min()),max_y=float(p[:,1].max()),length=float(request.geodesic_distance))))
    return p,float(request.geodesic_distance)


def clean(points):
    keep=[points[0]]
    for p in points[1:]:
        if np.linalg.norm(np.array(p)-keep[-1])>1e-5:keep.append(p)
    return np.array(keep)


def sample(points,distance):
    lengths=np.linalg.norm(np.diff(points,axis=0),axis=1);cum=np.r_[0,np.cumsum(lengths)]
    j=min(len(lengths)-1,max(0,int(np.searchsorted(cum,distance,side='right')-1)))
    t=np.clip((distance-cum[j])/lengths[j],0,1)
    return points[j]+t*(points[j+1]-points[j]),j


def create_plan():
    anchors={
      '1':snap_eye_raw('8370742d6ac748fd81e4751d7cc8dd4c'),
      '2':snap_eye_raw('53e6ea6aa17b4876b3fc7835279e99c2'),
      '3':snap_eye_raw('81999e63ec744b079b238f6bb3662df4'),
      '4':snap_eye_raw('cc3a8c91626f4824ab02269b167c0ea1'),
      '5':np.array([-1.4202772378921509,-3.508549928665161,-15.5663480758667]),
      '6':snap_eye_raw('1ef91e17b2c1476b8e2b1da60321cd36'),
    }
    anchors['5']=np.asarray(sim.pathfinder.snap_point(anchors['5']),dtype=float)
    waypoints=['1','2','3','4','5','4','3','6'];segments=[];route=[];distance=0.;visits=[];outbound={}
    for i,label in enumerate(waypoints):
        if i==0:route=[anchors[label]];visits.append(dict(label=label,distance_m=0));continue
        prior=waypoints[i-1]
        if (label,prior) in outbound:p=outbound[(label,prior)][::-1].copy();length=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
        elif prior=='3' and label=='6':
            # Continue through the entry and onto the porch. The utility shortcut
            # in this scan requires a 68m upstairs detour and was rejected.
            mids=[anchors['3'],snap_eye_raw('4c1951ece37a4b79890b361cb320469a'),snap_eye_raw('c967dad1b34d45308a0c6c909f19620b'),snap_eye_raw('e3e9e67979e94b6e9f8cbb441dadc8da'),anchors['6']]
            parts=[navpath(a,b)[0] for a,b in zip(mids,mids[1:])];p=clean(np.vstack(parts));length=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
        else:p,length=navpath(anchors[prior],anchors[label]);outbound[(prior,label)]=p
        route.extend(p[1:]);segments.append(dict(from_anchor=prior,to_anchor=label,start_m=distance,length_m=length));distance+=length
        visits.append(dict(label=label,distance_m=distance))
    route=clean(route);length=float(np.linalg.norm(np.diff(route,axis=0),axis=1).sum())
    if length<40:raise RuntimeError(f'Pilot route is only {length:.3f}m; adjust anchors instead of claiming >=40m.')
    regular=list(np.arange(0,length,2.));regular.append(length)
    distances=sorted(set(round(float(d),6) for d in regular+[v['distance_m'] for v in visits]))
    checkpoints=[]
    for i,d in enumerate(distances):
        if checkpoints and d-checkpoints[-1]['distance_m']<.0001:
            checkpoints[-1]['anchor_labels'] += [v['label'] for v in visits if abs(v['distance_m']-d)<.0001];continue
        pos,j=sample(route,min(d,length));forward=route[min(j+1,len(route)-1)]
        if np.linalg.norm(forward-pos)<.001 and j+2<len(route):forward=route[j+2]
        yaw=yaw_toward(pos,forward)
        checkpoints.append(dict(id=f'C{i+1:02d}',distance_m=d,position_floor_habitat=pos.tolist(),
            position_camera_habitat=eye(pos).tolist(),yaw_radians=yaw,
            anchor_labels=[v['label'] for v in visits if abs(v['distance_m']-d)<.0001],
            regular_2m_checkpoint=any(abs(d-r)<.0001 for r in regular),panorama=None,video_time_s=None))
    for i,c in enumerate(checkpoints):
        c['id']=f'C{i+1:02d}'
        c['interval_path_m']=c['distance_m']-checkpoints[i-1]['distance_m'] if i else 0.
        c['interval_euclidean_m']=float(np.linalg.norm(np.array(c['position_floor_habitat'])-checkpoints[i-1]['position_floor_habitat'])) if i else 0.
    return dict(title='Environment 04 · side-excursion walkthrough',scene='SN83YJsR3w2',
        authored=True,source_rxr_path_id=12519,source_rxr_guide_length_m=47.31053818616118,
        route_length_m=length,route_floor_habitat=route.tolist(),anchor_floor_habitat={k:v.tolist() for k,v in anchors.items()},
        anchor_sequence=waypoints,anchor_visits=visits,legs=segments,checkpoints=checkpoints,
        camera=dict(height_m=EYE_HEIGHT,hfov_degrees=FOV,resolution=[W,H],fps=FPS),
        nominal_speed_m_s=SPEED,turn_speed_degrees_s=TURN_SPEED,
        inspection_anchor='5',inspection_rotation_degrees=360,physical_gpu=0,
        note='New navigable Habitat pilot. Source RxR length is a separate metric. Additional anchor checkpoints subdivide the regular 2m intervals.')


def place_props():
    tm=sim.get_object_template_manager()
    for i,prop in enumerate(SCENE['props']):
        handle='pilot_'+prop['id'];a=tm.create_new_template(handle,False);a.render_asset_handle=prop['asset'];a.collision_asset_handle=prop['asset']
        a.orient_up=mn.Vector3(0,1,0);a.orient_front=mn.Vector3(0,0,-1);a.scale=mn.Vector3(1)
        a.compute_COM_from_shape=False;a.com=mn.Vector3(0);a.requires_lighting=False;tm.register_template(a,handle)
        oid=sim.add_object_by_handle(handle,light_setup_key=hs.gfx.NO_LIGHT_KEY)
        sim.set_object_motion_type(hs.physics.MotionType.KINEMATIC,oid);q=prop['rotation_xyzw']
        sim.set_rotation(mn.Quaternion(mn.Vector3(*q[:3]),q[3]),oid);sim.set_translation(mn.Vector3(*prop['translation']),oid)
        sim.set_object_motion_type(hs.physics.MotionType.STATIC,oid)


def panorama(position,out):
    # Cubemap reprojection: longitude 0 faces Habitat -Z; north is +Y.
    width,height=2048,1024
    lon=(np.arange(width)+.5)/width*2*np.pi-np.pi;lat=np.pi/2-(np.arange(height)+.5)/height*np.pi
    co=np.cos(lat)[:,None];dx=co*np.sin(lon)[None,:];dy=np.broadcast_to(np.sin(lat)[:,None],(height,width));dz=-co*np.cos(lon)[None,:]
    directions=np.stack([dx,dy,dz],axis=-1);result=np.zeros((height,width,3),dtype=np.uint8);score=np.full((height,width),-1.)
    for yaw,pitch in [(0,0),(math.pi/2,0),(math.pi,0),(-math.pi/2,0),(0,math.pi/2),(0,-math.pi/2)]:
        set_camera(position,yaw,pitch);obs=sim.get_sensor_observations()['cube'][:,:,:3]
        q=quat_from_angle_axis(yaw,np.array([0,1,0]))*quat_from_angle_axis(pitch,np.array([1,0,0]))
        import quaternion
        rot=quaternion.as_rotation_matrix(q);local=directions@rot
        z=-local[:,:,2];valid=(z>0)&(z>=np.abs(local[:,:,0])-1e-6)&(z>=np.abs(local[:,:,1])-1e-6)&(z>score)
        mx=np.float32((local[:,:,0]/np.maximum(z,1e-6)+1)*256-.5)
        my=np.float32((1-local[:,:,1]/np.maximum(z,1e-6))*256-.5)
        sampled=cv2.remap(obs,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
        result[valid]=sampled[valid];score[valid]=z[valid]
    if np.any(score<0):raise RuntimeError('Panorama has unmapped directions')
    Image.fromarray(result).save(out,quality=94)


try:
    if not sim.pathfinder.is_loaded:raise RuntimeError('No existing navmesh')
    plan=create_plan();place_props();dump(args.out/'plan.json',plan)
    for label in ['1','3','5','6']:
        p=np.array(plan['anchor_floor_habitat'][label]);yaw=0 if label=='5' else yaw_toward(p,np.array(plan['anchor_floor_habitat']['5']))
        set_camera(eye(p),yaw);Image.fromarray(sim.get_sensor_observations()['rgb'][:,:,:3]).save(args.out/f'anchor_{label}.jpg')
    print('PLAN',plan['route_length_m'],'m',len(plan['checkpoints']),'checkpoints',flush=True)
    if not args.plan_only:
        points=np.array(plan['route_floor_habitat']);inspection=next(v['distance_m'] for v in plan['anchor_visits'] if v['label']=='5')
        length=plan['route_length_m'];timeline=[];current=points[0];yaw=yaw_toward(points[0],points[1]);distance=0.
        writer=cv2.VideoWriter(str(args.out/'walkthrough_source.avi'),cv2.VideoWriter_fourcc(*'MJPG'),FPS,(W,H))
        if not writer.isOpened():raise RuntimeError('Video encoder not available')
        def frame(pos,yaw,distance,event='walk'):
            set_camera(eye(pos),yaw);rgb=sim.get_sensor_observations()['rgb'][:,:,:3];writer.write(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
            timeline.append(dict(frame=len(timeline),time_s=len(timeline)/FPS,distance_m=float(distance),position_camera_habitat=eye(pos).tolist(),yaw_radians=float(yaw),event=event))
        def turn(pos,start,delta,distance,event):
            count=max(1,math.ceil(abs(math.degrees(delta))/TURN_SPEED*FPS))
            for i in range(1,count+1):frame(pos,start+delta*i/count,distance,event)
            return start+delta
        destinations=sorted(set([0.,inspection,length]+[float(d) for d in np.arange(SPEED/FPS,length,SPEED/FPS)]))
        for d in destinations:
            current,j=sample(points,d)
            look,_=sample(points,min(length,d+.65));target=yaw_toward(current,look) if np.linalg.norm(look-current)>.001 else yaw
            change=angle_delta(yaw,target);yaw+=np.clip(change,-math.radians(TURN_SPEED)/FPS,math.radians(TURN_SPEED)/FPS)
            frame(current,yaw,d)
            if abs(d-inspection)<1e-7:
                # Face the bag, inspect all directions, then face back along the branch.
                target=yaw_toward(current,np.array(SCENE['props'][1]['target'])-np.array([0,EYE_HEIGHT,0]))
                yaw=turn(current,yaw,angle_delta(yaw,target),d,'face_inspection_target')
                start_frame=len(timeline);yaw=turn(current,yaw,2*math.pi,d,'inspection_360')
                plan['inspection_video_interval_s']=[start_frame/FPS,len(timeline)/FPS]
                next_pos,_=sample(points,min(length,d+.2));return_yaw=yaw_toward(current,next_pos)
                yaw=turn(current,yaw,angle_delta(yaw,return_yaw),d,'turn_to_exit')
            if len(timeline)%200<2:print('VIDEO',len(timeline),'frames',round(d,1),'m',flush=True)
        writer.release()
        dump(args.out/'timeline.json',timeline)
        for c in plan['checkpoints']:
            closest=min(timeline,key=lambda f:abs(f['distance_m']-c['distance_m']))
            c['video_time_s']=closest['time_s'];c['video_frame']=closest['frame'];c['panorama']=c['id']+'_panorama.jpg'
            panorama(c['position_camera_habitat'],args.out/c['panorama'])
            set_camera(c['position_camera_habitat'],closest['yaw_radians'])
            Image.fromarray(sim.get_sensor_observations()['rgb'][:,:,:3]).save(args.out/(c['id']+'_forward.jpg'),quality=92)
            print('PANORAMA',c['id'],round(c['distance_m'],2),flush=True)
        plan.update(video='walkthrough.mp4',video_source='walkthrough_source.avi',video_duration_s=len(timeline)/FPS,frame_count=len(timeline),status='recorded; browser-compatible MP4 conversion pending')
        dump(args.out/'plan.json',plan)
        with (args.out/'checkpoints.csv').open('w') as f:
            writer_csv=csv.DictWriter(f,fieldnames=['id','distance_m','interval_path_m','interval_euclidean_m','video_time_s','regular_2m_checkpoint','panorama']);writer_csv.writeheader()
            for c in plan['checkpoints']:writer_csv.writerow({k:c[k] for k in writer_csv.fieldnames})
        print('COMPLETE',len(timeline),'frames',len(plan['checkpoints']),'panoramas',flush=True)
finally:sim.close()
