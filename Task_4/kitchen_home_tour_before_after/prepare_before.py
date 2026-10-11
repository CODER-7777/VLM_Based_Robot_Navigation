"""Browser-only earlier mesh: identical geometry, 1024px photographic atlases."""
from pathlib import Path
import sys,copy,io,json,hashlib
sys.path.insert(0,'/data/robotics/toshith/vivekananda/kitchen_repair_20261011/scripts')
import glb_tools as gt
from PIL import Image
ROOT=Path(__file__).resolve().parent
SOURCE=Path('/data/robotics/toshith/rxr_author/refined/2azQ1b91cZZ_v1_unpatched.glb')
TARGET=ROOT/'before_browser.glb'

if __name__=='__main__':
    g,b=gt.read(SOURCE);result=copy.deepcopy(g);replacements={};rows=[]
    original_views={i:b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']] for i,v in enumerate(g['bufferViews'])}
    for i,image in enumerate(result.get('images',[])):
        index=image['bufferView'];im=Image.open(io.BytesIO(original_views[index]));size=im.size
        im.thumbnail((1024,1024),Image.Resampling.LANCZOS)
        alpha=im.getchannel('A').getextrema()[0]<255 if 'A' in im.getbands() else False
        stream=io.BytesIO()
        if alpha:im.save(stream,format='PNG');image['mimeType']='image/png'
        else:im.convert('RGB').save(stream,format='JPEG',quality=94,subsampling=0);image['mimeType']='image/jpeg'
        replacements[index]=stream.getvalue();rows.append({'image':i,'original_size':list(size),'browser_size':list(im.size)})
    output=bytearray()
    for i,v in enumerate(result['bufferViews']):
        output.extend(b'\0'*((-len(output))%4));v['buffer']=0;v['byteOffset']=len(output)
        data=replacements.get(i,original_views[i]);v['byteLength']=len(data);output.extend(data)
        if i not in replacements:assert data==original_views[i]
    gt.write(TARGET,result,bytes(output));check,new=gt.read(TARGET)
    preserved=all(new[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]==original_views[i] for i,v in enumerate(check['bufferViews']) if i not in replacements)
    assert preserved and check['nodes']==g['nodes'] and check['meshes']==g['meshes'] and check['accessors']==g['accessors']
    report={'source':str(SOURCE),'source_sha256':gt.sha(SOURCE),'browser_scene':str(TARGET),'browser_sha256':gt.sha(TARGET),'bytes':TARGET.stat().st_size,'geometry_nodes_accessors_preserved':True,'texture_max_edge':1024,'texture_optimisation_applies_to':'earlier saved mesh only; repaired scene unchanged','images':rows}
    (ROOT/'evidence/before_browser.json').write_text(json.dumps(report,indent=2));print('BEFORE_BROWSER_READY',TARGET.stat().st_size,flush=True)
