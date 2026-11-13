"""Measure rendered camera clearance from scene triangles, without Habitat/GPU.

Absolute floor_y is not camera clearance. The legacy renderer places the camera
at floor_y + its 1.2m sensor offset, so actual clearance needs a mesh intersection.
Ambiguous, missing and changing-height support is reported rather than guessed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def mp3d_to_habitat(points):
    """Habitat's legacy MP3D GLB frame: source +Z up becomes world +Y.

    Fixed asset convention, not a fit: Asset.cpp creates CoordinateFrame(+Z,+Y),
    whose frame-to-world rotation is -90 degrees around X.
    https://github.com/facebookresearch/habitat-sim/blob/main/src/esp/assets/Asset.cpp
    """
    return np.stack([points[...,0],points[...,2],-points[...,1]],axis=-1)


class VerticalFloorIndex:
    """Uniform XZ bins for vertical intersections with floor-like triangles."""
    def __init__(self, triangles, cell=.5):
        t=np.asarray(triangles,dtype=np.float64)
        normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
        length=np.linalg.norm(normal,axis=1)
        keep=(length>1e-10)&(np.abs(normal[:,1])>=.7*length)
        self.t=t[keep];self.cell=cell;self.bins={};self.large=[]
        self.lo=self.t[:,:,[0,2]].min(axis=1);self.hi=self.t[:,:,[0,2]].max(axis=1)
        for i,(lo,hi) in enumerate(zip(self.lo,self.hi)):
            a=np.floor(lo/cell).astype(int);b=np.floor(hi/cell).astype(int)
            if np.prod(b-a+1)>4096:
                self.large.append(i);continue
            for x in range(a[0],b[0]+1):
                for z in range(a[1],b[1]+1):self.bins.setdefault((x,z),[]).append(i)

    def heights(self,x,z):
        ids=list(self.bins.get((math.floor(x/self.cell),math.floor(z/self.cell)),[]))+self.large
        if not ids:return np.empty(0)
        t=self.t[ids];p=np.array([x,z]);a=t[:,0][:,[0,2]]
        u=t[:,1][:,[0,2]]-a;v=t[:,2][:,[0,2]]-a;q=p-a
        det=u[:,0]*v[:,1]-u[:,1]*v[:,0]
        safe=np.where(np.abs(det)>1e-12,det,1.)
        b=(q[:,0]*v[:,1]-q[:,1]*v[:,0])/safe
        c=(u[:,0]*q[:,1]-u[:,1]*q[:,0])/safe
        valid=(np.abs(det)>1e-12)&(b>=-1e-7)&(c>=-1e-7)&(b+c<=1+1e-7)
        return (t[:,0,1]+b*(t[:,1,1]-t[:,0,1])+c*(t[:,2,1]-t[:,0,1]))[valid]

    def support(self,x,z,base_y,mount=1.2):
        floors=[];ambiguous=False
        for dx,dz in [(0,0),(.05,0),(-.05,0),(0,.05),(0,-.05)]:
            ys=self.heights(x+dx,z+dz)
            below_base=ys[(ys<=base_y+.25)&(ys>=base_y-3.)]
            below_camera=ys[(ys<=base_y+mount-.05)&(ys>=base_y-3.)]
            if not len(below_base):continue
            floor=float(below_base.max());floors.append(floor)
            if len(below_camera) and below_camera.max()-floor>.1:ambiguous=True
        if len(floors)<3:return {'floor_y':None,'camera_clearance_m':None,'status':'missing_support'}
        spread=max(floors)-min(floors);floor=float(np.median(floors))
        return {'floor_y':floor,'camera_clearance_m':float(base_y+mount-floor),
                'support_spread_m':float(spread),
                'status':'ambiguous_overhead_or_object' if ambiguous else ('changing_surface' if spread>.1 else 'measured')}


def audit(poses_root,scene_root,out,mesh_frame='mp3d_z_up'):
    import trimesh
    out.mkdir(parents=True,exist_ok=True)
    groups={}
    for f in sorted(poses_root.glob('*.npz')):
        with np.load(f,allow_pickle=False) as z:
            scene=str(z['scene'].item())
        groups.setdefault(scene,[]).append(f)
    report={'method':'Vertical mesh intersections at the footprint and four 5cm offsets; no trajectory-scale fitting',
            'legacy_renderer':'agent_y=floor_y from first leg; camera_y=agent_y+mount_offset',
            'absolute_floor_y_is_not_camera_height':True,'training_performed':False,'gpu_used':False,
            'mesh_frame':mesh_frame,'mesh_to_habitat':'(x,y,z)->(x,z,-y)' if mesh_frame=='mp3d_z_up' else 'identity',
            'coordinate_source':'https://github.com/facebookresearch/habitat-sim/blob/main/src/esp/assets/Asset.cpp',
            'episodes':[]}
    for scene,files in groups.items():
        mesh_path=scene_root/scene
        print('LOAD_MESH',str(mesh_path),flush=True)
        loaded=trimesh.load(str(mesh_path),force='scene',process=False,skip_materials=True)
        mesh=loaded.dump(concatenate=True) if isinstance(loaded,trimesh.Scene) else loaded
        triangles=mp3d_to_habitat(mesh.triangles) if mesh_frame=='mp3d_z_up' else mesh.triangles
        world_bounds=np.stack([triangles.min(axis=(0,1)),triangles.max(axis=(0,1))])
        index=VerticalFloorIndex(triangles)
        for path in files:
            with np.load(path,allow_pickle=False) as z:
                poses=z['pose'].copy();base=float(z['floor_y']);episode=int(z['episode_id'])
                physical=json.loads(str(z['physical'].item()));starts=z['leg_start'].copy()
            mount=float(physical['camera_position_agent'][1])
            rows=[index.support(float(p[0]),float(p[1]),base,mount) for p in poses]
            measured=[r['camera_clearance_m'] for r in rows if r['status']=='measured']
            summary={'episode':episode,'scene':scene,'pose_file':str(path),'legacy_agent_y':base,
                     'camera_mount_m':mount,'legacy_camera_world_y':base+mount,'frames':len(poses),
                     'status_counts':{key:sum(r['status']==key for r in rows) for key in sorted({r['status'] for r in rows})},
                     'clearance_median_m':float(np.median(measured)) if measured else None,
                     'clearance_p05_m':float(np.quantile(measured,.05)) if measured else None,
                     'clearance_p95_m':float(np.quantile(measured,.95)) if measured else None,
                     'height_mismatch_fraction_of_measured':float(np.mean(np.abs(np.array(measured)-mount)>.1)) if measured else None,
                     'source_mesh_bounds':np.asarray(mesh.bounds).tolist(),'habitat_mesh_bounds':world_bounds.tolist(),
                     'selection_scope':'Geometry audit only; episode837 remains excluded from model/threshold selection'}
            payload={'summary':summary,'frames':rows,'leg_start':starts.tolist(),
                     'poses_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            (out/f'ep{episode}_height_audit.json').write_text(json.dumps(payload,indent=2)+'\n')
            report['episodes'].append(summary)
            (out/'height_summary.json').write_text(json.dumps(report,indent=2)+'\n')
            print('HEIGHT',json.dumps(summary),flush=True)
        del index,mesh,loaded
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--poses-root',type=Path,required=True)
    parser.add_argument('--scene-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--mesh-frame',choices=['mp3d_z_up','habitat_y_up'],default='mp3d_z_up')
    args=parser.parse_args();audit(args.poses_root,args.scene_root,args.out,args.mesh_frame)
