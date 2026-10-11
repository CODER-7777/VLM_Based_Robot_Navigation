"""Prepare personal v8 presentation; retain the reviewed v7 source unchanged."""
from pathlib import Path
import json, shutil, subprocess
OLD=Path('/data/robotics/toshith/vivekananda/kitchen_appliance_refinement_20261011')
ROOT=Path('/data/robotics/toshith/vivekananda/kitchen_tray_background_repair')
PY='/data/robotics/toshith/envs/kitchen3d/bin/python'
REV='kitchen_workspace_v8_tray_20261011'
for d in ['scripts','web','comparison/items','evidence','logs']:(ROOT/d).mkdir(exist_ok=True,parents=True)
shutil.copytree(OLD/'web',ROOT/'web',dirs_exist_ok=True)
shutil.copytree(OLD/'comparison/items',ROOT/'comparison/items',dirs_exist_ok=True)
for name in ['glb_tools.py','build_repairs.py','verify_artifacts.py']:
    shutil.copy2(OLD/'scripts'/name,ROOT/'scripts'/name)
rows=[{'id':'tea_tray','folder':'tea_tray_v8'},{'id':'wall_tea_background','folder':'wall_tea_background_v8'}]
(ROOT/'replacement_inventory.json').write_text(json.dumps(rows,indent=2))
s=(OLD/'scripts/merge_products.py').read_text()
s=s.replace("P=Path("+repr(str(OLD))+")","P=Path("+repr(str(ROOT))+")")
s=s.replace("source=Path('/data/robotics/toshith/vivekananda/kitchen_repair_20261011/home_pbr_products.glb')","source=Path("+repr(str(ROOT/'cleaned_source.glb'))+")")
(ROOT/'scripts/merge_products.py').write_text(s)
subprocess.run([PY,str(ROOT/'scripts/merge_products.py')],check=True)
s=(OLD/'scripts/prepare_workspace.py').read_text()
s=s.replace("NEW={'tea_tray':'tea_tray_v7','frother':'frother_v7','coffee_machine2':'coffee_machine2_v7'}","NEW={'tea_tray':'tea_tray_v8'}")
s=s.replace('/data/robotics/toshith/vivekananda/kitchen_repair_20261011/private_manifest.json',str(OLD/'private_manifest.json'))
s=s.replace('/data/robotics/toshith/vivekananda/kitchen_repair_20261011/comparison/items/catalog.json',str(OLD/'comparison/items/catalog.json'))
s=s.replace('kitchen_workspace_v7_20261011',REV)
(ROOT/'scripts/prepare_workspace.py').write_text(s)
subprocess.run([PY,str(ROOT/'scripts/prepare_workspace.py')],check=True)
cat=json.loads((ROOT/'comparison/items/catalog.json').read_text())
inventory=json.loads((ROOT/'evidence/scene_inventory.json').read_text())['objects']
byfolder={x['folder']:x for x in inventory}
for item in cat['room_items']:
    selected=[byfolder['tea_tray_v8'] if item['id']=='tea_tray' else byfolder[Path(fp).parent.name] for fp in item['fit_paths']]
    lo=[min(x['bounds_raw'][0][k] for x in selected) for k in range(3)]
    hi=[max(x['bounds_raw'][1][k] for x in selected) for k in range(3)]
    item.update(fit_paths=[x['fit_path'] for x in selected],nodes=sum([x['nodes'] for x in selected],[]),bounds_raw=[lo,hi],target_raw=[(a+b)/2 for a,b in zip(lo,hi)],mesh_parts=sum(x['parts'] for x in selected))
fit=json.loads((ROOT/'objects/tea_tray_v8/fit.json').read_text())
for section in ['items','room_items']:
    for item in cat[section]:
        if item['id']=='tea_tray':
            item.update(notes=fit['notes'],method=fit['method'],product=fit['product'],updated_in_revision=True)
cat.update(revision=REV,scene_refresh='Closed smooth tea tray and bounded original scan-remnant / backsplash repair')
(ROOT/'comparison/items/catalog.json').write_text(json.dumps(cat,indent=2))
s=(OLD/'products_dashboard.py').read_text().replace(str(OLD),str(ROOT)).replace('kitchen_workspace_v7_20261011',REV)
(ROOT/'products_dashboard.py').write_text(s)
# Make the GLB-only comparison directly discoverable in every room page.
h=ROOT/'web/home-tour.html';s=h.read_text()
s=s.replace('<a href="/">Current photo comparisons</a>', '<a href="/home-tour?version=compare">GLB before / after home tour</a> · <a href="/">Photo comparisons</a>')
s=s.replace('Before — earlier saved mesh','Before — earlier scanned GLB').replace('Before / After — side by side','GLB before / after — same camera')
s=s.replace('After — repaired + 3D models','After — repaired GLB + 3D models')
h.write_text(s)
h=ROOT/'web/comparison-first.html';s=h.read_text()
s=s.replace('<body>','<body><p style="padding:12px 24px"><a href="/home-tour?version=compare"><strong>Open GLB before / after home tour — walk and rotate both scenes from the same camera</strong></a></p>',1)
h.write_text(s)
subprocess.run([PY,str(ROOT/'scripts/verify_artifacts.py')],check=True)
print('PRIVATE_V8_READY',flush=True)
