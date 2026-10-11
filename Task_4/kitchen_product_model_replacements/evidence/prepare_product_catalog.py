"""Read-only scene inventory; prepare real photos and cameras for object comparisons."""
from pathlib import Path
import json, re, shutil, struct
import numpy as np
from PIL import Image

R = Path('/data/robotics/toshith/rxr_author/refined')
T = R / 'toaster_home_tour'
P = R / 'kitchen_product_replacements'
OUT = P / 'comparison/items'
OUT.mkdir(parents=True,exist_ok=True)
OUT.mkdir(exist_ok=True)
PHOTO = Path('/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ/undistorted_color_images')
rows = json.loads((R / 'kitchen_all_upgrade/previews/gaussian_index.json').read_text())
fits = {row['fit']['name']: row for row in json.loads((R / 'kitchen_all_upgrade/published_fits.json').read_text())}
mount_updates = json.loads((T / 'mount_fit_updates.json').read_text()) if (T / 'mount_fit_updates.json').exists() else []
for row in mount_updates: fits[row['fit']['name']] = row
mapping = {
    'toaster': ['toaster_v4'], 'blue_jug': ['blue_jug_v4'], 'phone': ['phone_v4'],
    'canister_l': ['canister_l_v3'], 'canister_r': ['canister_r_v3'],
    'soap_bottle': ['soap_bottle_v3'], 'soap_dish': ['soap_dish_p_v3'],
    'hot_tap': ['hot_tap_s4_style_v4'] if mount_updates else ['hot_tap_s4_style_v3'], 'soap_pump': ['soap_pump_p_lathe_v4'] if mount_updates else ['soap_pump_p_lathe_v3'],
    'air_gap': ['air_gap_p_lathe_v4'] if mount_updates else ['air_gap_p_lathe_v3'], 'bottles': ['bottles_v30', 'bottles_v31', 'bottles_v32', 'bottles_v33'],
    'knife_block_round': ['knife_block_round_v3'], 'knife_block': ['knife_block_v3'],
    'caddy': ['caddy_v3'], 'frogs': ['frogs_v3'], 'paper_towel': ['paper_towel_v3'],
    'grinder': ['grinder_v3'], 'range_kettle': ['range_kettle_v3'],
    'tea_tray': ['tea_tray_v3'], 'glass_kettle': ['glass_kettle_v3'],
    'frother': ['frother_v3'], 'coffee_machine': ['coffee_machine2_v3'], 'coffee_can': [],
}
labels = {'blue_jug':'Blue jug / miniature creamer', 'phone':'Telephone', 'canister_l':'Left canister', 'canister_r':'Right canister', 'soap_pump':'Sink soap pump', 'air_gap':'Sink air gap', 'range_kettle':'Stovetop kettle', 'frogs':'Frog statues', 'caddy':'Wooden caddy', 'coffee_can':'Coffee can (retained scan)'}
notes = {
    'toaster':'Hamilton Beach substitute for the Black & Decker in the photograph. Original three PBR texture maps are preserved.',
    'blue_jug':'Photo-built miniature creamer, about 5.1 cm tall. Glazed finish; its handle, lip and unseen surfaces remain approximate.',
    'phone':'Downloaded desk-phone substitute with photo-fitted controls. Its handset and housing differ from the photographed telephone.',
    'canister_l':'Photo-built ceramic jar. Lid hardware and the printed motif remain approximate.',
    'canister_r':'Photo-built ceramic jar. Lid hardware and the printed motif remain approximate.',
    'soap_bottle':'Photo-built foam-pump bottle. Pump shape, translucency and label remain approximate.',
    'soap_dish':'Resized dish and soap to fit the narrow space behind the sink; smaller than the photographed dish.',
    'hot_tap':'Licensed style-matched faucet substitute. Its curved spout differs from the photographed tap.',
    'soap_pump':'Photo-traced and fitted pump with a metallic finish; unseen details remain approximate.',
    'air_gap':'Photo-traced fitted shape with metallic finish.',
    'bottles':'Four photo-traced bottles with photo-derived labels. Glass and unseen label details remain approximate.',
    'knife_block_round':'Photo-built block and handles. Exact knife profiles remain approximate.',
    'knife_block':'Photo-built wooden block and utensils. Handle shapes and wood details remain approximate.',
    'caddy':'Photo-built caddy with photo-derived decoration. Slats, joinery and partly hidden contents remain approximate.',
    'frogs':'Approximate proxy sculptures. The mesh is less faithful than parts of the earlier photo-trained Gaussian view.',
    'paper_towel':'Photo-built holder and roll. Paper seams and fine paper texture are not reconstructed.',
    'grinder':'Photo-built dark-wood grinder with separate metal parts. Its exact mechanism and wood grain remain approximate.',
    'range_kettle':'Licensed teakettle substitute with steel and plastic parts. It stands on the grates at 0.991 m.',
    'tea_tray':'Photo-built tray and accessories; exact decorative details remain approximate.',
    'glass_kettle':'Photo-built glass kettle. Transmission, liquid and internal reflections remain approximate.',
    'frother':'Photo-built frother with separate material regions; brand details remain approximate.',
    'coffee_machine':'Licensed Nespresso substitute fitted to the photo. Exact brand/model details and controls differ.',
    'coffee_can':'Retained photographic scan, with no separate repaired mesh. It is included for comparison and inspection; it has not been upgraded to a product model.',
}

for product_row in json.loads((P/'replacement_inventory.json').read_text()):
    slug=product_row['id']; folder=product_row['folder']; fp=R/'kitchen/objects'/folder/'fit.json'
    fit=json.loads(fp.read_text()); fits[folder]={'fit':fit,'fit_path':str(fp)}
    mapping[slug]=[folder]; notes[slug]=product_row['notes']
SCENE = P / 'home_pbr_products.glb'
with SCENE.open('rb') as stream:
    stream.read(12)
    length, kind = struct.unpack('<II', stream.read(8))
    assert kind == 0x4e4f534a
    g = json.loads(stream.read(length))

def local_matrix(node):
    if 'matrix' in node:
        return np.array(node['matrix']).reshape(4, 4, order='F')
    matrix = np.eye(4)
    x,y,z,w = node.get('rotation', [0,0,0,1])
    rotation = np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)], [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)], [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
    matrix[:3,:3] = rotation @ np.diag(node.get('scale', [1,1,1]))
    matrix[:3,3] = node.get('translation', [0,0,0])
    return matrix

world = {}
def visit(index, parent):
    node = g['nodes'][index]
    world[index] = parent @ local_matrix(node)
    for child in node.get('children', []): visit(child, world[index])
for index in g['scenes'][g.get('scene',0)]['nodes']: visit(index, np.eye(4))

def bounds(indices):
    all_points = []
    for index in indices:
        for primitive in g['meshes'][g['nodes'][index]['mesh']]['primitives']:
            accessor = g['accessors'][primitive['attributes']['POSITION']]
            low, high = accessor['min'], accessor['max']
            corners = np.array([[x,y,z,1] for x in [low[0],high[0]] for y in [low[1],high[1]] for z in [low[2],high[2]]])
            all_points.extend((corners @ world[index].T)[:,:3])
    points = np.array(all_points)
    return [points.min(0).tolist(), points.max(0).tolist()]

cameras = {}
for line in (PHOTO.parent/'undistorted_camera_parameters/2azQ1b91cZZ.conf').read_text().splitlines():
    tokens = line.split()
    if tokens and tokens[0] == 'intrinsics_matrix':
        K = np.array(list(map(float,tokens[1:]))).reshape(3,3)*.625
        K[2,2] = 1
    elif tokens and tokens[0] == 'scan':
        cameras[tokens[2]] = {'K':K.tolist(), 'c2w_raw_gl':np.array(list(map(float,tokens[3:19]))).reshape(4,4).tolist(), 'width':800, 'height':640}

catalog = []
for row in rows:
    name = row['name']
    if name == 'coffee_can':
        # The fitted frother occupies this old crop; do not present it as a
        # repaired coffee-can model or as retained scan geometry.
        continue
    fit_rows = [fits[n] for n in mapping[name]]
    stems = {re.sub(r'_v\d+$','',n) for n in mapping[name]}
    patterns = [re.compile(r'^Kitchen_' + re.escape(stem) + r'_v\d+(?:_|$)') for stem in stems]
    indices = [i for i,node in enumerate(g['nodes']) if i in world and 'mesh' in node and any(pattern.match(node.get('name','')) for pattern in patterns)]
    if fit_rows and not indices: raise RuntimeError('No mesh parts found for ' + name)
    material_ids = sorted({primitive['material'] for i in indices for primitive in g['meshes'][g['nodes'][i]['mesh']]['primitives']})
    material_info = []
    for i in material_ids:
        mat = g['materials'][i]
        pbr = mat.get('pbrMetallicRoughness',{})
        material_info.append({'name':mat.get('name'), 'metallic':pbr.get('metallicFactor',1), 'roughness':pbr.get('roughnessFactor',1), 'colour_texture':'baseColorTexture' in pbr, 'normal_texture':'normalTexture' in mat, 'data_texture':'metallicRoughnessTexture' in pbr, 'unlit':'KHR_materials_unlit' in mat.get('extensions',{})})
    photo = row['photo']
    source = PHOTO/photo
    destination = OUT/photo
    if not destination.exists(): shutil.copy2(source, destination)
    crop = row['box']
    real = Image.open(source).convert('RGB')
    real.crop(tuple(round(v*1.6) for v in crop)).save(OUT/(name+'_real.jpg'),quality=95)
    bounds_raw = bounds(indices) if indices else None
    if bounds_raw:
        target = np.mean(bounds_raw,axis=0).tolist()
    else:
        # Retained coffee-can appearance: target its photo centre at counter height.
        camera = cameras[photo];m=np.array(camera['c2w_raw_gl']);k=np.array(camera['K']);x=(crop[0]+crop[2])/2;y=(crop[1]+crop[3])/2
        ray=m[:3,:3]@np.array([(x-k[0,2])/k[0,0],-(y-k[1,2])/k[1,1],-1.])
        target=(m[:3,3]+ray*((1.02-m[2,3])/ray[2])).tolist()
    product = next((f['fit'].get('product') for f in fit_rows if f['fit'].get('product')),None)
    if product and not product.get('url') and product.get('uid'):
        product=dict(product,url='https://sketchfab.com/3d-models/'+product['uid'])
    catalog.append({'id':name,'label':labels.get(name,name.replace('_',' ').title()),'photo':photo,'camera':cameras[photo],'crop':crop,
        'fit_paths':[str(f['fit_path']) for f in fit_rows], 'product':product,
        'method':'downloaded product, fitted and adapted' if product else ('photo-built fitted mesh' if fit_rows else 'retained scan'),
        'notes':notes[name], 'nodes':[g['nodes'][i]['name'] for i in indices], 'mesh_parts':len(indices), 'bounds_raw':bounds_raw,'target_raw':target,
        'counter_z':.991 if name=='range_kettle' else (.935 if name in ['tea_tray','glass_kettle','frother','coffee_machine','coffee_can'] else .929),
        'materials':material_info,'real_image':name+'_real.jpg','render_image':name+'_pbr.jpg','room_image':name+'_room.jpg', 'earlier_comparison':row['comparison']})

order=['toaster','blue_jug','phone','canister_l','canister_r','soap_bottle','soap_dish','bottles','paper_towel','caddy','knife_block','knife_block_round','grinder','range_kettle','hot_tap','soap_pump','air_gap','frogs','tea_tray','glass_kettle','frother','coffee_machine','coffee_can']
catalog.sort(key=lambda item:order.index(item['id']))
methods={'grinder':'photo-built grinder with licensed wood texture','hot_tap':'licensed spout with a photo-shaped stem','tea_tray':'licensed teapot with photo-built accessories','phone':'existing licensed phone with refined casing edges','coffee_machine':'existing licensed coffee machine with subdivided curved surfaces','frother':'licensed ribbed body with a photo-shaped base'}
changed_ids={row['id'] for row in json.loads((P/'replacement_inventory.json').read_text())}
for item in catalog:
    item['updated_in_revision']=item['id'] in changed_ids
    if item['id'] in methods:item['method']=methods[item['id']]

(OUT/'catalog.json').write_text(json.dumps({'revision':'kitchen_product_models_pbr_v2','items':catalog,'geometry_changed':True,'scene_refresh':'ten product and surface revisions, reviewed at photograph cameras','source_scene':str(SCENE)},indent=2))
print('CATALOG_READY',len(catalog),'views',len(cameras),'photo cameras',flush=True)
for item in catalog:
    print(item['id'],item['mesh_parts'],item['bounds_raw'],flush=True)
