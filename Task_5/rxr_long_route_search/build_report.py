"""Write a reviewable shortlist without changing any dataset or dashboard state."""
from pathlib import Path
from collections import defaultdict
import csv,json,math,heapq,hashlib
P=Path(__file__).resolve().parent
rows=json.loads((P/'all_validation_routes_ge40m.json').read_text())
sem=json.loads((P/'semantic_endpoint_checks.json').read_text())
summary=json.loads((P/'search_summary.json').read_text())
groups=defaultdict(list)
for r in rows:groups[r['split'],r['scan'],r['path_id']].append(r)
with (P/'all_long_validation_trajectories.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['split','scan','path_id','route_length_m','direct_distance_m','start_viewpoint','goal_viewpoint','instruction_ids','english_instruction_ids','nearest_true_sofa_obb_distance_m','nearest_true_sofa_same_region']);w.writeheader()
 for key,rr in sorted(groups.items()):
  r=rr[0];s=next(x for x in sem if x.get('path_id')==r['path_id'] and x.get('scan')==r['scan']);sofas=s.get('goal_nearest_sofas',[]);sf=sofas[0] if sofas else {}
  out={k:r[k] for k in ['split','scan','path_id','route_length_m','direct_distance_m','start_viewpoint','goal_viewpoint']}
  out.update(instruction_ids=';'.join(str(x['instruction_id']) for x in rr),english_instruction_ids=';'.join(str(x['instruction_id']) for x in rr if x['language'].startswith('en')),nearest_true_sofa_obb_distance_m=sf.get('obb_distance_m'),nearest_true_sofa_same_region=sf.get('same_region'))
  w.writerow(out)
selected=[]
for pid,iid,use,status in [(5495,14610,'riya_schoolbag','Adaptation candidate: verified hallway table; no schoolbag or storage habit verified.'),(4224,123271,'sofa','Best original-instruction candidate: two English annotations stop at brown sofas; en-US annotation stops nearer a chair. True couch 2.018 m from goal.'),(1662,4025,'sofa','Sofa-adjacent backup: true couch 0.836 m from goal, but original instructions stop at fireplace/TV/window.')]:
 rr=next(rr for key,rr in groups.items() if key[2]==pid);r=next(x for x in rr if x['instruction_id']==iid);s=next(x for x in sem if x.get('path_id')==pid)
 gdata=json.loads((P/'sources'/(r['scan']+'_connectivity.json')).read_text());g={x['image_id']:x for x in gdata}
 coords={v:[x['pose'][3],x['pose'][7],x['pose'][11]] for v,x in g.items()}
 q=[(0.,r['start_viewpoint'])];best={r['start_viewpoint']:0.}
 while q:
  distance,u=heapq.heappop(q)
  if distance!=best[u]:continue
  if u==r['goal_viewpoint']:break
  for j,enabled in enumerate(g[u]['unobstructed']):
   v=gdata[j]['image_id']
   if not enabled or not gdata[j]['included']:continue
   d=distance+math.dist(coords[u],coords[v])
   if d<best.get(v,math.inf):best[v]=d;heapq.heappush(q,(d,v))
 out=dict(r,selection_use=use,assessment=status,all_english_annotations=[x for x in rr if x['language'].startswith('en')],reference_positions_mp3d=[coords[v] for v in r['path']],shortest_graph_start_goal_m=best[r['goal_viewpoint']],endpoint_semantic_evidence=s)
 if pid==5495:
  out.update(existing_rxr_ce_episode_id='4240',existing_rxr_ce_episode_key='2azQ1b91cZZ_4240',existing_rxr_ce_reference_length_m=41.49157332974706,proposed_task="Quick! Riya's bus is here! But she still needs her school bag.",proposed_memory="Riya said: I usually leave my school bag on this little table beside the door.",memory_status='New user-authored scenario assumption, not an original RxR fact or a visually observed bag.')
 selected.append(out)
(P/'shortlisted_routes.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2))
bag_rows=json.loads((P/'all_validation_bag_mentions.json').read_text())
bag=next(r for r in bag_rows if r['instruction_id']==21792)
g={x['image_id']:[x['pose'][3],x['pose'][7],x['pose'][11]] for x in json.loads((P/'sources/QUCTc6BB5sX_connectivity.json').read_text())}
bag['route_length_m']=sum(math.dist(g[a],g[b]) for a,b in zip(bag['path'],bag['path'][1:]));bag['assessment']='Explicit bag destination; fails >=40 m. Bag is not identified as a schoolbag and routine not documented.'
(P/'explicit_bag_route_below_threshold.json').write_text(json.dumps(bag,ensure_ascii=False,indent=2))
# Export scientific route diagrams as a standalone artifact.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axs=plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
for ax,r in zip(axs,selected):
 pts=r['reference_positions_mp3d'];xs=[v[0] for v in pts];ys=[v[1] for v in pts]
 ax.plot(xs,ys,'-',color='#496eaa',linewidth=1.4);sc=ax.scatter(xs,ys,c=[v[2] for v in pts],cmap='viridis',s=23)
 ax.scatter(xs[0],ys[0],marker='o',s=85,facecolors='none',edgecolors='green',label='Start');ax.scatter(xs[-1],ys[-1],marker='*',s=150,color='#c23a36',label='Goal')
 ax.set_title(f"{r['scan']} / path {r['path_id']}\n{r['split']}: {r['route_length_m']:.2f} m")
 ax.set_xlabel('Matterport X (m)');ax.set_ylabel('Matterport Y (m)');ax.axis('equal');ax.grid(alpha=.25);ax.legend()
fig.suptitle('Original RxR guide routes; XY projection of full 3D reference paths')
fig.savefig(P/'shortlisted_route_maps.png',dpi=160);fig.savefig(P/'shortlisted_route_maps.pdf');plt.close(fig)
report=f'''# RxR routes at least 40 m: school-bag and sofa search

Searched both complete public validation guide splits from the [official RxR release](https://github.com/google-research-datasets/RxR), using the authors' [Matterport navigation graphs](https://github.com/peteanderson80/Matterport3DSimulator/tree/{summary['connectivity_revision']}/connectivity). No full scene/model download or model inference was needed. Existing server semantic files and cached goal views were reused.

| Split | Guide instruction records searched | Distinct paths searched | Paths >=40 m | Instruction variants on those paths |
| --- | ---: | ---: | ---: | ---: |
| val_seen | 8,813 | 1,244 | 14 | 78 |
| val_unseen | 13,652 | 1,517 | 14 | 126 |

All 204 long-route annotations and 28 distinct paths are saved. English annotations cover 25 paths; three seen paths have only Hindi/Telugu instructions. Their endpoints were also checked with scene semantics. All reference edges passed included/unobstructed graph checks.

## Shortlist

| Use | Split / scene | Original RxR path / instruction ID | Reference route (m) | Direct (m) | Endpoint evidence and limit |
| --- | --- | --- | ---: | ---: | --- |
| Riya school-bag adaptation | val_unseen / 2azQ1b91cZZ | 5495 / 14610 | 41.476140 | 9.148139 | Same-region side table object 351, 0.447 m from the goal panorama to its oriented box. Cached views show the door and side table; no visible bag. The routine must be an authored memory. |
| Sofa candidate | val_seen / VFuaQ6m2Qom | 4224 / 123271 | 49.367640 | 16.136824 | English variants 123270/123271 name brown sofas at arrival. Semantic couch 316 is in the same region, 2.018 m from the goal panorama to its box. Variant 86347 names a chair, and a chair is closer. Requires visual review for strict sofa-only labeling. |
| Sofa-adjacent backup | val_seen / VzqfbhrpDEA | 1662 / 4025 | 40.200356 | 24.908583 | Semantic couch 1618 is in the same region, 0.836 m from the goal panorama to its box. Original stop cues are fireplace/TV/window, not the sofa itself. |

The first route is already in your collector catalog as **RxR-CE episode `2azQ1b91cZZ_4240`**, with its stored continuous-environment reference-waypoint length **41.491573 m**. Original RxR instruction ID **14610** and RxR-CE episode ID **4240** are different identifiers. The small length difference comes from their respective saved coordinates. Sofa IDs above are original RxR IDs; a corresponding RxR-CE episode ID has not been verified.

### School-bag conclusion

No >=40 m English validation instruction explicitly identifies a school-bag destination or documents where children routinely keep bags. A generic bag is explicitly mentioned at the endpoint of unseen **QUCTc6BB5sX / path 7767 / instruction 21792**, but that route is only **{bag['route_length_m']:.6f} m**. It fails the length requirement and does not establish that the bag belongs to a child.

The unseen 41.48 m hallway-table route is a usable **authored adaptation**, not a confirmed original school-bag task. Suggested task: “Quick! Riya's bus is here! But she still needs her school bag.” Suggested memory: “Riya said: I usually leave my school bag on this little table beside the door.” Treat that memory as a new scenario assumption. No bag pickup or bag visibility is established by these cached views.

Your previous **EU6Fwq7SyZv_10664** school-things scenario has a stored RxR-CE sparse reference length **39.206777 m**, so it does not meet >=40 m under that metric. Its original endpoint is near a bed, chair and ottoman; it is not an original bag-location annotation.

### Sofa conclusion

The strongest instruction-supported >=40 m sofa candidate is **seen-validation path 4224**. It is not unanimously labeled: English variants disagree between a sofa and a chair. Path 1662 is a physically sofa-adjacent backup with a different original stop landmark. The third same-region sofa-near endpoint, seen path 7512 (**43.430021 m**, couch box **2.511 m** away), explicitly stops at steps and was not selected as a strict sofa goal.

No confirmed sofa endpoint was found among the **14 original unseen guide paths >=40 m**. A sofa mentioned along the route does not make it the goal. Labels such as `sofa#chair` with normalized category `chair` were excluded from true-sofa checks. Geometry alone does not establish line of sight, accessibility to the furniture, or object interaction.

## Files and metric

- [Shortlisted routes with full original instructions, reference positions, viewpoints, and evidence](shortlisted_routes.json)
- [All 28 long trajectories](all_long_validation_trajectories.csv)
- [All 204 original instruction records on long routes](all_validation_routes_ge40m.json)
- [Endpoint semantic checks](semantic_endpoint_checks.json)
- [Entry-table cached goal views](goal_evidence/bag_table_goal_contact_sheet.jpg)
- [Route diagrams](shortlisted_route_maps.png)
- [Official source URLs, revision and SHA-256 hashes](search_summary.json)

Route length is the **sum of 3D distances between consecutive original guide viewpoints**. It is not model rollout length, direct distance, shortest-path length, or RxR-CE dense action-trace length. None of the paths were lengthened or joined to meet 40 m. MP3D positions are **Z-up**; do not paste them into Habitat's Y-up agent pose without conversion and the source episode's height convention. Exact original viewpoint sequences and heading are retained in JSON. Semantic distances use the `.house` panorama center and object oriented box; they are geometric proximity checks, not traversable/geodesic distances. All instructions retain their original split; sofa results are explicitly **val_seen**, not unseen.

The live collector and its unfinished sample were not changed.
'''
(P/'RESULTS.md').write_text(report)
print('Wrote report, shortlist, full long-route CSV, and route diagrams')
for r in selected:print(r['selection_use'],r['path_id'],r['route_length_m'],'shortest graph',r['shortest_graph_start_goal_m'])
