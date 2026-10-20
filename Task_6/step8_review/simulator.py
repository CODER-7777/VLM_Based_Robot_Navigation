"""Transient Habitat review navigation. Never writes actions, frames, audio or video."""
from __future__ import annotations
import gzip
import io
import json
import math
import secrets
import time
from pathlib import Path

import numpy as np
import quaternion
import habitat_sim as hs
from PIL import Image, ImageDraw

from model import SCENE

GLB='/data/robotics/toshith/rxr_author/refined/v16p/2azQ1b91cZZ.glb'
RXR='/data/toshith/agentvln/data/datasets/RxR_VLNCE_v0/val_unseen/val_unseen_guide.json.gz'
ASSETS=Path(__file__).resolve().parent/'assets'

class Navigation:
    def __init__(self,catalog,glb=GLB):
        self.catalog=catalog;self.glb=glb;self.sessions={};self.props=[];self.base_frames={}
        cfg=hs.SimulatorConfiguration();cfg.scene_id=glb;cfg.allow_sliding=True;cfg.enable_physics=True
        specs=[]
        for uid,typ in [('rgb',hs.SensorType.COLOR),('depth',hs.SensorType.DEPTH)]:
            s=hs.CameraSensorSpec();s.uuid=uid;s.sensor_type=typ;s.resolution=[600,800];s.hfov=90;s.position=[0,1.25,0];specs.append(s)
        agent=hs.agent.AgentConfiguration(height=.88,radius=.18,sensor_specifications=specs,action_space={
            'w':hs.agent.ActionSpec('move_forward',hs.agent.ActuationSpec(amount=.25)),
            's':hs.agent.ActionSpec('move_backward',hs.agent.ActuationSpec(amount=.25)),
            'a':hs.agent.ActionSpec('turn_left',hs.agent.ActuationSpec(amount=15)),
            'd':hs.agent.ActionSpec('turn_right',hs.agent.ActuationSpec(amount=15)),
            'up':hs.agent.ActionSpec('look_up',hs.agent.ActuationSpec(amount=15)),
            'down':hs.agent.ActionSpec('look_down',hs.agent.ActuationSpec(amount=15))})
        self.sim=hs.Simulator(hs.Configuration(cfg,[agent]));self.agent=self.sim.get_agent(0)
        self.sim.pathfinder.load_nav_mesh(glb.replace('.glb','.navmesh'))
        with np.load(catalog.source/f'grid_{SCENE}.npz') as grid:
            self.map_mpp=float(grid['mpp']);self.map_origin=grid['origin'].copy();self.map_floors=grid['floor_y'].copy()
            self.map_shapes=[grid[f'level{i}'].shape for i in range(len(self.map_floors))]
        episodes=json.load(gzip.open(RXR))['episodes']
        self.episodes={str(e['instruction']['instruction_id']):e for e in episodes if SCENE in e['scene_id']}
        self.add_props()

    def ray_height(self,x,z,ceiling,minimum):
        # This build has no static-stage Bullet ray hits. Use its rendered depth,
        # which measures the actual visible scan rather than guessed semantic bounds.
        saved=self.agent.get_state()
        try:
            st=hs.AgentState();st.position=np.array([x,ceiling-1.25,z],np.float32)
            self.agent.set_state(st,reset_sensors=True)
            for _ in range(6):self.agent.act('down')
            depth=self.sim.get_sensor_observations()['depth'];y=ceiling-float(np.median(depth[298:303,398:403]))
            return y if minimum<=y<ceiling else None
        finally:self.agent.set_state(saved,reset_sensors=False)

    def add_props(self):
        # Scan semantic centers locate the support; downward rays set the actual surface height.
        # The source v16p asset and navmesh are never changed. All five props coexist in the simulator.
        support={
            'calculator':dict(item="Olivia's calculator",at='p118',xz=[18.22,-8.933],top=1.12,low=.55,yaw=0),
            'glasses':dict(item="Grandma's reading glasses",at='room14',xz=[29.05,.12],top=1.20,low=.65,yaw=0),
            'cleat':dict(item="Olivia's other cleat",at='foyer bench',xz=[16.0,-.4],top=1.10,low=.35,yaw=0),
            'crossword_book':dict(item="Grandma's crossword book",at='p45',xz=[-1.65,4.44],top=.87,low=.28,yaw=.25),
            'cardigan':dict(item="Grandma's cardigan",at='p45',xz=[-.88,4.60],top=.87,low=.28,yaw=-.2),
        }
        # Obtain the real foyer bench centre from the original semantic metadata.
        house=Path('/data/robotics/toshith/pixel_ekf/data/raw/matterport3d/mp3d')/SCENE/f'{SCENE}.house'
        cats={}
        for line in house.read_text().splitlines():
            t=line.split()
            if t and t[0]=='C':cats[int(t[1])]=t[3].replace('#',' ')
            elif t and t[0]=='O' and cats.get(int(t[3]))=='bench':
                x,y,z=float(t[4]),float(t[6]),-float(t[5])
                if 7.5<x<18.78 and -3.34<z<2.73 and y<1.3:
                    support['cleat']['xz']=[x,z];support['cleat']['top']=min(1.2,y+.45)
        tm=self.sim.get_object_template_manager();om=self.sim.get_rigid_object_manager()
        for name,p in support.items():
            x,z=p['xz'];y=self.ray_height(x,z,p['top'],p['low'])
            confirmed=y is not None
            if y is None:y=p['low']
            config=ASSETS/f'{name}.object_config.json'
            handle=tm.load_configs(str(config))[0]
            obj=om.add_object_by_template_id(handle);obj.motion_type=hs.physics.MotionType.KINEMATIC
            obj.translation=np.array([x,y+.008,z],np.float32);obj.rotation=quaternion_to_magnum(p['yaw'])
            obj.collidable=False
            self.props.append(dict(id=name,**p,position=[x,y+.008,z],support_ray_hit=confirmed,object_id=obj.object_id,
                                   model='procedural review prop; appearance needs human review'))

    def initialize(self,cid,blind=False):
        c=self.catalog.by_id[cid];ep=self.episodes[str(c['level1_instruction_id'])]
        route=ep['reference_path'];sub=c.get('sub');route=route[sub[0]:sub[1]+1] if sub else route
        st=hs.AgentState();st.position=np.array(c['start']['xyz'],np.float32)
        if sub:
            delta=np.array(route[1])-np.array(route[0]);yaw=math.atan2(-delta[0],-delta[2]);st.rotation=quaternion.from_rotation_vector([0,yaw,0])
        else:
            x,y,z,w=ep['start_rotation'];st.rotation=quaternion.quaternion(w,x,y,z)
        self.agent.set_state(st,reset_sensors=True)
        token=secrets.token_urlsafe(24)
        if len(self.sessions)>20:
            oldest=min(self.sessions,key=lambda t:self.sessions[t]['touched']);del self.sessions[oldest]
        self.sessions[token]=dict(case_id=cid,blind=blind,state=self.agent.get_state(),route=np.array(route),touched=time.monotonic(),steps=0)
        return token

    def act(self,token,action='none',overlays=False):
        session=self.sessions[token];c=self.catalog.by_id[session['case_id']]
        if action=='reset':
            fresh=self.initialize(session['case_id'],session['blind']);self.sessions[token]=self.sessions.pop(fresh);session=self.sessions[token]
        else:
            self.agent.set_state(session['state'],reset_sensors=False)
            if action!='none':self.agent.act(action);session['steps']+=1
        session['state']=self.agent.get_state();session['touched']=time.monotonic()
        obs=self.sim.get_sensor_observations();img=Image.fromarray(obs['rgb'][...,:3]);pos=np.array(session['state'].position)
        status=dict(recording=False,steps=session['steps'])
        if not session['blind']:
            status.update(position=pos.tolist(),goal_distance=float(np.linalg.norm(pos-np.array(c['end_xyz']))))
            if overlays:self.draw_route(img,obs['depth'],session['route'])
        return jpeg(img),status

    def locator(self,token):
        session=self.sessions[token]
        if session['blind']:raise PermissionError('The position map is for case review.')
        state=session['state'];pos=np.array(state.position)
        floor=int(np.argmin(np.abs(self.map_floors-pos[1])))
        img=Image.open(self.catalog.source/f'{SCENE}_floor{floor}.png').convert('RGB')
        rows,cols=self.map_shapes[floor]
        x=(pos[0]-self.map_origin[0])/self.map_mpp*img.width/cols
        y=(pos[2]-self.map_origin[2])/self.map_mpp*img.height/rows
        forward=quaternion.as_rotation_matrix(state.rotation)@np.array([0,0,-1])
        direction=np.array([forward[0]*img.width/cols,forward[2]*img.height/rows]);direction/=max(np.linalg.norm(direction),1e-9)
        dx,dy=direction;draw=ImageDraw.Draw(img)
        draw.ellipse((x-12,y-12,x+12,y+12),fill='#007bca',outline='white',width=3)
        draw.line((x,y,x+dx*32,y+dy*32),fill='#003e78',width=6)
        tip=np.array([x,y])+direction*38;back=tip-direction*14;side=np.array([-dy,dx])*8
        draw.polygon([tuple(tip),tuple(back+side),tuple(back-side)],fill='#003e78')
        label=('Ground floor' if floor==0 else 'Upstairs')+' - YOU ARE HERE (blue dot and arrow)'
        if abs(pos[1]-self.map_floors[floor])>.6:label+=' - Between floors: showing nearest floor'
        draw.rectangle((0,0,img.width,28),fill='white');draw.text((8,8),label,fill='#003e78')
        return jpeg(img)

    def draw_route(self,img,depth,route):
        pts=np.concatenate([np.linspace(a,b,max(2,int(np.linalg.norm(b-a)/.12))) for a,b in zip(route[:-1],route[1:])])
        cam=self.agent.get_state().sensor_states['rgb'];R=quaternion.as_rotation_matrix(cam.rotation)
        points=(pts+np.array([0,.05,0])-np.array(cam.position))@R;z=-points[:,2]
        with np.errstate(divide='ignore',invalid='ignore'):
            u=400+400*points[:,0]/z;v=300-400*points[:,1]/z
        d=ImageDraw.Draw(img)
        for x,y,zz in zip(u,v,z):
            if zz>.1 and 0<=x<800 and 0<=y<600 and zz<depth[int(y),int(x)]+.22:
                d.ellipse((x-3,y-2,x+3,y+2),fill=(48,205,160))

    def photo(self,name):
        saved=self.agent.get_state()
        try:
            if name.startswith('memory_'):
                mid=name.removeprefix('memory_').removesuffix('.jpg');m=next(m for m in self.catalog.week['moments'] if m['id']==mid);pose=m['view_pose']
                eye=np.array(pose['xyz']);yaw=math.radians(pose['yaw_deg'])
            elif name=='image_case07.jpg':
                p=next(p for p in self.props if p['id']=='cleat');target=np.array(p['position'])+[0,.04,0];eye=target+[0,.32,.32];yaw=0
            else:
                c=self.catalog.cases[int(name[10:12])-1];view=c['levels']['3']['image_view']
                # Reuse a verified memory camera (>= 2 m from this using case's end).
                matches=[m for m in self.catalog.week['moments'] if m.get('view')==view and m.get('view_pose')]
                room=int(view[4:]) if view.startswith('room') else self.catalog.places[view]['room']
                if not matches:matches=[m for m in self.catalog.week['moments'] if m.get('view')==f'room{room}' and m.get('view_pose')]
                if not matches:raise ValueError('No verified request-photo camera; needs visual review')
                pose=matches[0]['view_pose'];eye=np.array(pose['xyz'])
                if math.dist(eye[[0,2]],np.array(c['end_xyz'])[[0,2]])<2:raise ValueError('Request-photo camera is too near the route end')
                target=self.catalog.inventory['rooms'][str(room)]['nav'] if view.startswith('room') else self.catalog.places[view]['hp']
                delta=np.array(target)-eye;yaw=math.atan2(-delta[0],-delta[2])
            st=hs.AgentState();st.position=eye-[0,1.25,0];st.rotation=quaternion.from_rotation_vector([0,yaw,0]);self.agent.set_state(st,reset_sensors=True)
            if name=='image_case07.jpg':
                for _ in range(3):self.agent.act('down')
            im=Image.fromarray(self.sim.get_sensor_observations()['rgb'][...,:3])
            if name=='image_case07.jpg':im=im.crop((180,110,620,550)).resize((512,512))
            return jpeg(im)
        finally:self.agent.set_state(saved,reset_sensors=False)

    def inspect_prop(self,prop_id):
        p=next(p for p in self.props if p['id']==prop_id);saved=self.agent.get_state()
        try:
            target=np.array(p['position']);candidates=[]
            for dx,dz in [(0,.9),(0,-.9),(.9,0),(-.9,0)]:
                nav=np.array(self.sim.pathfinder.snap_point(target+[dx,-.7,dz]));
                if np.all(np.isfinite(nav)):
                    candidates.append((np.linalg.norm(nav[[0,2]]-(target+[dx,0,dz])[[0,2]]),nav))
            if not candidates:raise ValueError('No inspection position near prop')
            pos=min(candidates,key=lambda x:x[0])[1];delta=target-pos;yaw=math.atan2(-delta[0],-delta[2])
            st=hs.AgentState();st.position=pos;st.rotation=quaternion.from_rotation_vector([0,yaw,0]);self.agent.set_state(st,reset_sensors=True)
            for _ in range(2):self.agent.act('down')
            return jpeg(Image.fromarray(self.sim.get_sensor_observations()['rgb'][...,:3]))
        finally:self.agent.set_state(saved,reset_sensors=False)

def quaternion_to_magnum(yaw):
    import magnum as mn
    return mn.Quaternion.rotation(mn.Rad(yaw),mn.Vector3.y_axis())

def jpeg(img):
    b=io.BytesIO();img.save(b,format='JPEG',quality=90);return b.getvalue()
