"""Add explicit pickup detours to original bed-goal routes without changing their order."""
from pathlib import Path
import json
import math
from search_room_tasks import shortest, obb_distance

ROOT=Path(__file__).resolve().parent


def graph_for(scan):
    rows=json.loads((ROOT.parent/'sources'/f'{scan}_connectivity.json').read_text())
    g={r['image_id']:[] for r in rows if r['included']}
    for r in rows:
        if not r['included']:continue
        for ok,v in zip(r['unobstructed'],rows):
            if ok and v['included']:
                g[r['image_id']].append((v['image_id'],math.dist([r['pose'][i] for i in (3,7,11)],[v['pose'][i] for i in (3,7,11)])))
    coordinates={r['image_id']:[r['pose'][i] for i in (3,7,11)] for r in rows if r['included']}
    return g,coordinates


def main():
    audits=json.loads((ROOT/'all_28_room_audits.json').read_text())
    variants=[]
    for r in audits:
        beds=[o for o in r['goal_same_region_beds'] if o['obb_distance_m']<=1.5]
        if not beds:continue
        h=json.loads((ROOT/'sources'/f"{r['scan']}_rooms.json").read_text());pans=h['panoramas'];g,coordinates=graph_for(r['scan'])
        nora_options=[None]+[o['nora_region'] for o in r['bedroom_avoidance_options'] if not o['original_route_enters_forbidden_room']]
        for nora in nora_options:
            blocked={v for v in g if pans[v]['region']==nora} if nora is not None else set()
            for vp,p in pans.items():
                if vp not in g or h['regions'][str(p['region'])]['label'] not in ('a','t'):continue
                fixtures=[dict(o,obb_distance_m=obb_distance(p['position'],o)) for o in h['objects']
                          if o['region']==p['region'] and (o['category'] in ('sink','cabinet','counter','shelving') or 'vanity' in o['raw'])]
                fixtures.sort(key=lambda o:o['obb_distance_m'])
                if not fixtures or fixtures[0]['obb_distance_m']>3:continue
                options=[]
                for i,(a,b) in enumerate(zip(r['path'],r['path'][1:])):
                    pa=shortest(g,a,vp,blocked);pb=shortest(g,vp,b,blocked)
                    if pa and pb:
                        added=pa['length_m']+pb['length_m']-math.dist(coordinates[a],coordinates[b])
                        options.append((added,i,pa,pb))
                if not options:continue
                added,i,pa,pb=min(options,key=lambda x:x[0])
                path=r['path'][:i]+pa['path']+pb['path'][1:]+r['path'][i+2:]
                length=sum(math.dist(coordinates[a],coordinates[b]) for a,b in zip(path,path[1:]))
                assert abs(length-r['route_length_m']-added)<1e-8
                assert not any(v in blocked for v in path)
                # Original guide order must survive verbatim as a subsequence.
                iterator=iter(path)
                assert all(any(v==u for v in iterator) for u in r['path'])
                variants.append(dict(source_split=r['split'],scan=r['scan'],source_path_id=r['path_id'],
                    source_length_m=r['route_length_m'],adapted_length_m=length,added_length_m=added,
                    source_path=r['path'],path=path,positions_mp3d=[coordinates[v] for v in path],
                    pickup_viewpoint=vp,pickup_region=p['region'],pickup_index=path.index(vp),
                    pickup_storage_fixtures=fixtures,riya_region=beds[0]['region'],bed_object_id=beds[0]['id'],
                    nora_region=nora,forbidden_viewpoints=sorted(blocked),
                    authored=True,source_instructions_unchanged=True,
                    graph_edges_verified=True,continuous_route_verified=False,
                    shortcut_avoidance_demonstrated=False,
                    warning='New authored task. Preserves the original guide detours, not shortest delivery distance. Nora constraint has no demonstrated shortcut conflict.'))
    variants.sort(key=lambda v:(v['adapted_length_m'],v['nora_region'] is not None,v['nora_region'] or -1))
    (ROOT/'all_authored_pickup_adaptations.json').write_text(json.dumps(variants,indent=2))
    extension_options=[]
    for r in audits:
        h=json.loads((ROOT/'sources'/f"{r['scan']}_rooms.json").read_text());pans=h['panoramas'];g,coords=graph_for(r['scan'])
        pickups=[]
        for j,v in enumerate(r['path']):
            reg=pans[v]['region']
            if h['regions'][str(reg)]['label'] not in ('a','t'):continue
            fixtures=[o for o in h['objects'] if o['region']==reg and
                      (o['category'] in ('sink','counter','cabinet','shelving') or 'vanity' in o['raw'])]
            if fixtures:pickups.append(dict(index=j,viewpoint=v,region=reg,fixtures=[o['id'] for o in fixtures]))
        if not pickups:continue
        allowed_noras=[None]+[o['nora_region'] for o in r['bedroom_avoidance_options'] if not o['original_route_enters_forbidden_room']]
        for nora in allowed_noras:
            blocked={v for v in g if pans[v]['region']==nora} if nora is not None else set()
            for bed in [o for o in h['objects'] if o['category']=='bed' and h['regions'].get(str(o['region']),{}).get('label')=='b' and o['region']!=nora]:
                options=[]
                for vp,p in pans.items():
                    if vp not in g or p['region']!=bed['region'] or obb_distance(p['position'],bed)>1.5:continue
                    leg=shortest(g,r['path'][-1],vp,blocked)
                    if leg:options.append((leg['length_m'],vp,leg))
                if not options:continue
                extra,goal,leg=min(options,key=lambda x:x[0]);path=r['path']+leg['path'][1:]
                assert not any(v in blocked for v in path)
                extension_options.append(dict(scan=r['scan'],source_split=r['split'],source_path_id=r['path_id'],
                    source_length_m=r['route_length_m'],adapted_length_m=r['route_length_m']+extra,
                    added_delivery_leg_m=extra,goal_viewpoint=goal,bed_object_id=bed['id'],riya_region=bed['region'],
                    nora_region=nora,pickups=pickups,path=path,authored=True,
                    original_goal_changed=True,continuous_route_verified=False,
                    warning='Retains the original non-bed stop as a waypoint, then adds a delivery leg. May overshoot a bed passed earlier; not a shortest delivery route.'))
    (ROOT/'bathroom_source_delivery_extensions.json').write_text(json.dumps(extension_options,indent=2))
    chosen=min((v for v in variants if v['nora_region']==26),key=lambda v:v['adapted_length_m'])
    chosen.update(task_individual="Riya is packing for her trip. Bring her toiletries to her bed.",
        task_combined="Riya is packing for her trip. Bring her toiletries to her bed. Don't go through Nora's room; she's sleeping!",
        authored_memory=["Riya's bed is in bedroom region 21.",
                         "Riya keeps her toiletries beside the sink in the downstairs bathroom, region 20.",
                         "Nora sleeps in bedroom region 26. Do not enter that room."],
        pickup_objects_placed=False,placement_status='pending measured surface placement',
        source_review_index=6,physical_gpu=0)
    (ROOT/'environment_06/scenario.json').write_text(json.dumps(chosen,indent=2))
    print('authored variants',len(variants),'source routes',len({(v['source_split'],v['source_path_id']) for v in variants}),
          'chosen length',chosen['adapted_length_m'],'pickup region',chosen['pickup_region'])


if __name__=='__main__':main()
