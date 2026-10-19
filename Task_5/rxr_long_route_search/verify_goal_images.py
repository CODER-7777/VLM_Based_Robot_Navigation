from pathlib import Path
import json,zipfile,hashlib,subprocess,re
from PIL import Image
root=Path(__file__).resolve().parent;p=root/'goal_images_28'
manifest=json.loads((p/'render_manifest.json').read_text())
assert len(manifest)==28
assert {r['split'] for r in manifest}=={'val_seen','val_unseen'}
assert sum(r['split']=='val_seen' for r in manifest)==14
assert sum(len(r['views']) for r in manifest)==112
for r in manifest:
 assert r['route_length_m']>=40 and r['goal_viewpoint']==r['path'][-1]
 assert r['goal_camera_eye_habitat']==[r['goal_position_mp3d'][0],r['goal_position_mp3d'][2],-r['goal_position_mp3d'][1]]
 for v in r['views']:
  f=p/v['path'];assert Image.open(f).size==(512,512)
  assert hashlib.sha256(f.read_bytes()).hexdigest()==v['sha256']
info=subprocess.check_output(['pdfinfo',str(p/'all_28_goal_contact_sheets.pdf')],text=True)
pdf_pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1));assert pdf_pages==28
verification={'passed':True,'trajectories':28,'seen':14,'unseen':14,'distinct_physical_goal_viewpoints':26,'rendered_png_images':112,'pdf_pages':pdf_pages,'image_hashes_match':True,'camera_coordinate_conversion_checked':True,'all_goal_images_overview_visually_reviewed':True,'primary_sofa_contact_sheets_visually_reviewed':True,'schoolbag_storage_habits_verified':False}
(p/'image_verification.json').write_text(json.dumps(verification,indent=2))
(p/'rendered_goal_images.tar.gz').unlink(missing_ok=True)
zip_path=root/'rxr_28_goal_images.zip'
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
 for f in sorted(p.rglob('*')):
  if f.is_file():z.write(f,str(f.relative_to(root)))
with zipfile.ZipFile(zip_path) as z:
 assert sum(n.endswith('.png') for n in z.namelist())==112
 assert not any(n.endswith('rendered_goal_images.tar.gz') for n in z.namelist())
print(json.dumps(verification,indent=2));print('ZIP size MiB',round(zip_path.stat().st_size/1024**2,2))
