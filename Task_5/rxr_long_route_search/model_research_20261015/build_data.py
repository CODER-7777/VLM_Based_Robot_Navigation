"""Assemble a portable local review dashboard from the actual RxR files."""
from pathlib import Path
import json
import shutil
from datetime import datetime, timezone
from PIL import Image
import trimesh

ROOT=Path(__file__).resolve().parent
SEARCH=ROOT.parent
DIST=ROOT/'dashboard/dist'


def copy_image(src, dest):
    path=DIST/dest; path.parent.mkdir(parents=True,exist_ok=True)
    im=Image.open(src).convert('RGB'); im.thumbnail((1100,1100)); im.save(path,quality=90)
    return dest


def main():
    selected=json.loads((SEARCH/'user_validated_selection/selection.json').read_text())
    approved=set(selected['accepted_review_indices'])
    descriptions={r['review_index']:r['endpoint_description'] for r in selected['selected_routes']}
    routes=[]
    for path in sorted((SEARCH/'rxr_28_goal_images/goal_images_28').glob('*/goal_metadata.json')):
        d=json.loads(path.read_text());idx=d['review_index']
        conn=json.loads((SEARCH/'sources'/(d['scan']+'_connectivity.json')).read_text())
        poses={c['image_id']:[c['pose'][3],c['pose'][7],c['pose'][11]] for c in conn}
        points=[poses[v] for v in d['path']]
        variants=[v for v in d.get('instruction_variants',[]) if v.get('language','').startswith('en')]
        if not variants: variants=[{'language':d['language'],'instruction':d['instruction'],'instruction_id':d['instruction_id']}]
        images=[copy_image(path.parent/f'goal_heading_{h:03d}.png',f'assets/routes/{idx:02d}_{h:03d}.jpg') for h in [0,90,180,270]]
        routes.append(dict(id=idx,split=d['split'],scene=d['scan'],path_id=d['path_id'],length_m=d['route_length_m'],
                           direct_distance_m=d['direct_distance_m'],selected=idx in approved,description=descriptions.get(idx,'Reviewed endpoint; not selected by the user'),
                           goal_viewpoint=d['goal_viewpoint'],start_viewpoint=d['start_viewpoint'],viewpoints=d['path'],points_mp3d=points,
                           instructions=variants,images=images,status='Placement candidate' if idx==4 else ('User-selected endpoint' if idx in approved else 'Outside selected set')))
    sketches=json.loads((ROOT/'sketchfab_models.json').read_text())
    downloads={m['id']:m for m in json.loads((ROOT/'downloads.json').read_text()) if m.get('file')}
    chosen=['64249ba38f5045bdaabbb5749aa30033','708a2854348b46c7aa0fd9af55fe76a5','524d7fc724094ead9f203ed06bae76e1',
            'bbbb1521eb0a4c0296cf515503efb5ca','5e8ee405f4494081b2c09953a4363c8f','0ffbecc68a4040cfbec56fe91b688b56',
            '14d4adabb2564307ae69838eb4cac51a','c3f9ac6e6930473e9eef58933f8c14c3','b8037798633640e7bf040aac16ea8d45']
    notes={
      chosen[0]:('4K photoscan · school-specific','Closest free school-bag candidate. Official download requires a Sketchfab login/token; not downloaded.'),
      chosen[1]:('New local scan · repaired mesh','Xtreme-brand backpack scanned and repaired in Maya/Substance by its author. Public GLB downloaded for inspection; not placed in the scene.'),
      chosen[2]:('Cloth-modelled school backpack','Author used Marvelous Designer and Substance Painter. Mesh not downloaded; official download requires login.'),
      chosen[3]:('4K photoscan · compact mesh','Author advertises a 4K diffuse and normal map. Public preview inspected; mesh not downloaded.'),
      chosen[4]:('New local photoscan','Photo scan includes a support/display base. Downloaded for inspection; base cleanup required before placing.'),
      chosen[5]:('Brand-quality scanning reference','Arkify demonstrates soft-goods scanning. Download disabled in author metadata; reference only.'),
      chosen[6]:('Photo scan · alternative color','Red backpack scan. A public archived GLB exists; not downloaded in this search.'),
      chosen[7]:('Product / advertising candidate','High-resolution printed school bags. NoAI restriction on the listing needs rights review for VLM use; not downloaded.'),
      chosen[8]:('Current environment 04 model','Tan canvas scan already used in revision 03. Included as the baseline; user has requested a better school-backpack alternative.')}
    models=[]
    for uid in chosen:
        m=next(x for x in sketches if x['id']==uid)
        label,note=notes[uid];local=downloads.get(uid)
        license=m.get('license') or {}
        row=dict(id=uid,name=m['name'],author=m.get('author'),source=m.get('source'),embed=m.get('embed'),preview=m.get('preview'),
                 platform='Sketchfab',license=license.get('label','No download license supplied'),license_url=license.get('url'),
                 access='Downloaded' if local else ('Reference only' if not m.get('downloadable') else 'Login required'),
                 price='Free / attribution' if license.get('slug','').startswith('by') else 'See source',
                 texture='4K advertised' if uid in [chosen[0],chosen[3]] else ('1K source textures' if uid==chosen[8] else 'See author metadata'),
                 triangles=m.get('triangles'),fit=label,note=note,local_file=local.get('file') if local else None,
                 downloaded=bool(local),preferred=uid in chosen[:4],formats='glTF / GLB in local archive' if local else 'Check official download',
                 evidence='Author metadata and public preview; inspected 2026-10-15')
        if local:
            scene=trimesh.load(DIST/local['file'],force='scene')
            textures=[]
            for geom in scene.geometry.values():
                material=getattr(geom.visual,'material',None)
                img=getattr(material,'baseColorTexture',None)
                if img is None: img=getattr(material,'image',None)
                if img is not None: textures.append(list(img.size))
            row['mesh_inspection']={'meshes':len(scene.geometry),'faces':sum(len(g.faces) for g in scene.geometry.values()),'base_color_texture_sizes':textures,'source_sha256':local['sha256'],'bytes':local['bytes']}
            row['texture']=' / '.join(sorted(set(f'{w}×{h}' for w,h in textures))) or 'No embedded base-color image found'
        if uid==chosen[8]:
            src=SEARCH/'environment_04/revision_02/assets/canvas_backpack_baked_clean_40cm.glb'
            dst=DIST/'assets/glb/current_canvas.glb';shutil.copy2(src,dst);row.update(local_file='assets/glb/current_canvas.glb',downloaded=True,access='Current baseline')
        models.append(row)
    markets=json.loads((ROOT/'marketplace_models.json').read_text())
    for m in markets:
        m.update(downloaded=False,local_file=None,preferred=m['id'] in ['3dtrix-safari','3dtrix-school'],evidence='Official seller listing; specifications advertised, file not inspected')
        m.pop('advertised_file_links',None)
    # Put strong school-specific options first, while retaining source/account limits.
    models=models[:2]+[m for m in markets if m['id'].startswith('3dtrix')]+models[2:]+[m for m in markets if not m['id'].startswith('3dtrix')]
    models.append(dict(id='jansport-brand',name='JanSport brand product viewers',author='JanSport organization',platform='Sketchfab / brand',
                       source='https://sketchfab.com/Jansport/models',preview=None,access='Reference collection',price='Viewing only',license='No reuse permission verified',
                       texture='Product presentation reference',formats='Viewer collection; not a downloaded asset',fit='Advertising / product reference',
                       note='Public brand collection includes Main Campus and SuperBreak variants. No model files extracted or downloaded.',downloaded=False,local_file=None,preferred=False))
    scenario=json.loads((SEARCH/'environment_04/revision_03/scenario.json').read_text())
    contact=json.loads((SEARCH/'environment_04/revision_03/contact_checks.json').read_text())
    placements=[]
    for obj in scenario['objects']:
        key=obj['object_id']; label='Brown seat' if 'brown' in key else 'Pink chair'
        images={kind:copy_image(SEARCH/f'environment_04/revision_03/placed/{key}_{kind}_detail.png',f'assets/placements/{key}_{kind}.jpg') for kind in ['close','side','contact','back']}
        placements.append(dict(id=key,label=label,images=images,position=obj['object_translation'],rotation=obj['rotation_xyzw'],
                               lean_degrees=obj['lean_back_degrees'],contact=next(c for c in contact if c['object_id']==key),status='Candidate · user visual validation pending'))
    data=dict(updated=datetime.now(timezone.utc).isoformat(),title='RxR Route & Object Studio',selected_indices=sorted(approved),routes=routes,models=models,
              placements=placements,research=dict(screened_model_records=len(sketches),curated_options=len(models),new_downloads=len(downloads),
              sources=['Sketchfab','CGTrader','TurboSquid','ArtStation','3DTRIXS','Polycam','Superhive','Fab','AllenAI Objaverse'],
              scope='Targeted public searches and author APIs; not a complete crawl of the web.'),
              instruction="Quick! Riya’s bus is here! But she still needs her school bag.",
              limitations=['All displayed route lengths are original annotated RxR guide lengths, not shortest navigation distances.',
                           'User-selected endpoints are plausible placement locations; they do not establish a visible school bag or a storage routine.',
                           'Environment 04 is a rendered geometry-fit candidate. Neither contact physics nor complete guide-route playback is established.'])
    (DIST/'data.json').write_text(json.dumps(data,indent=2)+'\n')
    (ROOT/'RESEARCH_REPORT.md').write_text('# School backpack model research\n\nScreened '+str(len(sketches))+' public model records; curated '+str(len(models))+' options. Downloaded '+str(len(downloads))+' new CC-BY scans from the official AllenAI Objaverse distribution.\n\n'+''.join(f"- [{m['name']}]({m['source']}): {m['access']}. {m['note']}\n" for m in models)+'\nSeller texture/quality claims are identified in the dashboard. A public advertising viewer does not establish download or reuse permission. Prices were observed on source listings and can change.\n')
    print('Dashboard data:',len(routes),'routes,',len(models),'model options,',len(placements),'placements')
    for m in models:
        if m.get('mesh_inspection'):print(m['name'],m['mesh_inspection'])


if __name__=='__main__': main()
