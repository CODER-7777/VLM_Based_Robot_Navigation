"""Assemble true rendered goal observations into contact sheets and a PDF."""
from pathlib import Path
import json,textwrap,zipfile,csv,hashlib
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent/'goal_images_28'
manifest=json.loads((ROOT/'render_manifest.json').read_text())
labels={405:'Garage wall / wires and storage',1662:'Lounge: fireplace, TV and nearby couch',4176:'Church altar / central aisle',4224:'Patio seating: sofa/chair annotations differ',5721:'Bedroom/door area; instruction variants differ',7512:'Patio entrance steps',11513:'Outdoor bench beside lion statues',12519:'Double-door threshold near living room',12976:'Outdoor terrace / pillars',13062:'White table and chair (Telugu instruction)',15009:'Kitchen/bin/telephone area',15391:'Garage storage / golf clubs',15740:'Closed yellow door at corridor end (Hindi)',15896:'Glass doorway after steps (Telugu)',720:'Bathroom bathtub / stool',859:'Garage car / cupboards',1119:'Upper-level loft: idol and floor cushions',1233:'Fireplace/window corner with flower-vase table',1505:'Garage car / lockers',4468:'Bathroom window / towel hanger',5255:'Powder-room doorway',5495:'Hallway side table beside a door',8364:'Upper-level loft: altar/window end',9789:'Garage doorway / lockers',9926:'Window/corner near fireplace and ornamental table',11065:'Study double doors / globe',11830:'Study double doors / globe',12136:'Garage: between car and pillar'}
font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
F=ImageFont.truetype(font_path,25);SM=ImageFont.truetype(font_path,18);TITLE=ImageFont.truetype(font_path,31)
pages=[];index=[]
for r in sorted(manifest,key=lambda x:x['review_index']):
 stem=f"{r['review_index']:02d}_{r['split']}_{r['scan']}_path{r['path_id']}"
 folder=ROOT/stem
 sheet=Image.new('RGB',(1080,1320),'#f6f7fa');d=ImageDraw.Draw(sheet)
 d.text((24,20),f"{r['review_index']:02d}  {r['scan']} / path {r['path_id']}",font=TITLE,fill='#172438')
 d.text((24,67),f"{r['split']} | original RxR guide route {r['route_length_m']:.2f} m",font=F,fill='#34435a')
 label=labels[r['path_id']];d.text((24,106),label,font=SM,fill='#34435a')
 status='Bag-storage routine is NOT verified.'
 if r['path_id']==5495:status='Plausible bag-location adaptation; no visible bag or verified routine.'
 d.text((24,140),status,font=SM,fill='#984c17')
 for i,v in enumerate(r['views']):
  image=Image.open(ROOT/v['path']).convert('RGB');assert image.size==(512,512)
  x=24+(i%2)*520;y=183+(i//2)*548
  sheet.paste(image,(x,y));d.text((x,y+516),f"Goal view: heading {v['heading_degrees_mp3d']} degrees",font=SM,fill='#34435a')
 d.text((24,1290),'Unmodified Matterport scene; exact RxR goal camera position.',font=SM,fill='#34435a')
 sheet.save(folder/'goal_contact_sheet.jpg',quality=92);pages.append(sheet)
 nearest=next((x for x in json.loads((ROOT.parent/'semantic_endpoint_checks.json').read_text()) if x.get('path_id')==r['path_id'] and x.get('scan')==r['scan']),{})
 image_rows=[]
 for v in r['views']:
  p=ROOT/v['path'];image_rows.append({'file':v['path'],'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 index.append({'review_index':r['review_index'],'split':r['split'],'scan':r['scan'],'path_id':r['path_id'],'route_length_m':r['route_length_m'],'goal_viewpoint':r['goal_viewpoint'],'endpoint_description':label,'schoolbag_status':status,'contact_sheet':str((folder/'goal_contact_sheet.jpg').relative_to(ROOT)),'views':image_rows})
# Full-resolution multi-page PDF: one route per page.
pages[0].save(ROOT/'all_28_goal_contact_sheets.pdf',save_all=True,append_images=pages[1:],resolution=120.0)
# Compact overview retains all four views for each route.
thumb_w,thumb_h=360,440
board=Image.new('RGB',(thumb_w*4,thumb_h*7),'white')
for i,page in enumerate(pages):
 thumb=page.resize((thumb_w,thumb_h),Image.Resampling.LANCZOS);board.paste(thumb,((i%4)*thumb_w,(i//4)*thumb_h))
board.save(ROOT/'overview_all_28.jpg',quality=93)
(ROOT/'goal_image_index.json').write_text(json.dumps(index,indent=2))
with (ROOT/'goal_image_index.csv').open('w',newline='') as f:
 keys=['review_index','split','scan','path_id','route_length_m','goal_viewpoint','endpoint_description','schoolbag_status','contact_sheet'];w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
 for row in index:w.writerow({k:row[k] for k in keys})
readme='''# Goal images for all 28 RxR validation routes >=40 m

These are all 28 long **RxR validation guide trajectories**, not 28 confirmed school-bag locations. Their 28 records share 26 distinct physical goal viewpoints. There are 14 seen and 14 unseen trajectories.

- **all_28_goal_contact_sheets.pdf**: 28 pages, one route per page, four full-size goal views.
- **overview_all_28.jpg**: compact overview of all routes and all four headings.
- Each numbered folder: four original RGB PNGs, a contact sheet, and full goal metadata/instruction variants.
- **goal_image_index.csv / .json**: exact split, scan, path, length, goal viewpoint, description and image hashes.
- **render_manifest.json**: complete rendering provenance, eye coordinates, image headings, original RxR instructions and paths.

The strongest hallway-table adaptation is **2azQ1b91cZZ / path 5495**, unseen, **41.476140 m**. No rendered backpack or routine of keeping children's school bags is established. Any school-bag habit must be explicitly authored as a new memory. Do not label every table, cabinet, bathroom or garage as a school-bag destination.

Images were rendered from the existing original Matterport `.glb` files using Habitat RGB only, with no navigation policy, image generation, added bag, or robot action. Views are 512x512, 90-degree horizontal field of view, at headings 0/90/180/270 degrees from Matterport +Y. The raw original goal camera center is converted from MP3D Z-up to Habitat Y-up as [x,z,-y]; sensor offset is zero. Images show reconstructed scene appearance, including mesh holes and texture artifacts. Length is original 3D viewpoint-path sum, not shortest-path or rollout length. The existing collector sample is preserved.

The endpoint descriptions summarize source instructions and semantic scene labels; bag-storage suitability remains a user-authored scenario decision. Sofa/chair wording differs between annotations for path 4224. All original language variants are retained in metadata.
'''
(ROOT/'README.md').write_text(readme)
# Single downloadable package, with original PNGs, route sheets, PDF, index and metadata.
zip_path=ROOT.parent/'rxr_28_goal_images.zip'
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
 for p in sorted(ROOT.rglob('*')):
  if p.is_file() and p.name!='rendered_goal_images.tar.gz':z.write(p,str(p.relative_to(ROOT.parent)))
print('Built',len(pages),'contact sheets,',sum(len(r['views']) for r in manifest),'PNG images, PDF and ZIP')
print('ZIP bytes',zip_path.stat().st_size)
