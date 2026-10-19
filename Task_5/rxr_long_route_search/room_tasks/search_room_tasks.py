"""Screen every original RxR validation guide route >=40m against MP3D rooms.

Region membership is annotation evidence, not continuous collision validation.
Names, sleeping and ownership are authored scenario assignments, never RxR truth.
"""
from pathlib import Path
import collections
import csv
import hashlib
import heapq
import json
import math
import gzip
import numpy as np

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
LABELS = {'a': 'bathroom', 'b': 'bedroom', 'c': 'closet', 'd': 'dining room',
          'e': 'entryway', 'f': 'family room', 'g': 'garage', 'h': 'hallway',
          'i': 'library', 'j': 'laundry', 'k': 'kitchen', 'l': 'living room',
          'm': 'meeting room', 'n': 'lounge', 'o': 'office', 'p': 'porch',
          'r': 'recreation room', 's': 'stairs', 't': 'toilet', 'u': 'utility',
          'v': 'TV room', 'w': 'gym', 'x': 'outdoor', 'y': 'balcony',
          'z': 'other', 'B': 'bar', 'C': 'classroom', 'D': 'dining booth',
          'S': 'spa', 'Z': 'junk', '-': 'unlabeled'}


def parse_house(scan):
    path = ROOT/'sources'/f'{scan}.house'
    regions, panoramas, categories, objects = {}, {}, {}, []
    with path.open() as f:
        for line in f:
            t = line.split()
            if not t:
                continue
            if t[0] == 'R':
                regions[int(t[1])] = dict(label=t[5], name=LABELS.get(t[5], t[5]),
                    level=int(t[2]), position=list(map(float, t[6:9])), bounds=list(map(float, t[9:15])))
            elif t[0] == 'P' and len(t[1]) == 32:
                panoramas[t[1]] = dict(region=int(t[3]), position=list(map(float, t[5:8])))
            elif t[0] == 'C':
                categories[int(t[1])] = dict(raw=t[3], category=t[5])
            elif t[0] == 'O':
                objects.append(dict(id=int(t[1]), region=int(t[2]), category_id=int(t[3]),
                    center=list(map(float,t[4:7])), axes=list(map(float,t[7:13])), radii=list(map(float,t[13:16]))))
    for o in objects:
        o.update(categories.get(o['category_id'], dict(raw='unlabeled',category='unlabeled')))
    out = dict(scan=scan, regions=regions, panoramas=panoramas, objects=objects,
               source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (ROOT/'sources'/f'{scan}_rooms.json').write_text(json.dumps(out,indent=2))
    return out


def obb_distance(point, obj):
    a0, a1 = np.array(obj['axes']).reshape(2,3)
    a2 = np.cross(a0, a1)
    local = np.array([a0,a1,a2]) @ (np.array(point)-obj['center'])
    return float(np.linalg.norm(np.maximum(np.abs(local)-obj['radii'], 0)))


def shortest(graph, start, goal, blocked=frozenset()):
    if start in blocked or goal in blocked:
        return None
    dist, previous, queue = {start:0.}, {}, [(0.,start)]
    while queue:
        d, u = heapq.heappop(queue)
        if d != dist[u]:
            continue
        if u == goal:
            path = [u]
            while u != start:
                u = previous[u]; path.append(u)
            return dict(path=path[::-1], length_m=d)
        for v,w in graph[u]:
            if v in blocked:
                continue
            nd = d+w
            if nd < dist.get(v, math.inf):
                dist[v],previous[v] = nd,u
                heapq.heappush(queue,(nd,v))
    return None


def main():
    annotations = json.loads((BASE/'all_validation_routes_ge40m.json').read_text())
    # Independently verify the cached long-route selection against both full splits.
    source_counts={};selected={};coordinates={}
    for split in ('val_seen','val_unseen'):
        records=[json.loads(line) for line in gzip.decompress((BASE/'sources'/f'rxr_{split}_guide.jsonl.gz').read_bytes()).splitlines()]
        source_counts[split]=dict(instruction_records=len(records),distinct_paths=len({r['path_id'] for r in records}))
        for r in records:
            scan=r['scan']
            if scan not in coordinates:
                graph=json.loads((BASE/'sources'/f'{scan}_connectivity.json').read_text())
                coordinates[scan]={v['image_id']:[v['pose'][3],v['pose'][7],v['pose'][11]] for v in graph}
            positions=coordinates[scan]
            length=sum(math.dist(positions[u],positions[v]) for u,v in zip(r['path'],r['path'][1:]))
            if length>=40:selected[(split,scan,r['path_id'],r['instruction_id'])]=length
    assert len(selected)==len(annotations)
    for r in annotations:
        assert abs(selected[(r['split'],r['scan'],r['path_id'],r['instruction_id'])]-r['route_length_m'])<1e-8
    unique = {}
    for r in annotations:
        unique.setdefault((r['split'],r['scan'],r['path_id']),[]).append(r)
    houses = {s:parse_house(s) for s in sorted({k[1] for k in unique})}
    graphs = {}
    for scan in houses:
        raw = json.loads((BASE/'sources'/f'{scan}_connectivity.json').read_text())
        graph = {r['image_id']:[] for r in raw if r['included']}
        for r in raw:
            if not r['included']:continue
            for flag,v in zip(r['unobstructed'],raw):
                if flag and v['included']:
                    a=[r['pose'][3],r['pose'][7],r['pose'][11]]
                    b=[v['pose'][3],v['pose'][7],v['pose'][11]]
                    graph[r['image_id']].append((v['image_id'],math.dist(a,b)))
        graphs[scan]=graph
    audits, avoidance, delivery, combined, adaptations, compatible = [], [], [], [], [], []
    for index, (key, variants) in enumerate(sorted(unique.items()), 1):
        split,scan,path_id=key; r=variants[0]; h=houses[scan]; g=graphs[scan]
        pans=h['panoramas']; rooms=h['regions']; obs=h['objects']; path=r['path']
        seq=[pans[v]['region'] for v in path]
        room_seq=[v for i,v in enumerate(seq) if i==0 or seq[i-1]!=v]
        bedroom_ids=[i for i,v in rooms.items() if v['label']=='b']
        goal_objects=sorted([dict(o,obb_distance_m=obb_distance(pans[path[-1]]['position'],o))
                    for o in obs if o['category']=='bed'],key=lambda x:x['obb_distance_m'])
        same_beds=[o for o in goal_objects if o['region']==seq[-1]]
        # Pickup/storage has a stricter semantic requirement than just a generic table.
        pickups=[]
        for j,v in enumerate(path[:-1]):
            region=pans[v]['region']
            if rooms[region]['label'] not in ('a','t'):continue
            storage=[dict(o,obb_distance_m=obb_distance(pans[v]['position'],o)) for o in obs
                     if o['region']==region and (o['category'] in ('sink','counter','cabinet','shelving') or 'vanity' in o['raw'])]
            storage.sort(key=lambda x:x['obb_distance_m'])
            if storage:pickups.append(dict(route_index=j,viewpoint=v,region=region,storage_objects=storage))
        base=dict(review_index=index,split=split,scan=scan,path_id=path_id,
                  route_length_m=r['route_length_m'],path=path,start_viewpoint=path[0],goal_viewpoint=path[-1],
                  start_position_mp3d=r['start_position_mp3d'],goal_position_mp3d=r['goal_position_mp3d'],
                  instruction_ids=[v['instruction_id'] for v in variants],
                  english_instructions=[dict(instruction_id=v['instruction_id'],instruction=v['instruction']) for v in variants if v['language'].startswith('en')],
                  room_sequence=[dict(region=i,**rooms[i]) for i in room_seq],
                  room_at_each_viewpoint=seq,goal_same_region_beds=same_beds,
                  nearest_bed=goal_objects[0] if goal_objects else None, toiletries_pickups_on_original_route=pickups,
                  bedroom_avoidance_options=[],endpoint_delivery_eligible=bool(same_beds),
                  status='annotation_screen_only; identities/routine authored; visual and continuous-path checks required')
        for bedroom in bedroom_ids:
            blocked={v for v in g if pans[v]['region']==bedroom}
            if path[0] in blocked or path[-1] in blocked:continue
            alternative=shortest(g,path[0],path[-1],blocked)
            if alternative is None:continue
            crosses=bedroom in seq[1:-1]
            unrestricted=shortest(g,path[0],path[-1])
            shortcut=any(v in blocked for v in unrestricted['path'])
            # An unrelated bedroom elsewhere in the house is a weak, vacuous match.
            kind='reference_route_crosses_bedroom' if crosses else ('shortest_route_crosses_bedroom' if shortcut else 'unrelated_bedroom_only')
            option=dict(nora_region=bedroom,evidence=kind,original_route_enters_forbidden_room=crosses,
                        forbidden_viewpoints=sorted(blocked),alternative=alternative,
                        unrestricted_shortest=unrestricted,alternative_is_original_rxr_route=False,
                        alternative_ge40m=alternative['length_m']>=40)
            base['bedroom_avoidance_options'].append(option)
            if bedroom not in seq:
                adjacent_steps=[]
                for j,u in enumerate(path):
                    if any(v in blocked for v,w in g[u]):adjacent_steps.append(j)
                compatible.append(dict(split=split,scan=scan,path_id=path_id,route_length_m=r['route_length_m'],
                    nora_region=bedroom,original_path_avoids_room=True,
                    route_steps_adjacent_to_room=adjacent_steps,bed_objects=[o['id'] for o in obs if o['region']==bedroom and o['category']=='bed'],
                    evidence_strength='passes_room_entrance_graph_neighbor' if adjacent_steps else 'room_elsewhere_in_same_connected_scene',
                    warning='Compatible negative constraint only; no demonstrated shortcut through this bedroom.'))
            if kind!='unrelated_bedroom_only':
                avoidance.append(dict(split=split,scan=scan,path_id=path_id,route_length_m=r['route_length_m'],**option))
            if same_beds and pickups and kind!='unrelated_bedroom_only':
                # Preserve at least one pickup in the constrained start->pickup->bed plan.
                for pickup in pickups:
                    a=shortest(g,path[0],pickup['viewpoint'],blocked); b=shortest(g,pickup['viewpoint'],path[-1],blocked)
                    if a and b:
                        combined.append(dict(split=split,scan=scan,path_id=path_id,nora_region=bedroom,pickup=pickup,
                            constrained_path=a['path']+b['path'][1:],constrained_length_m=a['length_m']+b['length_m']))
                        break
        if same_beds and pickups:
            delivery.append(dict(split=split,scan=scan,path_id=path_id,route_length_m=r['route_length_m'],beds=same_beds,pickups=pickups))
        # Explicitly separate useful scenes/segments from qualifying ORIGINAL goals.
        bed_visits=[dict(route_index=j,viewpoint=v,region=seq[j],beds=[o['id'] for o in obs if o['category']=='bed' and o['region']==seq[j]])
                    for j,v in enumerate(path) if any(o['category']=='bed' and o['region']==seq[j] for o in obs)]
        if bed_visits or rooms[seq[-1]]['label'] in ('a','t'):
            adaptations.append(dict(split=split,scan=scan,path_id=path_id,route_length_m=r['route_length_m'],
                                    bed_visits=bed_visits,goal_region=seq[-1],goal_room=rooms[seq[-1]]['name'],
                                    original_goal_is_bed=bool(same_beds),pickups=pickups,
                                    warning='Changing/reversing/extending the route is an authored adaptation; recompute length.'))
        audits.append(base)
    def write(name,data): (ROOT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False))
    write('all_28_room_audits.json',audits)
    write('nora_avoidance_options.json',avoidance)
    write('nora_compatible_original_routes_room_options.json',compatible)
    write('toiletries_delivery_original_matches.json',delivery)
    write('combined_original_matches.json',combined)
    write('adaptation_candidates.json',adaptations)
    summary=dict(scope='RxR val_seen + val_unseen, original forward guide length >=40m',
        unique_original_routes=len(audits),instruction_variants=len(annotations),
        goal_bedroom_routes=sum(x['endpoint_delivery_eligible'] for x in audits),
        original_toiletries_to_bed_matches=len(delivery),combined_original_matches=len(combined),
        meaningful_avoidance_source_routes=len({(x['split'],x['scan'],x['path_id']) for x in avoidance}),
        meaningful_avoidance_room_options=len(avoidance),
        nora_compatible_original_routes=len({(x['split'],x['scan'],x['path_id']) for x in compatible}),
        nora_compatible_room_assignments=len(compatible),
        nora_passes_room_entrance_routes=len({(x['split'],x['scan'],x['path_id']) for x in compatible if x['route_steps_adjacent_to_room']}),
        constrained_avoidance_routes_ge40m=sum(x['alternative_ge40m'] for x in avoidance),
        strong_shortcut_avoidance_matches_found=False,source_counts=source_counts,
        identities_are_authored=True,room_mapping='official .house panorama region membership',
        limitations=['Graph paths do not guarantee continuous collision-free navigation.',
                    'Edges are checked by node regions only; a straight edge can clip another region.',
                    'Storage fixtures and bed category do not establish toiletries visibility, ownership or reachable support surfaces.'])
    write('summary.json',summary)
    with (ROOT/'all_28_room_audits.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['split','scan','path_id','route_length_m','room_sequence','goal_beds','bathroom_pickups','meaningful_avoidance_options']);w.writeheader()
        for a in audits:w.writerow(dict(split=a['split'],scan=a['scan'],path_id=a['path_id'],route_length_m=a['route_length_m'],room_sequence=' > '.join(str(r['region'])+':'+r['name'] for r in a['room_sequence']),goal_beds=','.join(str(o['id']) for o in a['goal_same_region_beds']),bathroom_pickups=len(a['toiletries_pickups_on_original_route']),meaningful_avoidance_options=sum(o['evidence']!='unrelated_bedroom_only' for o in a['bedroom_avoidance_options'])))
    print(json.dumps(summary,indent=2))
    for a in audits:
        print(a['split'],a['scan'],a['path_id'],round(a['route_length_m'],2),' > '.join(str(r['region'])+':'+r['name'] for r in a['room_sequence']),'BEDS',[o['id'] for o in a['goal_same_region_beds']])


if __name__=='__main__':main()
