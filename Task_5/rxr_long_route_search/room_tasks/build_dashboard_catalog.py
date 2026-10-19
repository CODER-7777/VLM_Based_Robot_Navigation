"""Join reviewed RxR sources and authored variants for the interactive inspector."""
from pathlib import Path
import csv
import json

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent


def main():
    audits=json.loads((ROOT/'all_28_room_audits.json').read_text())
    annotations=json.loads((BASE/'all_validation_routes_ge40m.json').read_text())
    accepted=set(json.loads((BASE/'user_validated_selection/selection.json').read_text())['accepted_review_indices'])
    nora=json.loads((ROOT/'nora_compatible_original_routes_room_options.json').read_text())
    primary=json.loads((ROOT/'all_authored_pickup_adaptations.json').read_text())
    secondary=json.loads((ROOT/'bathroom_source_delivery_extensions.json').read_text())
    images=list(csv.DictReader((BASE/'goal_images_28/goal_image_index.csv').open()))
    chosen=json.loads((ROOT/'environment_06/scenario.json').read_text())
    scenes={}
    for scan in sorted({r['scan'] for r in audits}):
        house=json.loads((ROOT/'sources'/f'{scan}_rooms.json').read_text())
        graph=json.loads((BASE/'sources'/f'{scan}_connectivity.json').read_text())
        coords={r['image_id']:[r['pose'][i] for i in (3,7,11)] for r in graph if r['included']}
        scenes[scan]=dict(scan=scan,regions=house['regions'],panoramas=house['panoramas'],
            coordinates=coords,props=[],beds=[o for o in house['objects'] if o['category']=='bed'],
            scene_asset=f'/data/robotics/toshith/vln_baselines/data/scene_datasets/mp3d/{scan}/{scan}.glb')
    for o in json.loads((ROOT/'environment_06/placements.json').read_text()):
        scenes['VFuaQ6m2Qom']['props'].append(dict(id=o['object_id'],label='Conditioner tube' if o['object_id']=='conditioner' else 'Boxed eye cream',
            asset='/tmp/rxr_room_tasks_20261015/placement/'+o['asset'],translation=o['translation'],rotation_xyzw=o['rotation_xyzw'],
            target=[o['translation'][0],o['translation'][1]+o['physical_height_m']/2,o['translation'][2]],
            eye=[-18.5,1.55,-6.25],region=20))
    bag=json.loads((BASE/'environment_04/revision_03/scenario.json').read_text())
    for o in bag['objects']:
        pos=o['translation_world']
        scenes['SN83YJsR3w2']['props'].append(dict(id=o['object_id'],label='School bag on brown seat' if 'brown' in o['object_id'] else 'School bag on pink seat',
            asset='/tmp/rxr_schoolbags_env04_20261015/environment_04/revision_03/'+o['asset'],translation=pos,rotation_xyzw=o['rotation_xyzw'],
            target=[pos[0],pos[1]+.2,pos[2]],eye=[pos[0]-.9,pos[1]+1,pos[2]+1.3],region=7))
    routes=[]
    for r in audits:
        scan=r['scan'];pathid=r['path_id'];scene=scenes[scan]
        key=f"{r['split']}:{scan}:{pathid}"
        rows=[a for a in annotations if a['split']==r['split'] and a['scan']==scan and a['path_id']==pathid]
        photos=next(a for a in images if a['scan']==scan and int(a['path_id'])==pathid)
        options=[o for o in nora if o['scan']==scan and o['path_id']==pathid and o['split']==r['split']]
        variants=[dict(id='original',kind='original',label='Original RxR guide',path=r['path'],
            positions_raw=[scene['coordinates'][v] for v in r['path']],length_m=r['route_length_m'],
            nora_region=None,pickup_index=None,riya_region=None,authored=False,
            note='Original guide waypoints. Step playback previews camera positions; it is not a navigation rollout.')]
        for j,a in enumerate(primary):
            if a['scan']!=scan or a['source_path_id']!=pathid or a['source_split']!=r['split']:continue
            combined=a['nora_region'] is not None
            is_chosen=a['path']==chosen['path'] and a['nora_region']==chosen['nora_region']
            variants.append(dict(id=f'pickup-{j}',kind='combined' if combined else 'toiletries',
                label=('★ Prepared combined task' if is_chosen else ('Combined' if combined else 'Toiletries'))+f" · bathroom {a['pickup_region']}"+(f" · avoid room {a['nora_region']}" if combined else ''),
                path=a['path'],positions_raw=a['positions_mp3d'],length_m=a['adapted_length_m'],
                nora_region=a['nora_region'],pickup_index=a['pickup_index'],pickup_region=a['pickup_region'],riya_region=a['riya_region'],
                authored=True,prepared=is_chosen,requires_new_goal=False,
                note='Bathroom pickup detour added; original guide order and bed-adjacent goal retained. No bedroom shortcut conflict is demonstrated.'))
        for j,a in enumerate(secondary):
            if a['scan']!=scan or a['source_path_id']!=pathid or a['source_split']!=r['split']:continue
            variants.append(dict(id=f'extension-{j}',kind='combined' if a['nora_region'] is not None else 'toiletries',
                label=f"New bed goal · bedroom {a['riya_region']}"+(f" · avoid {a['nora_region']}" if a['nora_region'] is not None else ''),
                path=a['path'],positions_raw=[scene['coordinates'][v] for v in a['path']],length_m=a['adapted_length_m'],
                nora_region=a['nora_region'],pickup_index=a['pickups'][0]['index'],pickup_region=a['pickups'][0]['region'],
                riya_region=a['riya_region'],authored=True,prepared=False,requires_new_goal=True,
                note='Secondary authored candidate with a new bed delivery leg. Props and new goal have not been visually validated; original guide can overshoot the bed.'))
        prepared=next((v['id'] for v in variants if v.get('prepared')),None)
        tags=[]
        if r['review_index'] in accepted:tags.append('schoolbag')
        if options:tags.append('nora-compatible')
        if any(o['route_steps_adjacent_to_room'] for o in options):tags.append('nora-strong')
        if len(variants)>1:tags+=['toiletries','combined']
        if r['endpoint_delivery_eligible']:tags.append('bed-goal')
        routes.append(dict(id=key,index=r['review_index'],scan=scan,path_id=pathid,split=r['split'],
            source_length_m=r['route_length_m'],description=photos['endpoint_description'],tags=tags,
            schoolbag_selected=r['review_index'] in accepted,nora_options=options,variants=variants,
            default_variant=prepared or 'original',goal_contact_sheet='/goal_images_28/'+photos['contact_sheet'],
            goal_views=['/goal_images_28/'+str(Path(photos['contact_sheet']).parent/f'goal_heading_{h:03d}.png') for h in (0,90,180,270)],
            instructions=[dict(id=a['instruction_id'],language=a['language'],text=a['instruction']) for a in rows],
            original_heading=rows[0]['heading'],original_room_sequence=r['room_sequence']))
    catalog=dict(version=1,title='RxR trajectory and room inspector',routes=routes,scenes=scenes,
        counts=dict(original_routes=len(routes),schoolbag_selected=len(accepted),nora_compatible=25,nora_stronger=2,
                    toiletries_sources=8,authored_variants=sum(len(r['variants'])-1 for r in routes)),
        defaults=dict(route='val_seen:VFuaQ6m2Qom:5721'),
        notes=['Original validation guide length ≥40 m. Authored variants are not additional original RxR trajectories.',
               'Inspection mode permits visiting candidate Nora rooms. No navigation or manipulation success is claimed.'])
    (ROOT/'dashboard_catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
    print(json.dumps(catalog['counts']))


if __name__=='__main__':main()
