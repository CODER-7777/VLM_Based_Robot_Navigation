"""Merge latest fitted static GLBs into a private scene without rebaking their materials."""
from pathlib import Path
import copy, hashlib, json, re, struct

R=Path('/data/robotics/toshith/rxr_author/refined')
T=R/'toaster_home_tour'
P=R/'kitchen_product_replacements'
def read(path):
    with path.open('rb') as stream:
        magic,version,total=struct.unpack('<III',stream.read(12));assert magic==0x46546c67 and version==2
        n,kind=struct.unpack('<II',stream.read(8));assert kind==0x4e4f534a
        g=json.loads(stream.read(n));n,kind=struct.unpack('<II',stream.read(8));assert kind==0x004e4942
        binary=stream.read(n)
    return g,binary


source_g,source_blob=read(T/'home_pbr_items.glb');final_g,final_blob=read(P/'home_pbr_products.glb')
toaster=[i for i,n in enumerate(source_g['nodes']) if n.get('name','').startswith('Kitchen_toaster_v4_') and 'mesh' in n];assert len(toaster)==11
images=set();mats=set()
for i in toaster:
 assert source_g['nodes'][i]==final_g['nodes'][i]
 mi=source_g['nodes'][i]['mesh'];assert source_g['meshes'][mi]==final_g['meshes'][mi]
 for prim in source_g['meshes'][mi]['primitives']:mats.add(prim['material'])
for i in mats:
 mat=source_g['materials'][i];assert mat==final_g['materials'][i]
 pbr=mat['pbrMetallicRoughness']
 for texture in [pbr['baseColorTexture'],pbr['metallicRoughnessTexture'],mat['normalTexture']]:images.add(source_g['textures'][texture['index']]['source'])
checks=[]
for i in images:
 assert source_g['images'][i]==final_g['images'][i]
 view=source_g['bufferViews'][source_g['images'][i]['bufferView']];lo=view.get('byteOffset',0);hi=lo+view['byteLength'];a=hashlib.sha256(source_blob[lo:hi]).hexdigest();b=hashlib.sha256(final_blob[lo:hi]).hexdigest();assert a==b;checks.append({'image':i,'sha256':a})
report={'original_toaster_parts':len(toaster),'original_texture_maps':checks,'all_original_toaster_geometry_materials_and_texture_bytes_preserved':True}
(P/'original_material_verification.json').write_text(json.dumps(report,indent=2));print(report)
