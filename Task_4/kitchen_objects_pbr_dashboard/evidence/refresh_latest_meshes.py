"""Merge latest fitted static GLBs into a private scene without rebaking their materials."""
from pathlib import Path
import copy, hashlib, json, re, struct

R=Path('/data/robotics/toshith/rxr_author/refined')
T=R/'toaster_home_tour'
def read(path):
    with path.open('rb') as stream:
        magic,version,total=struct.unpack('<III',stream.read(12));assert magic==0x46546c67 and version==2
        n,kind=struct.unpack('<II',stream.read(8));assert kind==0x4e4f534a
        g=json.loads(stream.read(n));n,kind=struct.unpack('<II',stream.read(8));assert kind==0x004e4942
        binary=stream.read(n)
    return g,binary

source=T/'home_pbr.glb'
g,binary=read(source);data=bytearray(binary)
report={'source':str(source),'output':str(T/'home_pbr_items.glb'),'replacements':[],'unchanged_toaster_original_textures':True}
for slug,folder in [('blue_jug','blue_jug_v4'),('phone','phone_v4')]:
    path=R/'kitchen/objects'/folder/'world_pbr.glb';s,blob=read(path)
    assert not s.get('skins') and not s.get('animations'),'Only fitted static models supported'
    pattern=re.compile(r'^Kitchen_'+re.escape(slug)+r'_v\d+(?:_|$)')
    removed=[i for i,node in enumerate(g['nodes']) if pattern.match(node.get('name',''))]
    for scene in g['scenes']:scene['nodes']=[i for i in scene.get('nodes',[]) if i not in removed]
    for node in g['nodes']:
        if 'children' in node:node['children']=[i for i in node['children'] if i not in removed]
    padding=(-len(data))%4;data.extend(b'\0'*padding);binary_offset=len(data);data.extend(blob)
    keys=['bufferViews','accessors','images','samplers','textures','materials','meshes','nodes']
    offsets={key:len(g.setdefault(key,[])) for key in keys}
    for view in s.get('bufferViews',[]):
        value=copy.deepcopy(view);assert value.get('buffer',0)==0
        value['buffer']=0;value['byteOffset']=value.get('byteOffset',0)+binary_offset;g['bufferViews'].append(value)
    for accessor in s.get('accessors',[]):
        value=copy.deepcopy(accessor)
        if 'bufferView' in value:value['bufferView']+=offsets['bufferViews']
        if 'sparse' in value:
            for name in ['indices','values']:value['sparse'][name]['bufferView']+=offsets['bufferViews']
        g['accessors'].append(value)
    for image in s.get('images',[]):
        value=copy.deepcopy(image);assert 'bufferView' in value,'Embedded source image required'
        value['bufferView']+=offsets['bufferViews'];g['images'].append(value)
    g['samplers'].extend(copy.deepcopy(s.get('samplers',[])))
    for texture in s.get('textures',[]):
        value=copy.deepcopy(texture)
        if 'source' in value:value['source']+=offsets['images']
        if 'sampler' in value:value['sampler']+=offsets['samplers']
        for extension in value.get('extensions',{}).values():
            if isinstance(extension,dict) and 'source' in extension:extension['source']+=offsets['images']
        g['textures'].append(value)
    def material_indices(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key.endswith('Texture') and isinstance(item,dict) and 'index' in item:item['index']+=offsets['textures']
                else:material_indices(item)
        elif isinstance(value,list):
            for item in value:material_indices(item)
    for mat in s.get('materials',[]):
        value=copy.deepcopy(mat);material_indices(value);g['materials'].append(value)
    for mesh in s.get('meshes',[]):
        value=copy.deepcopy(mesh)
        for primitive in value['primitives']:
            for name in primitive['attributes']:primitive['attributes'][name]+=offsets['accessors']
            for target in primitive.get('targets',[]):
                for name in target:target[name]+=offsets['accessors']
            if 'indices' in primitive:primitive['indices']+=offsets['accessors']
            if 'material' in primitive:primitive['material']+=offsets['materials']
        g['meshes'].append(value)
    for node in s.get('nodes',[]):
        value=copy.deepcopy(node)
        if 'mesh' in value:value['mesh']+=offsets['meshes']
        if 'children' in value:value['children']=[i+offsets['nodes'] for i in value['children']]
        if 'name' in value and not value['name'].startswith('Kitchen_'):value['name']='Kitchen_'+folder+'_'+value['name']
        g['nodes'].append(value)
    # Fitted source files are standard glTF Y-up; the full scene is raw MP3D Z-up.
    roots=[i+offsets['nodes'] for i in s['scenes'][s.get('scene',0)]['nodes']]
    wrapper=len(g['nodes']);g['nodes'].append({'name':'Kitchen_'+folder+'_Yup_to_raw','rotation':[2**-.5,0,0,2**-.5],'children':roots})
    g['scenes'][g.get('scene',0)]['nodes'].append(wrapper)
    for key in ['extensionsUsed','extensionsRequired']:
        if key in s:g[key]=sorted(set(g.get(key,[])+s[key]))
    report['replacements'].append({'id':slug,'source_glb':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'old_parts_removed':len(removed),'new_mesh_parts':sum('mesh' in node for node in s['nodes']),'materials_preserved':True})

g['buffers']=[{'byteLength':len(data)}]
encoded=json.dumps(g,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);data.extend(b'\0'*((-len(data))%4))
size=12+8+len(encoded)+8+len(data);output=T/'home_pbr_items.glb'
with output.open('wb') as stream:
    stream.write(struct.pack('<III',0x46546c67,2,size));stream.write(struct.pack('<II',len(encoded),0x4e4f534a));stream.write(encoded);stream.write(struct.pack('<II',len(data),0x004e4942));stream.write(data)
report['bytes']=size
(T/'latest_mesh_refresh.json').write_text(json.dumps(report,indent=2));print('LATEST_MESHES_REFRESHED',report,flush=True)
