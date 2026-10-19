"""Prepare real scanned objects, align their base to measured counter normals."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
from PIL import Image

ROOT=Path(__file__).resolve().parent
probe=ROOT/'toiletries_probe'
camera=json.loads((probe/'cameras.json').read_text())[0]
matrix=np.array(camera['camera_to_world'])
depth=np.load(probe/'sink_front_depth.npy')
f=768/(2*math.tan(math.radians(37.5)))


def world(x,y):
    d=float(depth[y,x])
    if d<=0:return None
    return matrix[:3,:3] @ np.array([(x+.5-384)*d/f,-(y+.5-384)*d/f,-d])+matrix[:3,3]


placements=[];credits=[]
for name,pixel,source_name in [
    ('conditioner',(289,421),'Marc_Anthony_Skip_Professional_Oil_of_Morocco_Conditioner_with_Argan_Oil'),
    ('cream',(324,429),'Perricone_MD_Hypoallergenic_Firming_Eye_Cream_05_oz'),
]:
    x,y=pixel
    points=np.array([world(xx,yy) for yy in range(y-10,y+11) for xx in range(x-10,x+11) if world(xx,yy) is not None])
    points=points[(points[:,1]>.91)&(points[:,1]<.96)]
    center=points.mean(axis=0);_,_,vt=np.linalg.svd(points-center,full_matrices=False)
    normal=vt[-1]
    if normal[1]<0:normal=-normal
    residuals=(points-center)@normal
    assert len(points)>200 and np.quantile(abs(residuals),.95)<.008
    assert normal[1]>.98
    support=world(x,y)
    support=support-normal*np.dot(support-center,normal)
    scene=trimesh.load(ROOT/'assets'/name/'meshes/model.obj',force='scene')
    # GSO's MTL names texture.png without the relative materials/textures directory.
    # Resolve it explicitly; otherwise trimesh silently exports an untextured mesh.
    texture=Image.open(ROOT/'assets'/name/'materials/textures/texture.png').convert('RGB')
    for mesh in scene.geometry.values():
        assert mesh.visual.kind=='texture' and mesh.visual.uv is not None
        mesh.visual.material.image=texture
    # GSO source Z-up in metres; preserve physical scale and photographic texture.
    transform=np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1.]])
    scene.apply_transform(transform)
    bounds=scene.bounds.copy()
    scene.apply_translation([-bounds[:,0].mean(),-bounds[0,1],-bounds[:,2].mean()])
    output=ROOT/'assets'/(name+'.glb');scene.export(output)
    assert any(getattr(mesh.visual.material,'image',None) is not None for mesh in scene.geometry.values())
    meshes=[]
    for node in scene.graph.nodes_geometry:
        mat,key=scene.graph[node];mesh=scene.geometry[key].copy();mesh.apply_transform(mat);meshes.append(mesh)
    geometry=trimesh.util.concatenate(meshes)
    base=geometry.vertices[geometry.vertices[:,1]<.003]
    rotation=trimesh.geometry.align_vectors([0,1,0],normal)[:3,:3]
    # Rotate front toward the approach camera without changing its fitted up axis.
    yaw=Rotation.from_euler('y',90,degrees=True).as_matrix()
    rotation=rotation@yaw
    rotated=geometry.vertices@rotation.T
    shift=.0005-float((rotated@normal).min())
    translation=support+normal*shift
    q=Rotation.from_matrix(rotation).as_quat().tolist()
    gaps=(base@rotation.T+translation-center)@normal
    item=dict(object_id=name,asset='assets/'+name+'.glb',translation=translation.tolist(),rotation_xyzw=q,
        physical_height_m=float(scene.bounds[1,1]-scene.bounds[0,1]),
        support_pixel=list(pixel),support_position_habitat=support.tolist(),support_normal=normal.tolist(),
        support_plane_points=len(points),support_plane_p95_residual_m=float(np.quantile(abs(residuals),.95)),
        base_sample_count=len(base),base_plane_gap_min_median_max_m=np.quantile(gaps,[0,.5,1]).tolist(),
        surface='marble counter left of bathroom sink, MP3D region 20',
        measurement='RGB-D surface fit; static placement. Not a physics/contact-stability test.')
    placements.append(item)
    credits.append(dict(object_id=name,author='Google LLC',license='CC BY 4.0',
        source_url='https://app.gazebosim.org/GoogleResearch/fuel/models/'+source_name,
        download_url=f'https://fuel.gazebosim.org/1.0/GoogleResearch/models/{source_name}/tip/{source_name}.zip',
        source_zip_sha256=hashlib.sha256((ROOT/'assets'/(name+'.zip')).read_bytes()).hexdigest(),
        prepared_glb_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        modifications='Z-up to Y-up; centered base at origin; embedded original photographic texture; no scale change.'))
(ROOT/'placements.json').write_text(json.dumps(placements,indent=2))
(ROOT/'asset_credits.json').write_text(json.dumps(credits,indent=2))
print(json.dumps(placements,indent=2))
