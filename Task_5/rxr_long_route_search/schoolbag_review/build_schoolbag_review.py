"""Persist the image-by-image review under the user's school-bag-place criterion."""
from pathlib import Path
import json,csv,os,shutil,zipfile,textwrap
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'goal_images_28'
index=json.loads((SOURCE/'goal_image_index.json').read_text())
# Reviewed all four displayed goal images in each original-resolution contact sheet.
# These are visual suitability judgments, not original RxR household-use labels.
observations={
1:['Office partition, computer monitor and desk.','White office desk and swivel chair.','Numbered office door and wall.','Office cubicles and chairs; no child-specific context.'],
2:['Exterior column and balustrade.','Closed exterior door and tiled corridor.','Exterior wall and window.','Long exterior corridor; no bag surface or seating at goal.'],
3:['Garden hedge and edge of stone seating.','Unreconstructed black area; this direction cannot support object identification.','Garden hedge and stone boundary.','Garden walkway, planters and outdoor stone seating.'],
4:['Pool table and armchair beyond a doorway.','Living-room armchairs across the threshold.','Living-room seating visible beyond the open floor.','Nearby lamp on an end table beside seating; partly occluded by doorway.'],
5:['Outdoor patio furniture and plants.','Patio seating and a glass doorway.','Covered patio sofa, chairs and coffee table.','Covered patio seating; outdoor setting lowers priority.'],
6:['Bed and bedside furnishing.','Bedroom desk/cabinet and chair, with doors and windows.','Bedroom windows and edge of desk/cabinet.','Bedroom wall, framed picture and closed door.'],
7:['Poolside patio and covered lounge furniture.','Patio seating beside house wall.','Covered sofas and coffee table.','Outdoor walkway/steps and plant pots; reference goal is the steps.'],
8:['Kitchen/bar counter and sink.','Counter edge, telephone and distant seating.','Pool-table room and sofa visible beyond bar.','Wooden shelving above counter; furniture is kitchen/bar oriented.'],
9:['Garage, car and distant golf equipment.','Construction sheeting and portable blower equipment, not school bags.','Bare garage wall.','Garage wall, wiring and door.'],
10:['Indoor sofa, ottoman and fireplace/TV.','Fireplace and window at reference endpoint.','Curtained window/corridor.','Nearby sofa and ottoman; practical indoor seating surface.'],
11:['Golf bags and clubs stored by garage wall.','Garage equipment and large storage/trash bags.','Garage/construction area and door.','Garage cabinet/work surface, barbecue equipment and window.'],
12:['Church altar and railing.','Church seating and altar area.','Church nave and rows of benches.','Church furnishings, not a household school-bag spot.'],
13:['Tiled shower/steam-room enclosure.','Bathroom wall and shower fittings.','Bath/spa pool or tub area.','Bathroom enclosure and pool/tub.'],
14:['Poolside railing and stone boundary.','Empty outdoor terrace with railing.','Lawn, pool and distant house.','Poolside planting and terrace; no suitable goal furniture.'],
15:['Bathroom doorway and vanity.','Bathroom sink and mirror.','Bathtub and arched windows.','Bathtub and bathroom cupboards.'],
16:['Living-room chair and coffee table beside fireplace.','Window niche.','Flower arrangement on a side table; surface is crowded.','Indoor seating and coffee table; use a specific chair/table in memory.'],
17:['Wooden door and wall controls.','Indoor hallway and arches.','Foyer/stair area and door.','Hallway console/side table beside door; strongest departure-time candidate.'],
18:['Wood-paneled wall at endpoint.','Window/corner with decorative vase.','Fireplace and ornamental table; chairs nearby.','Nearby indoor armchair and decorative side table; surface choice needs a memory.'],
19:['Loft table and chairs along railing.','Wooden chair beside window near goal.','Floor cushions and shrine/figurine at original endpoint.','Loft railing and open upper-level area.'],
20:['Loft table and chairs along railing.','Wooden chair beside window near goal.','Floor cushions and shrine/figurine at original endpoint.','Loft railing and open upper-level area; shares endpoint with path 1119.'],
21:['Garage cupboards with boxes above them.','Car in garage.','Garage columns and closed cupboards.','Garage wall and cupboards; no table, bed or seating at goal.'],
22:['Garage lockers/cupboards and boxes.','Garage column, car and doors.','Closed garage cupboards.','Garage wall; storage presence alone does not justify school-bag use.'],
23:['Bathroom doorway; distant bedroom visible beyond.','Frosted bathroom window.','Bathroom shower and cupboards.','Toilet and sink vanity; distant furniture is not the goal.'],
24:['Powder-room window and towel.','Bathroom sink; study visible through opening.','Interior door beside vanity.','Console partially visible outside the bathroom; reference goal remains a powder-room doorway.'],
25:['Garage wall and distant cupboards.','Garage car, columns and cupboards.','Garage side wall.','Closed garage door.'],
26:['Study glass doors.','Nearby padded reading/sofa chairs and footrests.','Study desk, chair and bookshelves.','Display shelves and globe; no need to infer a visible bag.'],
27:['Study glass doors.','Nearby padded reading/sofa chairs and footrests.','Study desk, chair and bookshelves.','Display shelves and globe; same endpoint as path 11065.'],
28:['Garage car and cupboard storage.','Garage column and doors.','Garage closed cupboards and side door.','Garage wall and column; no selected furniture type at endpoint.'],
}
keep={
4:('Living-room end table','An indoor end table is visible near the doorway. A memory must name this table, rather than any chair elsewhere in the room.',[270]),
6:('Bedroom bed or desk/chair','Bed and desk/chair provide plausible school-bag surfaces in a bedroom. The room is not independently established as Riya’s bedroom.',[0,90]),
10:('Indoor sofa / ottoman','A clearly visible indoor sofa/ottoman near the fireplace is a plausible school-bag resting place.',[0,270]),
16:('Living-room chair or side/coffee table','Nearby chair and tables fit the requested furniture types; the flower-filled side table is less convenient, so select the chair or a free table area.',[0,270]),
17:('Hallway table beside door','The console table beside the door is the most practical match to hurried school departure; its school-bag use still needs the authored memory.',[270]),
18:('Indoor armchair or side table','An armchair and side table are visible near the original window/corner goal. Specify one item in the school-bag memory.',[180,270]),
26:('Study desk / padded chair','The study contains a nearby desk and padded chairs: plausible surfaces for a school bag.',[90,180]),
27:('Study desk / padded chair','Same physical study endpoint as path 11065, reached by a different original >=40 m route.',[90,180]),
}
weaker={
1:('Office desk/chair','Fits desk/chair geometry, but this appears to be an office/cubicle rather than a child’s home study.',[0,90]),
5:('Covered patio sofa/chairs','Furniture fits the requested types, but outdoor patio storage is a weaker school-bag routine.',[180,270]),
7:('Covered patio sofa','A sofa is nearby, but the exact original endpoint is patio entrance steps rather than the seat.',[180]),
8:('Kitchen/bar counter and nearby chair','A surface and seating are present, but a kitchen/bar counter is a weaker match than an indoor study or hallway table.',[0,90]),
19:('Loft chair near window','A chair is near the endpoint, but the original endpoint is a floor-cushion/shrine area rather than the chair itself.',[90]),
20:('Loft chair near window','Same physical endpoint as path 1119; the chair is nearby but the original stop is the floor-cushion/shrine area.',[90]),
}
reject_reasons={2:'Exterior corridor/door without relevant goal furniture.',3:'Outdoor garden seating; weak fit for a usual household school-bag location, with incomplete mesh coverage.',9:'Garage/construction area; portable blowers are not school bags.',11:'Golf-equipment storage is unrelated to children’s school bags.',12:'Church altar/seating is not an appropriate household school-bag destination.',13:'Bathroom/spa endpoint.',14:'Outdoor terrace/railing without useful goal furniture.',15:'Bathroom bathtub/vanity endpoint.',21:'Garage car/cupboard endpoint; general storage is insufficient.',22:'Garage lockers/car endpoint; general storage is insufficient.',23:'Bathroom endpoint; bedroom furniture is only distant through a doorway.',24:'Powder-room endpoint; the hall/study furniture is beyond that endpoint.',25:'Garage doorway endpoint.',28:'Garage car/pillar endpoint.'}
rows=[];image_rows=[];pdf_pages={'keep':[],'weaker':[]}
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
F=ImageFont.truetype(font,23);T=ImageFont.truetype(font,29);S=ImageFont.truetype(font,17)
for r in index:
 i=r['review_index'];assert i in observations and len(observations[i])==4
 if i in keep:tier='keep';furniture,reason,heads=keep[i]
 elif i in weaker:tier='weaker';furniture,reason,heads=weaker[i]
 else:tier='reject';furniture='No suitable school-bag spot selected';reason=reject_reasons[i];heads=[]
 source_folder=SOURCE/Path(r['contact_sheet']).parent
 out=dict(r,decision=tier,furniture_focus=furniture,reason=reason,supporting_headings_degrees=heads,visible_schoolbag_required=False,schoolbag_routine='To be established by authored memory; not asserted as an original RxR fact.',views_reviewed=[])
 for heading,note in zip([0,90,180,270],observations[i]):
  view=next(v for v in r['views'] if f'heading_{heading:03d}' in v['file'])
  entry={'review_index':i,'split':r['split'],'scan':r['scan'],'path_id':r['path_id'],'heading_degrees':heading,'image':view['file'],'sha256':view['sha256'],'visible_evidence':note,'decision':tier}
  image_rows.append(entry);out['views_reviewed'].append(entry)
 if tier!='reject':
  destination=ROOT/('keep_8' if tier=='keep' else 'weaker_6')/source_folder.name;destination.mkdir(parents=True,exist_ok=True)
  for image in source_folder.glob('goal_heading_*.png'):
   dest=destination/image.name
   if not dest.exists():
    try:os.link(image,dest)
    except OSError:shutil.copy2(image,dest)
  sheet=Image.new('RGB',(1080,1360),'#f6f7fa');d=ImageDraw.Draw(sheet)
  title=f"{i:02d}  {r['scan']} / path {r['path_id']}"
  d.text((24,16),title,font=T,fill='#16243a')
  d.text((24,60),f"{r['split']} | {r['route_length_m']:.2f} m | {tier.upper()} candidate",font=F,fill='#246440' if tier=='keep' else '#8f571b')
  d.text((24,98),furniture,font=F,fill='#16243a')
  for line_no,line in enumerate(textwrap.wrap(reason,width=111)[:2]):d.text((24,132+line_no*23),line,font=S,fill='#34435a')
  d.text((24,181),'School bag need not be visible; memory establishes this furniture’s use.',font=S,fill='#34435a')
  for j,heading in enumerate([0,90,180,270]):
   x=24+(j%2)*520;y=225+(j//2)*548
   im=Image.open(source_folder/f'goal_heading_{heading:03d}.png').convert('RGB');sheet.paste(im,(x,y))
   d.text((x,y+516),f'Heading {heading} degrees'+(' — supports furniture choice' if heading in heads else ''),font=S,fill='#34435a')
  sheet.save(destination/'schoolbag_contact_sheet.jpg',quality=93)
  out['review_contact_sheet']=str((destination/'schoolbag_contact_sheet.jpg').relative_to(ROOT))
  (destination/'schoolbag_selection.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
  pdf_pages[tier].append(sheet)
 rows.append(out)
(ROOT/'all_28_schoolbag_decisions.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
with (ROOT/'all_28_schoolbag_decisions.csv').open('w',newline='') as f:
 keys=['review_index','split','scan','path_id','route_length_m','decision','furniture_focus','reason'];w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
 for r in rows:w.writerow({k:r[k] for k in keys})
with (ROOT/'all_112_image_reviews.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(image_rows[0]));w.writeheader();w.writerows(image_rows)
for tier,pages in pdf_pages.items():
 name='schoolbag_candidates_8.pdf' if tier=='keep' else 'schoolbag_weaker_candidates_6.pdf'
 pages[0].save(ROOT/name,save_all=True,append_images=pages[1:],resolution=120)
 thumbs=Image.new('RGB',(720,454*((len(pages)+1)//2)),'white')
 for j,page in enumerate(pages):thumbs.paste(page.resize((360,454),Image.Resampling.LANCZOS),((j%2)*360,(j//2)*454))
 thumbs.save(ROOT/f'{tier}_overview.jpg',quality=93)
notes='''# School-bag places: visual review of every goal view

User criterion: the school bag need not be visible. A plausible usual school-bag spot may be a table, sofa, sofa chair, bed or chair, with a memory establishing that Riya leaves her school bag there.

Reviewed all **112 views** at the 28 original RxR goals, using original-resolution four-view contact sheets and recording a separate observation for each heading. Furniture close to the goal was assessed; furniture passed earlier along the route does not qualify. Bathroom, garage/golf-equipment, church and bare outdoor-door goals were excluded. Merely seeing another kind of bag, general cupboards or storage does not qualify.

**Keep: 8 routes, 7 distinct physical endpoints.** These are plausible indoor furniture candidates, not original RxR school-bag task labels. Six weaker routes (5 distinct endpoints) are preserved separately. Fourteen routes were rejected. No school-bag visibility requirement was imposed, and no bags or objects were added to the images.

| Review image number | Split | Scene | RxR path | Length (m) | Furniture to use |
| --- | --- | --- | ---: | ---: | --- |
'''
for r in rows:
 if r['decision']=='keep':notes+=f"| {r['review_index']:02d} | {r['split']} | {r['scan']} | {r['path_id']} | {r['route_length_m']:.2f} | {r['furniture_focus']} |\n"
notes+='''
**Best school-departure match: image 17 / 2azQ1b91cZZ / path 5495**, the hallway table beside the door. For a study-chair setting, images 26 and 27 are different routes to the same study. For a bed setting, image 06 is the bedroom. For a sofa setting, image 10 is the indoor lounge sofa.

Each selection requires a specific authored memory naming the chosen item, e.g. “Riya said: I usually leave my school bag on this table beside the door.” This is the supplied scenario context, not a claim that the photographs independently establish a child's routine. Some original RxR stop landmarks are a doorway/window/fireplace; the furniture is nearby. If the chosen furniture requires moving the endpoint, recompute the route after that move instead of retaining the original length automatically.

Files:

- `schoolbag_candidates_8.pdf`: the eight kept route contact sheets.
- `keep_8/`: 32 original PNG views, annotated contact sheets and selection metadata.
- `schoolbag_weaker_candidates_6.pdf` and `weaker_6/`: office, patio, kitchen/bar and loft alternatives with reasons.
- `all_28_schoolbag_decisions.csv/.json`: keep/weaker/reject reason for every route.
- `all_112_image_reviews.csv`: separate observation for every goal image.

Earlier “28 routes” referred to all >=40 m validation paths, not 28 school-bag matches. This review supersedes broad generic-bag/storage-place interpretations. Original RxR files and the complete 28-route image collection are preserved.
'''
(ROOT/'README.md').write_text(notes)
with zipfile.ZipFile(ROOT/'schoolbag_candidates_8.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
 for file in sorted((ROOT/'keep_8').rglob('*')):
  if file.is_file():z.write(file,str(file.relative_to(ROOT)))
 for name in ['README.md','schoolbag_candidates_8.pdf','keep_overview.jpg','all_28_schoolbag_decisions.csv','all_112_image_reviews.csv']:z.write(ROOT/name,name)
print('Reviewed',len(image_rows),'images; kept',len(keep),'weaker',len(weaker),'rejected',len(reject_reasons))
