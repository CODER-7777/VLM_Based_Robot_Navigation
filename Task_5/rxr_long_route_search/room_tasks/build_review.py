"""Build reviewable individual/combined results without promoting adaptations to RxR truth."""
from pathlib import Path
import collections
import csv
import html
import json
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent
audits=json.loads((ROOT/'all_28_room_audits.json').read_text())
compatible=json.loads((ROOT/'nora_compatible_original_routes_room_options.json').read_text())
extensions=json.loads((ROOT/'bathroom_source_delivery_extensions.json').read_text())
scenario=json.loads((ROOT/'environment_06/scenario.json').read_text())
summary=json.loads((ROOT/'summary.json').read_text())
manifest=json.loads((ROOT/'views/render_manifest.json').read_text())
by_id=collections.defaultdict(list)
for r in compatible:by_id[(r['split'],r['scan'],r['path_id'])].append(r)
extension_ids=sorted({(r['source_split'],r['scan'],r['source_path_id']) for r in extensions})
rows=[]
for key,options in sorted(by_id.items()):
    source=next(r for r in audits if (r['split'],r['scan'],r['path_id'])==key)
    near=[o for o in options if o['route_steps_adjacent_to_room']]
    rows.append(dict(split=key[0],scan=key[1],path_id=key[2],route_length_m=source['route_length_m'],
        compatible_nora_regions=';'.join(str(o['nora_region']) for o in options),
        near_entrance_regions=';'.join(str(o['nora_region']) for o in near),
        visual_review='bedrooms rendered and reviewed' if near else 'annotation screen only',
        strength='entrance-adjacent candidate' if near else 'weak compatible route',
        original_path_unchanged=True,shortcut_conflict_demonstrated=False))
with (ROOT/'nora_all_25_compatible_routes.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
extension_rows=[]
for key in extension_ids:
    options=[r for r in extensions if (r['source_split'],r['scan'],r['source_path_id'])==key and r['nora_region'] is None]
    best=min(options,key=lambda x:x['adapted_length_m'])
    extension_rows.append(dict(split=key[0],scan=key[1],path_id=key[2],original_m=best['source_length_m'],
        extended_m=best['adapted_length_m'],riya_region=best['riya_region'],bed_object_id=best['bed_object_id'],
        status='authored new bed goal; image/continuous path validation pending'))
with (ROOT/'toiletries_7_bathroom_route_extensions.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(extension_rows[0]));writer.writeheader();writer.writerows(extension_rows)
summary.update(individual_nora_stronger_routes=2,individual_nora_broad_compatible_routes=25,
    individual_toiletries_original_bed_goal_source_routes=1,
    original_bed_goal_requires_pickup_detour=True,
    secondary_bathroom_source_routes_requiring_new_bed_goal=len(extension_ids),
    authored_same_bed_goal_variant_count=len(json.loads((ROOT/'all_authored_pickup_adaptations.json').read_text())),
    authored_combined_original_bed_goal_source_routes=1,
    chosen_source=dict(split='val_seen',scan='VFuaQ6m2Qom',path_id=5721),
    chosen_source_length_m=scenario['source_length_m'],chosen_authored_length_m=scenario['adapted_length_m'],
    selected_nora_region=26,selected_riya_region=21,
    shortcut_avoidance_demonstrated=False)
navfile=ROOT/'environment_06/toiletries_placed/route_navmesh_check.json'
if navfile.exists():
    nav=json.loads(navfile.read_text());summary['chosen_navmesh_pairs_connected']=nav['all_adjacent_pairs_connected']
    summary['chosen_navmesh_geodesic_edge_sum_m']=nav['geodesic_edge_sum_m']
(ROOT/'summary.json').write_text(json.dumps(summary,indent=2))
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font=ImageFont.truetype(fontpath,25)
pages=[]
for r in manifest:
    canvas=Image.new('RGB',(1060,1190),'#f5f6fa');d=ImageDraw.Draw(canvas)
    d.text((16,10),r['role'],font=font,fill='#172335')
    d.text((16,46),f"{r['scan']} / region {r['region']}",font=font,fill='#172335')
    d.text((16,82),'Room identities are proposed scenario labels.',font=font,fill='#854400')
    for i,v in enumerate(r['views']):
        x=12+(i%2)*524;y=128+(i//2)*530
        canvas.paste(Image.open(ROOT/'views'/v['path']),(x,y))
        d.text((x,y+513),f"Heading {v['heading_degrees_mp3d']} degrees",fill='#172335')
    canvas.save(ROOT/'views'/f"review_{r['review_index']:02d}.jpg",quality=92);pages.append(canvas)
pages[0].save(ROOT/'room_evidence.pdf',save_all=True,append_images=pages[1:],resolution=120)
extension_table='\n'.join(f"| {r['split']} | {r['scan']} | {r['path_id']} | {r['original_m']:.2f} | {r['extended_m']:.2f} | {r['riya_region']} |" for r in extension_rows)
navtext='Continuous navigation has not been validated.'
if navfile.exists():
    navtext=f"Navmesh adjacent pairs connected: {nav['all_adjacent_pairs_connected']}. Floor-snapped edge geodesic sum: {nav['geodesic_edge_sum_m']}. This is a separate metric, not an executed route or continuous forbidden-room verification."
report=f'''# RxR bedroom avoidance and toiletries delivery

Scope: both complete RxR validation guide splits; original guide length >=40 m. All 22,465 instruction records / 2,761 distinct paths were rechecked. Exactly 28 distinct original paths (204 instruction variants) pass the length filter. Length is the 3D connectivity-edge sum, not shortest distance or a robot rollout.

## Individual task 1: avoid Nora's sleeping room

The statement is a **constraint**, without a destination. For standalone screening we retain each RxR route's existing destination and propose a separate bedroom as Nora's room. Nora's identity and sleeping state are authored memories.

**25 compatible source routes**, of which **2 are stronger entrance-adjacent candidates**. The other 23 only have an avoidable bedroom elsewhere in the connected scene. They are weak compatibility matches, not validated avoidance challenges.

| Split | Scene | Path | Original m | Candidate Nora region | Evidence |
|---|---|---:|---:|---|---|
| val_seen | E9uDoFAP3SH | 15740 | 46.67 | 0 | Original start has a graph connection into this bedroom; route stays out. Bed visually checked. |
| val_seen | EDJbREhghzL | 11513 | 40.46 | 6 or 12 | Route passes graph connections into these bedrooms; stays out. Both beds visually checked. |

All compatible IDs and proposed rooms: [CSV](nora_all_25_compatible_routes.csv), [per-room JSON](nora_compatible_original_routes_room_options.json). Three excluded source routes: B6ByNegPMKs/13062, dhjEzFoUFzH/4176, ur6pFq6Qu1A/15896 (no assignable bedroom in the route's connected graph component).

**No nontrivial bedroom-shortcut avoidance case was demonstrated** among these 28 routes: removing a traversed bedroom either blocks the required connection, or the candidate forbidden room is not on the reference/shortest route. Do not claim the constraint forces a reroute. Node exclusion also does not prove an edge or continuous trajectory never clips a room.

## Individual task 2: bring toiletries to Riya's bed

**1 original bed-goal source route**: val_seen / VFuaQ6m2Qom / path **5721**, **{scenario['source_length_m']:.6f} m**, bedroom region **21**, bed object **447**. The original goal panorama is about **0.420 m** from the annotated bed box; all four original goal views were reviewed and show the bed. The variants disagree on the original stop cue (bed/door/portrait/living area); the new task uses the physical bed, not an alleged original toiletries instruction.

**0 unmodified original routes already satisfy bathroom pickup followed by a bed goal.** Path 5721 needs a pickup detour. A storage routine is an authored assumption; the original scene does not establish Riya's ownership or visible toiletries at that location.

## Combined task and concrete candidate

> {scenario['task_combined']}

Proposed memory: Riya's toiletries are beside the downstairs bathroom sink (region 20), her bed is in region 21, and Nora's bedroom is region 26.

The adapted path preserves every original guide step in order, inserts a bathroom pickup, and ends at the original bed-adjacent goal. **{scenario['adapted_length_m']:.6f} m** (extra **{scenario['added_length_m']:.6f} m**). This is **one authored source-route adaptation**, not another original RxR route. It stays outside region 26 at all graph nodes. Nora's room is a negative constraint here; no shortcut conflict is demonstrated.

[Scenario, exact path and memories](environment_06/scenario.json); [all pickup/forbidden-room variants](all_authored_pickup_adaptations.json). These 38 variants share one original source route and must not be counted as 38 distinct RxR trajectories.

{navtext}

## Additional bathroom-route adaptations

Seven other original long routes visit a bathroom but end elsewhere. Appending a bed delivery leg changes their goal. These are secondary authored candidates, not original bed-goal matches. Some pass the delivery room early and then travel elsewhere; preserving their whole guide path is inefficient and must not be described as a shortest fetch route.

| Split | Scene | Source path | Original m | Shortest added-leg version total m | New bed region |
|---|---|---:|---:|---:|---:|
{extension_table}

[All bed/forbidden-room extension options](bathroom_source_delivery_extensions.json), [one best unconstrained extension per source](toiletries_7_bathroom_route_extensions.csv). Images and continuous movement for these new goals still need validation before use.

## Images, placement and reproducibility

[Room images (PDF)](room_evidence.pdf); [image review](review.html). All room images are static renders of original MP3D geometry, not AI-generated reconstructions. Missing geometry and black mirror regions are source scan artifacts.

The toiletries placement uses two photographic Google Scanned Objects models, a conditioner tube (19.21 cm) and boxed eye cream (4.90 cm), with original physical scale and CC BY 4.0 attribution. The cream is a retail carton, not an unpackaged jar. [Credits](environment_06/asset_credits.json), [measured support normals/heights and transforms](environment_06/placements.json), [placed front view](environment_06/toiletries_placed/sink_front.png), [side view](environment_06/toiletries_placed/sink_side.png). These are newly added task props, not original observed toiletries. Static placement is distinct from grasping, carrying and delivery execution.

Every original route and rejection remains in [28-route audit CSV](all_28_room_audits.csv) and [JSON](all_28_room_audits.json). Sources: cached official RxR guides/connectivity; existing server MP3D .house/GLB assets. The official [.house format and room labels](https://github.com/niessner/Matterport/blob/master/data_organization.md) define the room evidence. No policy, collector or training run was changed.

Rebuild: `python3 -B search_room_tasks.py`, `python3 -B prepare_adaptations.py`, prepare/render the scene assets, then `python3 -B build_review.py`. The simulator renderer requires the existing server Habitat environment. Geometry fit does not certify physical stability or manipulation.
'''
(ROOT/'RESULTS.md').write_text(report)
sections=[]
for r in manifest:
    sections.append(f'<article><h2>{html.escape(r["role"])}</h2><p>{r["scan"]} · region {r["region"]} · proposed identities</p><a href="views/review_{r["review_index"]:02d}.jpg"><img src="views/review_{r["review_index"]:02d}.jpg"></a></article>')
placed=ROOT/'environment_06/toiletries_placed/sink_front.png'
if placed.exists():
    sections.insert(0,'<article><h2>Added toiletries beside the sink</h2><p>New 3D props; original scene unchanged on disk.</p><img src="environment_06/toiletries_placed/sink_front.png"><img src="environment_06/toiletries_placed/sink_side.png"></article>')
table=''
goal_index=list(csv.DictReader((ROOT.parent/'goal_images_28/goal_image_index.csv').open()))
for r in rows:
    goal=next(x for x in goal_index if x['scan']==r['scan'] and int(x['path_id'])==r['path_id'])
    cells=''.join(f'<td>{html.escape(str(r[k]))}</td>' for k in ('split','scan','path_id','route_length_m','near_entrance_regions','strength'))
    table+='<tr>'+cells+f'<td><a href="../goal_images_28/{goal["contact_sheet"]}">Original goal views</a></td></tr>'
document='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RxR room tasks review</title><style>body{margin:32px auto;max-width:1240px;padding:0 20px;background:#f4f6fa;color:#182535;font:17px/1.5 system-ui}h1{line-height:1.15}article,.intro{background:white;padding:22px;border-radius:14px;margin:24px 0}img{max-width:100%;height:auto}a{color:#1658b1}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border-bottom:1px solid #ccd3df;text-align:left}.scroll{overflow-x:auto}</style><h1>RxR: bedroom avoidance and toiletries delivery</h1>'''
document+=f'<div class="intro"><b>28 original validation routes ≥40 m reviewed.</b><p>Bedroom avoidance: 25 compatible routes, 2 stronger entrance-adjacent cases. Toiletries: 1 original bed-goal source, requiring a pickup detour. Combined authored candidate: {scenario["adapted_length_m"]:.2f} m. No demonstrated bedroom shortcut conflict.</p><p><a href="RESULTS.md">Full findings</a> · <a href="room_evidence.pdf">Room image PDF</a> · <a href="nora_all_25_compatible_routes.csv">All 25 compatible IDs</a> · <a href="all_28_room_audits.csv">All 28 audited routes</a></p></div>'
document+=''.join(sections)+'<h2>All compatible source routes</h2><div class="scroll"><table><tr><th>Split</th><th>Scene</th><th>Path</th><th>Original m</th><th>Near entrance rooms</th><th>Evidence</th><th>Images</th></tr>'+table+'</table></div></html>'
(ROOT/'review_gallery.html').write_text(document.replace('<h1>RxR: bedroom avoidance and toiletries delivery</h1>', '<p><a href="review.html">← Open the interactive trajectory dashboard</a></p><h1>RxR: bedroom avoidance and toiletries delivery</h1>'))
print('WROTE review, findings, PDF, candidate CSVs')
