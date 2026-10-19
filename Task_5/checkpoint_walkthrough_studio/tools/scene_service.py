"""Isolated, on-demand Habitat inspector. All GL work stays on one worker thread.

No policy, robot control, collection, scene editing, or physics stepping is performed.
Only this service's simulator and camera are changed. One active scene on GPU 0.
"""
import argparse
import base64
import io
import json
import math
from pathlib import Path
import queue
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

import numpy as np
from PIL import Image

ap=argparse.ArgumentParser();ap.add_argument('--catalog',type=Path,required=True)
ap.add_argument('--port',type=int,default=8894);args=ap.parse_args()
CAT=json.loads(args.catalog.read_text());ROUTES={r['id']:r for r in CAT['routes']}
JOBS=queue.Queue(maxsize=12)
HEALTH=dict(status='starting',scene=None,physical_gpu=0,frames=0,error=None)


def raw_to_habitat(p):return np.array([p[0],p[2],-p[1]],dtype=np.float32)


class Inspector:
    def __init__(self):
        import habitat_sim as hs
        import magnum as mn
        from habitat_sim.utils.common import quat_from_angle_axis
        self.hs,self.mn,self.quat=hs,mn,quat_from_angle_axis
        self.sim=None;self.scene_id=None;self.route=None;self.variant=None
        self.eye=np.zeros(3);self.yaw=0.;self.pitch=0.;self.step=0
        self.object_ids=[];self.show_props=True;self.walked=0.;self.frame=0
        self.message='Choose an instance';HEALTH['status']='ready'

    def load_scene(self,scan):
        if self.scene_id==scan:return
        HEALTH.update(status='loading',scene=scan,error=None)
        if self.sim is not None:self.sim.close();self.sim=None
        data=CAT['scenes'][scan];hs=self.hs;mn=self.mn
        cfg=hs.SimulatorConfiguration();cfg.scene_id=data['scene_asset'];cfg.gpu_device_id=0;cfg.enable_physics=True
        sensor=hs.SensorSpec();sensor.uuid='rgb';sensor.sensor_type=hs.SensorType.COLOR
        sensor.resolution=[512,768];sensor.position=[0,0,0];sensor.parameters['hfov']='85'
        ac=hs.agent.AgentConfiguration();ac.sensor_specifications=[sensor]
        self.sim=hs.Simulator(hs.Configuration(cfg,[ac]));self.agent=self.sim.initialize_agent(0)
        self.scene_id=scan;self.object_ids=[]
        tm=self.sim.get_object_template_manager()
        for i,prop in enumerate(data['props']):
            if not Path(prop['asset']).is_file():raise FileNotFoundError(prop['asset'])
            handle='rxr_review_'+prop['id'];a=tm.create_new_template(handle,False)
            a.render_asset_handle=prop['asset'];a.collision_asset_handle=prop['asset']
            a.orient_up=mn.Vector3(0,1,0);a.orient_front=mn.Vector3(0,0,-1)
            a.scale=mn.Vector3(1);a.compute_COM_from_shape=False;a.com=mn.Vector3(0)
            a.requires_lighting=False;tm.register_template(a,handle)
            oid=self.sim.add_object_by_handle(handle,light_setup_key=hs.gfx.NO_LIGHT_KEY)
            if oid<0:raise RuntimeError('Could not instantiate '+prop['id'])
            self.sim.set_object_motion_type(hs.physics.MotionType.KINEMATIC,oid)
            q=prop['rotation_xyzw'];self.sim.set_rotation(mn.Quaternion(mn.Vector3(*q[:3]),q[3]),oid)
            self.sim.set_translation(mn.Vector3(*prop['translation']),oid)
            self.sim.set_object_motion_type(hs.physics.MotionType.STATIC,oid)
            self.object_ids.append((oid,prop))
        self.apply_props(self.show_props)
        HEALTH.update(status='ready',scene=scan)

    def apply_props(self,visible):
        self.show_props=bool(visible)
        for oid,prop in self.object_ids:
            self.sim.set_object_motion_type(self.hs.physics.MotionType.KINEMATIC,oid)
            self.sim.set_translation(self.mn.Vector3(*(prop['translation'] if visible else [-10000,-10000,-10000])),oid)
            self.sim.set_object_motion_type(self.hs.physics.MotionType.STATIC,oid)

    def look_at(self,target):
        delta=np.array(target)-self.eye;horizontal=float(np.linalg.norm(delta[[0,2]]))
        self.yaw=math.atan2(-float(delta[0]),-float(delta[2]))
        self.pitch=max(-1.25,min(1.25,math.atan2(float(delta[1]),horizontal)))

    def jump(self,index):
        self.step=max(0,min(len(self.variant['path'])-1,int(index)))
        self.eye=raw_to_habitat(self.variant['positions_raw'][self.step]);self.pitch=0.
        if self.step<len(self.variant['path'])-1:
            target=raw_to_habitat(self.variant['positions_raw'][self.step+1]);target[1]=self.eye[1];self.look_at(target)
        else:
            region=self.variant.get('riya_region')
            candidates=[o for o in CAT['scenes'][self.scene_id]['beds'] if o['region']==region]
            if candidates:self.look_at(raw_to_habitat(candidates[0]['center']))
            else:self.yaw=0.
        self.yaw=self.variant['yaws'][self.step]
        self.message='Exact authored checkpoint camera. Checkpoint jump is an inspection teleport.'

    def handle(self,command,payload):
        if command=='select':
            route=ROUTES[payload['route_id']]
            variant=next((v for v in route['variants'] if v['id']==payload.get('variant_id',route['default_variant'])),None)
            if variant is None:raise ValueError('Unknown variant')
            self.route=route;self.variant=variant;self.walked=0.
            self.show_props=bool(payload.get('show_props',True));self.load_scene(route['scan'])
            self.apply_props(self.show_props);self.jump(payload.get('step',0))
        elif self.sim is None:raise ValueError('Select an instance first')
        elif payload.get('route_id') and payload['route_id']!=self.route['id']:
            raise ValueError('The active inspection instance changed; reselect your route.')
        elif command=='step':self.jump(payload['index'])
        elif command=='props':self.apply_props(payload.get('visible',True))
        elif command=='jump':
            role=payload['role']
            if role=='start':self.jump(0)
            elif role=='goal':self.jump(len(self.variant['path'])-1)
            elif role=='pickup':
                if self.variant.get('pickup_index') is None:raise ValueError('This route has no assigned pickup waypoint')
                self.jump(self.variant['pickup_index'])
                # Look toward the actual placed sink props when available.
                if self.scene_id=='VFuaQ6m2Qom' and self.variant.get('pickup_region')==20:
                    self.eye=np.array([-18.5,1.55,-6.25],dtype=np.float32)
                    self.look_at([-19.9,.98,-6.68]);self.message='Toiletries inspection camera beside the downstairs sink.'
            elif role=='nora':
                region=payload.get('region',self.variant.get('nora_region'))
                data=CAT['scenes'][self.scene_id]
                beds=[b for b in data['beds'] if b['region']==region]
                pans=[p for p in data['panoramas'].values() if p['region']==region]
                if not pans:raise ValueError('No panorama in that candidate room')
                center=beds[0]['center'] if beds else data['regions'][str(region)]['position']
                eye=min(pans,key=lambda p:float(np.linalg.norm(np.array(p['position'])-center)))['position']
                self.eye=raw_to_habitat(eye);self.look_at(raw_to_habitat(center))
                self.message="Inspecting the proposed Nora room. This inspection jump is not allowed task navigation."
            elif role.startswith('prop:'):
                prop=next(p for p in CAT['scenes'][self.scene_id]['props'] if p['id']==role[5:])
                self.eye=np.array(prop['eye'],dtype=np.float32);self.look_at(prop['target']);self.message=prop['label']+' · placement inspection'
            else:raise ValueError('Unknown jump target')
        elif command=='look':
            self.yaw+=math.radians(max(-90,min(90,float(payload.get('yaw',0)))))
            self.pitch=max(-1.25,min(1.25,self.pitch+math.radians(float(payload.get('pitch',0)))))
        elif command=='action':
            action=payload['action'];amount=min(.4,max(.05,float(payload.get('step_m',.22))))
            if action in ('left','right'):self.yaw+=math.radians(10)*(1 if action=='left' else -1)
            elif action in ('up','down'):self.pitch=max(-1.25,min(1.25,self.pitch+math.radians(7)*(1 if action=='up' else -1)))
            elif action in ('forward','backward','strafe_left','strafe_right'):
                if not self.sim.pathfinder.is_loaded:raise ValueError('Scene has no loaded navmesh')
                direction=np.array([-math.sin(self.yaw),0,-math.cos(self.yaw)])
                if action=='backward':direction=-direction
                elif action=='strafe_left':direction=np.array([-math.cos(self.yaw),0,math.sin(self.yaw)])
                elif action=='strafe_right':direction=np.array([math.cos(self.yaw),0,-math.sin(self.yaw)])
                requested=self.eye-np.array([0,1.5,0])
                floor=np.asarray(self.sim.pathfinder.snap_point(requested),dtype=np.float32)
                if not np.isfinite(floor).all() or np.linalg.norm(floor-requested)>1.5:
                    self.message='No nearby navigable floor. Jump to a route step to resume walking.'
                else:
                    end=np.asarray(self.sim.pathfinder.try_step(floor,floor+direction*amount),dtype=np.float32)
                    if not np.isfinite(end).all():raise ValueError('Invalid navmesh step')
                    if self.variant.get('floor_level')==0 and abs(float(end[1])-self.variant['floor_y_habitat'])>self.variant.get('floor_height_tolerance_m',.4):
                        self.message='Ground-floor boundary: stair ascent is blocked for this tour.'
                    else:
                        distance=float(np.linalg.norm(end-floor));self.walked+=distance
                        self.eye=end+np.array([0,1.5,0]);self.message='Navmesh-constrained inspection walk' if distance>.015 else 'Blocked by the navmesh boundary'
            else:raise ValueError('Unknown movement action')
        elif command!='state':raise ValueError('Unknown command')
        return self.packet()

    def packet(self):
        state=self.hs.AgentState();state.position=np.asarray(self.eye,dtype=np.float32)
        state.rotation=self.quat(self.yaw,np.array([0,1,0]))*self.quat(self.pitch,np.array([1,0,0]))
        self.agent.set_state(state,reset_sensors=True)
        before=time.monotonic();rgb=self.sim.get_sensor_observations()['rgb'][:,:,:3]
        output=io.BytesIO();Image.fromarray(rgb).save(output,format='JPEG',quality=87)
        self.frame+=1;HEALTH['frames']=self.frame
        raw=[float(self.eye[0]),float(-self.eye[2]),float(self.eye[1])]
        pans=CAT['scenes'][self.scene_id]['panoramas']
        nearest=min(pans,key=lambda v:float(np.linalg.norm(np.array(pans[v]['position'])-raw)))
        return dict(route_id=self.route['id'],variant_id=self.variant['id'],scan=self.scene_id,
            frame=self.frame,image='data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode(),
            position_habitat=self.eye.tolist(),position_raw=raw,heading_degrees=(-math.degrees(self.yaw))%360,
            pitch_degrees=math.degrees(self.pitch),route_step=self.step,route_steps=len(self.variant['path']),
            nearest_room=pans[nearest]['region'],nearest_viewpoint=nearest,room_assignment='nearest annotated panorama; approximate',
            walked_m=self.walked,show_props=self.show_props,message=self.message,
            render_encode_ms=round((time.monotonic()-before)*1000,1),physical_gpu=0,inspection_only=True)


def worker():
    inspector=None
    while True:
        job=JOBS.get()
        try:
            if inspector is None:inspector=Inspector()
            job['result']=inspector.handle(job['command'],job['payload'])
            HEALTH['error']=None
        except Exception as error:
            traceback.print_exc();job['error']=str(error);HEALTH['error']=str(error)
            if HEALTH['status']=='loading':HEALTH['status']='error'
        finally:job['done'].set();JOBS.task_done()


class Handler(BaseHTTPRequestHandler):
    def send_json(self,status,data):
        body=json.dumps(data,allow_nan=False).encode();self.send_response(status)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass

    def do_GET(self):
        if self.path=='/health':return self.send_json(200,HEALTH)
        return self.send_json(404,dict(error='Unknown route'))

    def do_POST(self):
        command=self.path.strip('/')
        if command not in ('select','state','step','jump','props','look','action'):
            return self.send_json(404,dict(error='Unknown command'))
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>32768:raise ValueError('Request too large')
            payload=json.loads(self.rfile.read(length) or b'{}')
            job=dict(command=command,payload=payload,done=threading.Event())
            JOBS.put(job,timeout=2)
            if not job['done'].wait(180):return self.send_json(504,dict(error='Scene load timed out; check health before retrying'))
            if 'error' in job:return self.send_json(400,dict(error=job['error']))
            return self.send_json(200,job['result'])
        except Exception as error:return self.send_json(400,dict(error=str(error)))

    def log_message(self,fmt,*values):
        if self.path!='/health':print(fmt%values,flush=True)


if __name__=='__main__':
    threading.Thread(target=worker,daemon=True,name='habitat-inspection-renderer').start()
    print('RXR inspection service 127.0.0.1:'+str(args.port),flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
