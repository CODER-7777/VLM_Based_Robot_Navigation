"""Seat three retained sink fittings exactly on the slab in new private versions."""
from pathlib import Path
import copy, json, struct
import trimesh

R=Path('/data/robotics/toshith/rxr_author/refined');T=R/'toaster_home_tour'
spec=[('hot_tap_s4_style_v3','hot_tap_s4_style_v4'),('soap_pump_p_lathe_v3','soap_pump_p_lathe_v4'),('air_gap_p_lathe_v3','air_gap_p_lathe_v4')]
def read(path):
    with path.open('rb') as stream:
        stream.read(12);n,k=struct.unpack('<II',stream.read(8));g=json.loads(stream.read(n));n,k=struct.unpack('<II',stream.read(8));binary=stream.read(n)
    return g,binary
def write(path,g,binary):
    data=json.dumps(g,separators=(',',':')).encode();data+=b' '*((-len(data))%4);binary+=b'\0'*((-len(binary))%4)
    with path.open('wb') as stream:
        stream.write(struct.pack('<III',0x46546c67,2,28+len(data)+len(binary)));stream.write(struct.pack('<II',len(data),0x4e4f534a));stream.write(data);stream.write(struct.pack('<II',len(binary),0x004e4942));stream.write(binary)

for _,new in spec:
    if (R/'kitchen/objects'/new).exists():raise RuntimeError('Refusing to overwrite '+new)
stage,binary=read(T/'home_pbr_items.glb');updates=[]
for old,new in spec:
    src=R/'kitchen/objects'/old;dest=R/'kitchen/objects'/new;dest.mkdir()
    fit=json.loads((src/'fit.json').read_text());dz=.929-float(fit['base'][2])
    asset,blob=read(Path(fit['glb']))
    for index in asset['scenes'][asset.get('scene',0)]['nodes']:
        node=asset['nodes'][index]
        if 'matrix' in node:node['matrix'][13]+=dz
        else:
            translation=node.setdefault('translation',[0,0,0]);translation[1]+=dz
    write(dest/'world_pbr.glb',asset,blob)
    mesh=trimesh.load(Path(fit['world_mesh']),process=False);mesh.apply_translation([0,0,dz]);mesh.export(dest/'world.ply')
    fit=copy.deepcopy(fit);fit['name']=new;fit['glb']=str(dest/'world_pbr.glb');fit['world_mesh']=str(dest/'world.ply');fit['base'][2]=.929
    if 'delete_aabb' in fit:fit['delete_aabb'][1][2]+=dz
    fit['keep_below_z']=.929
    fit['placement_refinement']={'previous_fit':str(src/'fit.json'),'raise_m':dz,'reason':'seat flange bottom on final counter slab at 0.929 m'}
    (dest/'fit.json').write_text(json.dumps(fit,indent=2))
    count=0
    for node in stage['nodes']:
        if node.get('name','').startswith('Kitchen_'+old+'_'):
            if 'matrix' in node:node['matrix'][14]+=dz
            else:node.setdefault('translation',[0,0,0])[2]+=dz
            count+=1
    assert count>0
    updates.append({'fit_path':str(dest/'fit.json'),'fit':fit,'old_name':old,'raise_m':dz,'scene_parts_shifted':count})
write(T/'home_pbr_items.glb',stage,binary)
(T/'mount_fit_updates.json').write_text(json.dumps(updates,indent=2));print('MOUNTS_SEATED',[(u['fit']['name'],u['raise_m']) for u in updates],flush=True)
