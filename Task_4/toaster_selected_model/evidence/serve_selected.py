import importlib.util,json,sys
from pathlib import Path
ROOT=Path('/data/robotics/toshith/rxr_author')
W=ROOT/'refined/toaster_selected'
O=ROOT/'refined/kitchen/objects/toaster_v4'
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('kitchen_route_base',ROOT/'author_pov_route.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
banner='''<div style="padding:12px;background:#153c2c;border-radius:6px;margin-bottom:12px">
<strong>Selected toaster installed — all other kitchen repairs retained</strong>
<p>Real photograph | previous toaster | selected AtTheSpeedOf toaster</p>
<img src="/repair-preview/toaster.jpg" style="width:100%" alt="Latest selected toaster comparison">
<p>Model: toaster by AtTheSpeedOf, CC BY 4.0. Original PBR maps preserved. The dashboard uses fixed kitchen-lighting reflections; branding and control arrangement differ from the Black &amp; Decker reference.</p>
<a href="/product-viewer">Rotate the downloaded model with metallic PBR lighting</a>
<details><summary>Earlier comparisons for all other repaired objects</summary>
<p>These saved panels predate the latest toaster change.</p>
<img src="/repair-preview/compare1.jpg" style="width:100%">
<img src="/repair-preview/compare2.jpg" style="width:100%">
<img src="/repair-preview/compare3.jpg" style="width:100%">
</details></div>'''
app.HTML=app.HTML.replace('<h2>Habitat first-person route author</h2>','<h2>Habitat first-person route author</h2>'+banner)
app.HTML=app.HTML.replace('port 8766 is running','the repaired kitchen dashboard is running')
original=app.make_handler
def make_handler(session):
 base=original(session)
 previous=ROOT/'refined/agentA_resume/previews'
 files={
 '/repair-preview/toaster.jpg':W/'previews/toaster_comparison.jpg',
 '/repair-preview/full.jpg':W/'previews/toaster_full_scene.jpg',
 '/repair-preview/toaster-novel.jpg':W/'previews/toaster_novel_views.jpg',
 '/repair-preview/compare1.jpg':previous/'agentA_resume_compare1.jpg',
 '/repair-preview/compare2.jpg':previous/'agentA_resume_compare2.jpg',
 '/repair-preview/compare3.jpg':previous/'agentA_resume_compare3.jpg',
 '/repair-preview/novel.jpg':previous/'agentA_resume_novel.jpg',
 }
 class Handler(base):
  def do_GET(self):
   path=self.path.split('?',1)[0]
   if path in files:self.send_bytes(200,'image/jpeg',files[path].read_bytes())
   elif path=='/toaster-pbr.glb':self.send_bytes(200,'model/gltf-binary',(O/'product_pbr.glb').read_bytes())
   elif path=='/model-viewer.min.js':self.send_bytes(200,'text/javascript',(W/'dashboard/model-viewer.min.js').read_bytes())
   elif path=='/product-viewer':
    html='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Selected toaster — PBR inspection</title><script type="module" src="/model-viewer.min.js"></script><style>body{margin:24px;background:#153c2c;color:white;font:16px sans-serif}a{color:#bbf7d0}model-viewer{width:100%;height:70vh;background:#ddd;border-radius:8px}</style></head><body><a href="/">Full kitchen editor</a> · <a href="/comparisons">All repair comparisons</a><h1>Downloaded toaster: original PBR material</h1><p>Drag to rotate; scroll to zoom. This view uses neutral studio illumination to inspect the original metallic/roughness and normal maps. The Habitat kitchen uses a separate fixed-reflection bake.</p><model-viewer src="/toaster-pbr.glb" camera-controls auto-rotate environment-image="neutral" exposure="1" shadow-intensity="1" camera-orbit="180deg 65deg auto" alt="Toaster by AtTheSpeedOf with original metallic materials"></model-viewer><p>This work is based on <a href="https://sketchfab.com/3d-models/toaster-0d39352a32404ce7b71b8ac020844949">toaster</a> by <a href="https://sketchfab.com/AtTheSpeedOf">AtTheSpeedOf</a>, licensed under <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Scaled uniformly for the kitchen scene. Hamilton Beach markings differ from the Black &amp; Decker reference.</p><p><a href="/toaster-pbr.glb" download="toaster_AtTheSpeedOf_CC-BY-4.0.glb">Download PBR GLB</a></p></body></html>'''
    self.send_bytes(200,'text/html; charset=utf-8',html.encode())
   elif path=='/scene-info':self.send_json({'scene_glb':str(session.scene_glb),'version':'toaster_selected','audit':json.loads((W/'audit.json').read_text()),'toaster_author':'AtTheSpeedOf','toaster_uid':'0d39352a32404ce7b71b8ac020844949','toaster_license':'CC-BY-4.0','pbr_viewer':'/product-viewer'})
   else:super().do_GET()
 return Handler
app.make_handler=make_handler
app.main()
