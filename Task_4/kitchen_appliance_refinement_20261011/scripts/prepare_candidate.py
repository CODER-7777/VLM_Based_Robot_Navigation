"""Build a separate room and dashboard from the reviewed personal v6 scene."""
from pathlib import Path
import json, shutil, subprocess
OLD=Path('/data/robotics/toshith/vivekananda/kitchen_repair_20261011')
ROOT=Path('/data/robotics/toshith/vivekananda/kitchen_appliance_refinement_20261011')
PY='/data/robotics/toshith/envs/kitchen3d/bin/python'
REV='kitchen_workspace_v7_20261011'
for d in ['scripts','logs','web','comparison/items','evidence']:(ROOT/d).mkdir(parents=True,exist_ok=True)
shutil.copytree(OLD/'web',ROOT/'web',dirs_exist_ok=True)
shutil.copytree(OLD/'comparison/items',ROOT/'comparison/items',dirs_exist_ok=True)
shutil.copy2(OLD/'scripts/glb_tools.py',ROOT/'scripts/glb_tools.py')
shutil.copy2(OLD/'scripts/build_repairs.py',ROOT/'scripts/build_repairs.py')
rows=[{'id':'tea_tray','folder':'tea_tray_v7'},{'id':'frother','folder':'frother_v7'},{'id':'coffee_machine','folder':'coffee_machine2_v7'}]
(ROOT/'replacement_inventory.json').write_text(json.dumps(rows,indent=2))
s=(OLD/'scripts/merge_products.py').read_text()
s=s.replace("P=Path('/data/robotics/toshith/vivekananda/kitchen_repair_20261011')",'P=Path('+repr(str(ROOT))+')')
s=s.replace("source=R/'kitchen_product_replacements/home_pbr_products.glb'",'source=Path('+repr(str(OLD/'home_pbr_products.glb'))+')')
(ROOT/'scripts/merge_products.py').write_text(s)
subprocess.run([PY,str(ROOT/'scripts/merge_products.py')],check=True)
s=(OLD/'scripts/prepare_workspace.py').read_text()
start=s.index('def source_fit(');end=s.index('\ndef classify(',start)
s=s[:start]+'''def source_fit(stem,old):
 path=ROOT/'objects'/NEW[stem]/'fit.json' if stem in NEW else Path(old)
 return path.parent.name,json.loads(path.read_text()),path
'''+s[end:]
s=s.replace("NEW={'soap_bottle':'soap_bottle_v6','soap_dish_p':'soap_dish_p_v6','blue_jug':'blue_jug_v6','glass_kettle':'glass_kettle_v6','tv_remote':'tv_remote_v6','phone_dock':'phone_dock_v6'}","NEW={'tea_tray':'tea_tray_v7','frother':'frother_v7','coffee_machine2':'coffee_machine2_v7'}")
s=s.replace("(P/'private_manifest.json')",'Path('+repr(str(OLD/'private_manifest.json'))+')')
s=s.replace("(P/'comparison/items/catalog.json')",'Path('+repr(str(OLD/'comparison/items/catalog.json'))+')')
s=s.replace('kitchen_workspace_v6_20261011',REV)
(ROOT/'scripts/prepare_workspace.py').write_text(s)
subprocess.run([PY,str(ROOT/'scripts/prepare_workspace.py')],check=True)
cat=json.loads((ROOT/'comparison/items/catalog.json').read_text())
inv=json.loads((ROOT/'evidence/scene_inventory.json').read_text())
by={i['name']:i for i in inv['objects']}
stemmap={'coffee_machine':'coffee_machine2'}
for section in ['items','room_items']:
 for item in cat[section]:
  stem=stemmap.get(item['id'],item['id'])
  if stem not in ['tea_tray','frother','coffee_machine2']:continue
  row=by[stem];fit=json.loads(Path(row['fit_path']).read_text())
  item.update(fit_paths=[row['fit_path']],nodes=row['nodes'],bounds_raw=row['bounds_raw'],
              target_raw=[sum(x)/2 for x in zip(*row['bounds_raw'])],notes=fit['notes'],product=fit.get('product'),updated_in_revision=True,
              method=fit.get('method','Retained licensed mesh with texture-backed PBR finish'),mesh_parts=row['parts'])
  item['render_provenance']='Private candidate; actual browser validation pending.'
cat.update(revision=REV,source_scene=str(ROOT/'home_pbr_products.glb'),scene_refresh='Tea glaze export fix, smooth sugar jar, appliance PBR finish repairs')
(ROOT/'comparison/items/catalog.json').write_text(json.dumps(cat,indent=2))
s=(OLD/'products_dashboard.py').read_text().replace(str(OLD),str(ROOT)).replace('kitchen_workspace_v6_20261011',REV)
(ROOT/'products_dashboard.py').write_text(s)
s=(OLD/'scripts/verify_artifacts.py').read_text()
(ROOT/'scripts/verify_artifacts.py').write_text(s)
subprocess.run([PY,str(ROOT/'scripts/verify_artifacts.py')],check=True)
print('CANDIDATE_PREPARED',str(ROOT),flush=True)
