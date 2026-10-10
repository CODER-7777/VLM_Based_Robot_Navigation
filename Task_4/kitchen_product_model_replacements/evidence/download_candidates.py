import os,json,hashlib
from pathlib import Path
os.environ['HOME']='/data/robotics/toshith/k3d_cache'
import objaverse
out=Path('/data/robotics/toshith/rxr_author/refined/kitchen_product_replacements')
rows=json.loads((out/'download_candidates.json').read_text());paths=objaverse.load_objects(uids=[r['uid'] for r in rows],download_processes=2)
for row in rows:
 path=paths.get(row['uid'])
 if path:row.update(path=path,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
 print('PRODUCT_DOWNLOADED',row['name'],bool(path),flush=True)
(out/'downloaded_models.json').write_text(json.dumps(rows,indent=2))
