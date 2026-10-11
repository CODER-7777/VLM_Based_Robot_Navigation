from pathlib import Path
import sys,json,shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));import glb_tools as gt
from PIL import Image
review=json.loads((ROOT/'evidence/browser_review.json').read_text())
assert review['status']=='passed' and review['scene_sha256']==gt.sha(ROOT/'home_pbr_products.glb')
cat=json.loads((ROOT/'comparison/items/catalog.json').read_text())
out=ROOT/'comparison/items'
for item in cat['items']:
    src=ROOT/'evidence/browser'
    shutil.copy2(src/(item['id']+'_current.jpg'),out/item['render_image'])
    shutil.copy2(src/(item['id']+'_before.jpg'),out/(item['id']+'_before.jpg'))
    Image.open(src/(item['id']+'_full.png')).convert('RGB').save(out/item['room_image'],quality=95,subsampling=0)
    item['render_provenance']='Actual Three.js browser capture of this saved v7 room; calibrated dataset camera and crop. Earlier image is the recorded v6 browser capture.'
    if item['id'] in ['tea_tray','frother','coffee_machine']:
        fit=json.loads(Path(item['fit_paths'][0]).read_text());g,b=gt.read(Path(fit['glb']))
        indices={p['material'] for m in g['meshes'] for p in m['primitives']}
        item['materials']=[{'name':g['materials'][i].get('name'),'metallic':g['materials'][i].get('pbrMetallicRoughness',{}).get('metallicFactor',1),'roughness':g['materials'][i].get('pbrMetallicRoughness',{}).get('roughnessFactor',1),'colour_texture':'baseColorTexture' in g['materials'][i].get('pbrMetallicRoughness',{}),'normal_texture':'normalTexture' in g['materials'][i],'data_texture':'metallicRoughnessTexture' in g['materials'][i].get('pbrMetallicRoughness',{})} for i in sorted(indices)]
cat['validation'].update(browser='passed for saved scene hash',publication='staged')
(ROOT/'comparison/items/catalog.json').write_text(json.dumps(cat,indent=2))
html=ROOT/'web/comparison-first.html';s=html.read_text().replace('Earlier uses a saved OpenGL PBR render; current uses an actual Three.js browser capture of this repaired room.','Both earlier (v6) and current (v7) panels use actual Three.js browser captures.');html.write_text(s)
for name in ['placement_audit.json','artifact_verification.json']:
    p=ROOT/'evidence'/name;j=json.loads(p.read_text());assert j['scene_sha256']==review['scene_sha256'];j['browser_review']='passed for this saved scene hash'
    if name=='artifact_verification.json':j['limitations']=review['remaining_limits']
    p.write_text(json.dumps(j,indent=2))
print('ALL_23_COMPARISON_PANELS_STAGED',flush=True)
