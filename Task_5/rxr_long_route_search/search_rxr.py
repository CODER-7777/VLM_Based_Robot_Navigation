"""Audit RxR validation guide routes from official annotations and graph coordinates."""
from pathlib import Path
import urllib.request, json, gzip, math, concurrent.futures, hashlib, time
ROOT=Path(__file__).resolve().parent
RAW=ROOT/'sources'; RAW.mkdir(exist_ok=True)
SOURCES=[]
def fetch(url, name):
    p=RAW/name
    if not p.exists():
        for retry in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'RxR-route-audit'}),timeout=60) as r: data=r.read()
                p.write_bytes(data); break
            except Exception:
                if retry==2: raise
                time.sleep(1)
    data=p.read_bytes()
    SOURCES.append({'url':url,'file':str(p.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    return data
splits=['val_seen','val_unseen']
def guides(split):
    data=fetch(f'https://storage.googleapis.com/rxr-data/rxr_{split}_guide.jsonl.gz',f'rxr_{split}_guide.jsonl.gz')
    rows=[json.loads(x) for x in gzip.decompress(data).splitlines() if x]
    print(split,'guide records',len(rows),flush=True)
    return rows
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    records=sum(list(pool.map(guides,splits)),[])
scans=sorted({r['scan'] for r in records})
rev=json.loads(fetch('https://api.github.com/repos/peteanderson80/Matterport3DSimulator/commits/master','connectivity_revision.json'))['sha']
def graph(scan):
    rows=json.loads(fetch(f'https://raw.githubusercontent.com/peteanderson80/Matterport3DSimulator/{rev}/connectivity/{scan}_connectivity.json',f'{scan}_connectivity.json'))
    return scan,({x['image_id']:([x['pose'][3],x['pose'][7],x['pose'][11]],i,x) for i,x in enumerate(rows)},rows)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: graphs=dict(pool.map(graph,scans))
long=[]; totals={s:{'guide_records':0,'unique_paths':set(),'long_guide_records':0,'long_unique_paths':set(),'max_route_m':0} for s in splits}
for r in records:
    g,rows=graphs[r['scan']]; path=r['path']; pts=[g[v][0] for v in path]
    length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
    t=totals[r['split']];t['guide_records']+=1;t['unique_paths'].add(r['path_id']);t['max_route_m']=max(t['max_route_m'],length)
    if length<40: continue
    t['long_guide_records']+=1;t['long_unique_paths'].add(r['path_id'])
    bad=[(a,b) for a,b in zip(path,path[1:]) if not g[a][2]['unobstructed'][g[b][1]] or not g[a][2]['included'] or not g[b][2]['included']]
    out={k:r[k] for k in ['split','instruction_id','language','path_id','scan','heading','path','instruction']}
    out.update(route_length_m=length,direct_distance_m=math.dist(pts[0],pts[-1]),start_viewpoint=path[0],goal_viewpoint=path[-1],start_position_mp3d=pts[0],goal_position_mp3d=pts[-1],invalid_graph_edges=bad)
    long.append(out)
for t in totals.values():
    for k in ['unique_paths','long_unique_paths']:t[k]=len(t[k])
long.sort(key=lambda x:(x['split'],x['path_id'],x['language'],x['instruction_id']))
(ROOT/'all_validation_routes_ge40m.json').write_text(json.dumps(long,ensure_ascii=False,indent=2))
(ROOT/'search_summary.json').write_text(json.dumps({'scope':'Official RxR validation guide paths; 3D graph-edge sum, not follower detours or RxR-CE dense traces','threshold_m':40,'connectivity_revision':rev,'splits':totals,'sources':sorted(SOURCES,key=lambda x:x['file'])},indent=2))
print(json.dumps(totals,indent=2),flush=True)
eng=[x for x in long if x['language'].startswith('en')]
(ROOT/'long_routes_english.txt').write_text('\n\n'.join(f"{x['split']} path={x['path_id']} instruction={x['instruction_id']} scan={x['scan']} route={x['route_length_m']:.6f}m\n{x['instruction']}" for x in eng))
print('English long instructions',len(eng),'unique paths',len({(x['split'],x['path_id']) for x in eng}),flush=True)
