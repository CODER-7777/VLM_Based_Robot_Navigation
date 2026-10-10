from pathlib import Path
import json,gzip,re,time
cache=Path('/data/robotics/toshith/k3d_cache/.objaverse/hf-objaverse-v1/metadata')
out=Path('/data/robotics/toshith/rxr_author/refined/kitchen_product_replacements');out.mkdir(exist_ok=True)
groups={'coffee_machine':r'nespresso|pixie|essenza','frother':r'frother|aeroccino','glass_kettle':r'kettle|electric teapot','tea_tray':r'tea.?pot|tea set|sugar bowl','frogs':r'frog|toad','hot_tap':r'faucet|water tap|hot water dispenser|antique tap|vintage tap'}
patterns={k:re.compile(v,re.I) for k,v in groups.items()};found={k:[] for k in groups}
for index,file in enumerate(sorted(cache.glob('*.json.gz'))):
 with gzip.open(file,'rt') as f:data=json.load(f)
 for uid,m in data.items():
  text=m.get('name','')+' '+m.get('description','')+' '+' '.join(t.get('name','') for t in m.get('tags',[]))
  hits=[k for k,pat in patterns.items() if pat.search(text)]
  if not hits:continue
  lic=m.get('license') or {};lic={'slug':lic} if isinstance(lic,str) else lic;user=m.get('user') or {};user={'username':user} if isinstance(user,str) else user;stats=m.get('stats') or {};thumbs=(m.get('thumbnails') or {}).get('images',[])
  row={'uid':uid,'name':m.get('name'),'description':m.get('description','')[:350],'license':lic.get('slug'),'author':user.get('displayName') or user.get('username'),'url':m.get('viewerUrl'),'faces':m.get('faceCount',stats.get('faceCount')),'vertices':m.get('vertexCount',stats.get('vertexCount')),'downloadable':m.get('isDownloadable'),'thumbnail':max(thumbs,key=lambda i:i.get('width',0)).get('url') if thumbs else None}
  for k in hits:found[k].append(row)
 if index%30==0:print('SEARCH_CHUNKS',index,flush=True)
(out/'cached_model_candidates.json').write_text(json.dumps(found,indent=2))
print('SEARCH_DONE',{k:len(v) for k,v in found.items()},flush=True)
for key in ['coffee_machine','frother','glass_kettle']:
 for row in found[key]:print(key,row['uid'],row['name'],row['faces'],row['license'],flush=True)
