"""Collect public author metadata and preview images; no login or viewer extraction."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
import re
import requests
import html
from PIL import Image
from io import BytesIO

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'dashboard/dist/assets/models'
OUT.mkdir(parents=True, exist_ok=True)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Research preview collection; public source metadata)'}


def get(url):
    return requests.get(url, headers=HEADERS, timeout=35)


def image_file(url, ident):
    try:
        r=get(url); r.raise_for_status()
        im=Image.open(BytesIO(r.content)).convert('RGB')
        im.thumbnail((900,900))
        name=ident+'.jpg'; im.save(OUT/name,quality=90)
        return 'assets/models/'+name
    except Exception as e:
        return None


def sketch(uid):
    url='https://api.sketchfab.com/v3/models/'+uid
    try:
        r=get(url); r.raise_for_status(); d=r.json()
        (ROOT/'metadata').mkdir(exist_ok=True)
        (ROOT/'metadata'/(uid+'.json')).write_text(json.dumps(d,indent=2))
        images=d.get('thumbnails',{}).get('images',[])
        image=min(images,key=lambda x:abs(x.get('width',0)-720)) if images else {}
        return dict(id=uid,name=d.get('name'),author=d.get('user',{}).get('displayName'),
                    source=d.get('viewerUrl'),embed=d.get('embedUrl'),
                    downloadable=d.get('isDownloadable'),license=d.get('license'),
                    triangles=d.get('faceCount'),vertices=d.get('vertexCount'),
                    texture_count=d.get('textureCount'),description=d.get('description'),
                    preview=image_file(image.get('url'),uid) if image else None,
                    published=d.get('publishedAt'))
    except Exception as e:
        return dict(id=uid,error=str(e))


def page(model):
    try:
        r=get(model['source']); model['http_status']=r.status_code
        if r.status_code != 200: return model
        text=r.text
        matches=re.findall(r'<meta\b[^>]+>',text,re.I)
        img=None
        for tag in matches:
            if re.search(r'(?:property|name)=[\"\'](?:og:image|twitter:image)[\"\']',tag,re.I):
                value=re.search(r'content=[\"\']([^\"\']+)',tag,re.I)
                if value: img=html.unescape(value.group(1)); break
        if img:
            model['preview']=image_file(img,model['id'])
            model['preview_source']=img
        # Public, advertised download links only. Never inspect protected viewer payloads.
        model['advertised_file_links']=list(dict.fromkeys(re.findall(r'https?://[^\s\"\'<>]+\.(?:glb|gltf|fbx|zip)(?:\?[^\s\"\'<>]*)?',text)))[:12]
    except Exception as e: model['error']=str(e)
    return model


def main():
    searches=[]; ids=set()
    queries=['school backpack','backpack photoscan','backpack photogrammetry']
    for query in queries:
        r=requests.get('https://api.sketchfab.com/v3/search',params={'type':'models','q':query,'count':24,'downloadable':'true'},headers=HEADERS,timeout=35)
        if r.ok:
            d=r.json(); searches.append({'query':query,'results':d.get('results',[])})
            ids.update(x['uid'] for x in d.get('results',[]))
        else: searches.append({'query':query,'http_status':r.status_code})
    (ROOT/'sketchfab_public_search.json').write_text(json.dumps(searches,indent=2))
    # Exact, publicly identified school bag and brand-reference examples.
    ids.update(['64249ba38f5045bdaabbb5749aa30033','524d7fc724094ead9f203ed06bae76e1','0ffbecc68a4040cfbec56fe91b688b56','c3f9ac6e6930473e9eef58933f8c14c3','b8037798633640e7bf040aac16ea8d45'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        models=list(pool.map(sketch,sorted(ids)))
    mapping=json.load(gzip.open(ROOT.parent/'environment_04/revision_02/assets/objaverse_mapping.json.gz','rt'))
    for model in models:
        if model['id'] in mapping:
            model['public_objaverse_glb']='https://huggingface.co/datasets/allenai/objaverse/resolve/main/'+mapping[model['id']]
    (ROOT/'sketchfab_models.json').write_text(json.dumps(models,indent=2))
    print('public API model records:',len(models),'public Objaverse matches:',sum('public_objaverse_glb' in x for x in models),flush=True)
    for m in models:
        if 'public_objaverse_glb' in m: print('MATCH',m['id'],m.get('name'),m.get('license',{}).get('label'),flush=True)
    # Brand's own public product collection (metadata only).
    r=get('https://api.sketchfab.com/v3/users/Jansport/models?count=24')
    if r.ok:
        data=r.json(); (ROOT/'jansport_brand_models.json').write_text(json.dumps(data,indent=2))
        brand=[]
        for d in data.get('results',[])[:4]: brand.append(sketch(d['uid']))
        (ROOT/'jansport_brand_previews.json').write_text(json.dumps(brand,indent=2))
        print('brand product previews:',len(brand),flush=True)
    listing=json.loads((ROOT/'marketplace_sources.json').read_text())
    with ThreadPoolExecutor(max_workers=4) as pool: pages=list(pool.map(page,listing))
    (ROOT/'marketplace_models.json').write_text(json.dumps(pages,indent=2))
    print('marketplace pages:',[(m['id'],m.get('http_status'),bool(m.get('preview'))) for m in pages],flush=True)


if __name__=='__main__': main()
