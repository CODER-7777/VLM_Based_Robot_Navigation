"""Export actual texture-backed PBR repairs; shared reference assets are read only."""
from pathlib import Path
import copy, io, json, sys
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
import trimesh

OLD=Path('/data/robotics/toshith/vivekananda/kitchen_repair_20261011')
ROOT=Path('/data/robotics/toshith/vivekananda/kitchen_appliance_refinement_20261011')
sys.path.insert(0,str(OLD/'scripts'))
import glb_tools as gt

def add_array(g,b,a,kind,component=5126):
    a=np.asarray(a,dtype='<f4' if component==5126 else '<u4')
    b.extend(b'\0'*((-len(b))%4));off=len(b);b.extend(a.tobytes())
    bv=len(g.setdefault('bufferViews',[]));g['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':a.nbytes})
    ac={'bufferView':bv,'componentType':component,'count':len(a),'type':kind}
    if kind=='VEC3':ac.update(min=a.min(0).tolist(),max=a.max(0).tolist())
    ai=len(g.setdefault('accessors',[]));g['accessors'].append(ac);return ai

def add_texture(g,b,arr,name):
    img=Image.fromarray(np.uint8(np.clip(arr,0,255)));mem=io.BytesIO();img.save(mem,format='PNG')
    (ROOT/'textures').mkdir(exist_ok=True);(ROOT/'textures'/(name+'.png')).write_bytes(mem.getvalue())
    b.extend(b'\0'*((-len(b))%4));off=len(b);b.extend(mem.getvalue())
    bv=len(g.setdefault('bufferViews',[]));g['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':len(mem.getvalue())})
    im=len(g.setdefault('images',[]));g['images'].append({'name':name,'bufferView':bv,'mimeType':'image/png'})
    si=len(g.setdefault('samplers',[]));g['samplers'].append({'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':33071})
    ti=len(g.setdefault('textures',[]));g['textures'].append({'source':im,'sampler':si});return ti

def reset_raw(g,parts):
    """Flatten the fitted object's transforms; retain material and texture references."""
    g['nodes']=[];g['meshes']=[];g['scenes']=[{'nodes':[]}];g['scene']=0
    root={'name':'Raw_Zup_to_glTF_Yup','rotation':[-2**-.5,0,0,2**-.5],'children':[]}
    g['nodes'].append(root);g['scenes'][0]['nodes']=[0]

def mesh(g,b,name,v,f,material,uv=None,normals=None):
    if normals is None:
        tm=trimesh.Trimesh(v,f,process=False);normals=tm.vertex_normals
    att={'POSITION':add_array(g,b,v,'VEC3'),'NORMAL':add_array(g,b,normals,'VEC3')}
    if uv is not None:att['TEXCOORD_0']=add_array(g,b,uv,'VEC2')
    p={'attributes':att,'indices':add_array(g,b,np.asarray(f).reshape(-1,1),'SCALAR',5125),'material':material}
    mi=len(g['meshes']);g['meshes'].append({'name':name,'primitives':[p]})
    ni=len(g['nodes']);g['nodes'].append({'name':name,'mesh':mi});g['nodes'][0]['children'].append(ni)

def smooth_normals(v,f):
    # Weld only coincident vertices for averaging; faces and all surface points are unchanged.
    _,inv=np.unique(np.round(v,7),axis=0,return_inverse=True)
    faces=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    n=np.zeros((inv.max()+1,3))
    for corner in range(3):np.add.at(n,inv[f[:,corner]],faces)
    n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-15)
    return n[inv]

def lathe(profile,center,segments=128,ell=(1,1)):
    z,r=np.asarray(profile).T
    dense=np.unique(np.r_[z,np.linspace(z.min(),z.max(),160)])
    rad=PchipInterpolator(z,r)(dense)
    ang=np.arange(segments)*2*np.pi/segments
    v=np.stack([np.broadcast_to(center[0]+rad[:,None]*np.cos(ang)*ell[0],(len(dense),segments)),
                np.broadcast_to(center[1]+rad[:,None]*np.sin(ang)*ell[1],(len(dense),segments)),
                np.broadcast_to(center[2]+dense[:,None],(len(dense),segments))],axis=-1).reshape(-1,3)
    f=[]
    for j in range(len(dense)-1):
        for k in range(segments):
            a=j*segments+k;d=j*segments+(k+1)%segments;c=d+segments;b=a+segments
            f.extend([[a,d,c],[a,c,b]])
    # Closed caps with opposite outward winding.
    v=np.vstack([v,[center[0],center[1],center[2]+dense[0]],[center[0],center[1],center[2]+dense[-1]]])
    for k in range(segments):
        f.append([len(v)-2,(k+1)%segments,k]);last=(len(dense)-1)*segments
        f.append([len(v)-1,last+k,last+(k+1)%segments])
    return v,np.asarray(f)

def save(folder,g,b,oldfit,note):
    dest=ROOT/'objects'/folder;dest.mkdir(parents=True,exist_ok=True)
    # Remove superseded binary geometry, while preserving every referenced texture.
    used=set()
    for mm in g['meshes']:
        for p in mm['primitives']:used.update(p['attributes'].values());used.add(p['indices'])
    amap={a:i for i,a in enumerate(sorted(used))};aa=[copy.deepcopy(g['accessors'][a]) for a in sorted(used)]
    views={a['bufferView'] for a in aa}|{im['bufferView'] for im in g.get('images',[])}
    vb=[];bb=bytearray();vm={}
    for vi in sorted(views):
        view=copy.deepcopy(g['bufferViews'][vi]);offset=view.get('byteOffset',0);bb.extend(b'\0'*((-len(bb))%4))
        view['byteOffset']=len(bb);bb.extend(b[offset:offset+view['byteLength']]);vm[vi]=len(vb);vb.append(view)
    for a in aa:a['bufferView']=vm[a['bufferView']]
    for im in g.get('images',[]):im['bufferView']=vm[im['bufferView']]
    for mm in g['meshes']:
        for p in mm['primitives']:
            p['attributes']={key:amap[val] for key,val in p['attributes'].items()};p['indices']=amap[p['indices']]
    g['accessors']=aa;g['bufferViews']=vb;b=bb
    gt.write(dest/'world_pbr.glb',g,b)
    gg,bb=gt.read(dest/'world_pbr.glb');pp=gt.parts(gg,bb,True);allparts=list(pp);v=np.concatenate([p[5] for p in allparts])
    fit=copy.deepcopy(oldfit);fit.update(glb=str(dest/'world_pbr.glb'),folder=folder,
        bounds_raw=[v.min(0).tolist(),v.max(0).tolist()],height=float(np.ptp(v[:,2])),notes=note)
    fit.update(geometry_changed=True,materials_changed=True,revision='kitchen_workspace_v7_20261011',realism_notes=note)
    fit['provenance']={'retained_source_credit':fit.get('product'),'geometry_and_finish':note,
        'new_textures':'Original procedural maps referenced to existing dataset photographs; no photographic illumination baked into metal.'}
    from shapely.geometry import MultiPoint,Polygon,box
    hull=MultiPoint(v[:,:2]).convex_hull
    if fit.get('delete_polygon'):hull=hull.union(Polygon(fit['delete_polygon'])).convex_hull
    if fit.get('delete_aabb'):
        lo,hi=fit['delete_aabb'];hull=hull.union(box(lo[0],lo[1],hi[0],hi[1])).convex_hull
        fit['delete_aabb']=[np.minimum(lo,v.min(0)).tolist(),np.maximum(hi,v.max(0)).tolist()]
    fit['delete_polygon']=[list(x) for x in hull.exterior.coords[:-1]]
    fit['base'][2]=float(v[:,2].min());fit.pop('matrix',None)
    triangles=trimesh.util.concatenate([trimesh.Trimesh(p[5],p[6],process=False) for p in allparts]);triangles.export(dest/'world.ply')
    fit['world_mesh']=str(dest/'world.ply');(dest/'fit.json').write_text(json.dumps(fit,indent=2))
    return fit

def tea():
    folder=OLD/'objects/tea_tray_v5';fit=json.loads((folder/'fit.json').read_text());g,b=gt.read(folder/'world_pbr.glb');parts=list(gt.parts(g,b,True));b=bytearray(b);reset_raw(g,parts)
    # Height mapped UVs explicitly encode the unavailable procedural shader.
    w=h=1024;u,z=np.meshgrid(np.linspace(0,1,w),np.linspace(0,1,h));rng=np.random.default_rng(47)
    grain=rng.normal(0,1,(h,w));waves=(np.sin(29*u*2*np.pi)+.45*np.sin(71*u*2*np.pi+1))
    edge=.40+.023*waves+.009*grain
    t=np.clip((z-edge)/.075+.5,0,1);t=t*t*(3-2*t)
    brown=np.array([43,33,25]);turq=np.array([64,157,158]);rgb=brown[None,None,:]*(1-t[:,:,None])+turq[None,None,:]*t[:,:,None]
    band=np.exp(-((z-edge)/.035)**2);rgb+=band[:,:,None]*np.array([55,30,2])+grain[:,:,None]*1.2
    colour=add_texture(g,b,rgb,'reactive_glaze_basecolor');mr=np.zeros((h,w,3));mr[:,:,0]=255;mr[:,:,1]=np.clip(66+6*grain+25*band,45,115)
    rough=add_texture(g,b,mr,'reactive_glaze_roughness')
    glaze=g['materials'][1];glaze['pbrMetallicRoughness'].update(baseColorFactor=[1,1,1,1],baseColorTexture={'index':colour},metallicFactor=0,roughnessFactor=1,metallicRoughnessTexture={'index':rough})
    glaze['extensions']={'KHR_materials_clearcoat':{'clearcoatFactor':.8,'clearcoatRoughnessFactor':.16}}
    g['extensionsUsed']=sorted(set(g.get('extensionsUsed',[])+['KHR_materials_clearcoat']))
    g['materials'][0]['pbrMetallicRoughness']['roughnessFactor']=.22
    for i,n,p,m,anc,v,f in parts:
        name=n['name'].replace('_v5','_v7');v=v.copy();v[:,2]+=.0039817070961
        uv=None
        if p['material']==1:
            if 'Sugar_jar' in name:
                v,f=lathe([(0,.032),(.004,.038),(.015,.046),(.035,.052),(.055,.046),(.065,.038),(.070,.039),(.080,.032),(.092,.018),(.096,.008),(.100,.012),(.104,.011),(.108,.002)],(1.635,-3.86,.941981707))
                center=np.array([1.635,-3.86,.941981707]);v=center+(v-center)*np.array([.85,.85,.82])
                zspan=.132
            else:zspan=.148
            uv=np.c_[(v[:,0]-1.50)/.30,np.clip((v[:,2]-.941981707)/zspan,0,1)]
        normals=smooth_normals(v,f) if p['material']==1 else gt.accessor(g,b,p['attributes']['NORMAL'])@m[:3,:3].T
        mesh(g,b,name,v,f,p['material'],uv,normals)
    return save('tea_tray_v7',g,b,fit,'Exported turquoise/brown photo-matched glaze base-colour and roughness textures; smooth sugar jar. Licensed teapot retained. Tray bottom raised 3.98 mm to counter surface. Exact reactive-glaze pattern is approximate.')

def frother():
    folder=OLD/'objects/frother_v5';fit=json.loads((folder/'fit.json').read_text());g,b=gt.read(folder/'world_pbr.glb');parts=list(gt.parts(g,b,True));b=bytearray(b);reset_raw(g,parts)
    g['materials'][0]['pbrMetallicRoughness'].update(baseColorFactor=[.006,.0055,.005,1],roughnessFactor=.29)
    g['materials'][1]['pbrMetallicRoughness'].update(baseColorFactor=[.70,.71,.72,1],metallicFactor=1,roughnessFactor=.10)
    # The inherited bump map has no meaningful UV mapping on the new acrylic lid.
    g['materials'][2].pop('normalTexture',None)
    g['materials'][2]['pbrMetallicRoughness'].update(baseColorFactor=[.8,.85,.85,1],roughnessFactor=.1)
    g['materials'][2]['extensions']['KHR_materials_specular']={'specularFactor':1}
    g['materials'][2]['extensions']['KHR_materials_transmission']={'transmissionFactor':.98}
    for i,n,p,m,anc,v,f in parts:
        if n['name'].endswith('_Cap'):continue
        uv=gt.accessor(g,b,p['attributes']['TEXCOORD_0']).copy() if 'TEXCOORD_0' in p['attributes'] else None
        norm=gt.accessor(g,b,p['attributes']['NORMAL'])@np.linalg.inv(m[:3,:3])
        norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-15)
        if p['material']==1:norm=smooth_normals(v,f)
        mesh(g,b,n['name'].replace('_v5','_v7'),v,f,p['material'],uv,norm)
    # Rounded dark gasket surrounds the shallow clear cap, as in the photograph.
    theta=np.arange(128)*2*np.pi/128;phi=np.arange(16)*2*np.pi/16
    t,ph=np.meshgrid(theta,phi,indexing='ij');rad=.045+.0012*np.cos(ph)
    v=np.stack([1.668+rad*np.cos(t),-3.475+rad*np.sin(t),1.1223+.0012*np.sin(ph)],axis=-1).reshape(-1,3)
    f=[]
    for a in range(128):
        for k in range(16):
            p=a*16+k;q=a*16+(k+1)%16;r=((a+1)%128)*16+k;s=((a+1)%128)*16+(k+1)%16
            f.extend([[p,r,q],[r,s,q]])
    mesh(g,b,'Kitchen_frother_v7_Rounded_lid_gasket',v,np.asarray(f),3)
    section=[(.045,1.121),(.045,1.124),(.043,1.124),(.041,1.121),(.039,1.116),(.0001,1.116),(.0001,1.115),(.043,1.115),(.045,1.121)]
    vv=[];ff=[]
    for r,z in section:
        for a in theta:vv.append([1.668+r*np.cos(a),-3.475+r*np.sin(a),z])
    for j in range(len(section)-1):
        for k in range(128):
            a=j*128+k;d=j*128+(k+1)%128;ff.extend([[a,d,a+128],[d,d+128,a+128]])
    mesh(g,b,'Kitchen_frother_v7_Photo_recessed_clear_lid',np.asarray(vv),np.asarray(ff),2)
    v,f=lathe([(0,.0001),(.0001,.036),(.0003,.036),(.0005,.0001)],(1.668,-3.475,1.1135))
    mesh(g,b,'Kitchen_frother_v7_Dark_lid_interior',v,f,3)
    return save('frother_v7',g,b,fit,'Retained licensed ribbed-body mesh. Smoothed chrome collar normals, corrected chrome reflectance; photo-shaped shallow recessed clear lid with a rounded dark gasket and interior. Exact product details remain approximate.')

def coffee():
    folder=OLD/'objects/coffee_machine2_v5';fit=json.loads((folder/'fit.json').read_text());g,b=gt.read(folder/'world_pbr.glb');parts=list(gt.parts(g,b,True));b=bytearray(b);reset_raw(g,parts)
    # Restore the side-panel shader as actual colour/data textures.
    w=h=1024;u,z=np.meshgrid(np.linspace(0,1,w),np.linspace(0,1,h));rng=np.random.default_rng(38)
    rib=.5+.5*np.cos(z*2*np.pi*16);fine=rng.normal(0,1,(h,w));rgb=np.repeat((85+65*rib+fine*1.5)[:,:,None],3,axis=2)
    rgb[:,:,0]*=1.055;rgb[:,:,2]*=.93
    colour=add_texture(g,b,rgb,'coffee_ribbed_metal_basecolor');mr=np.zeros((h,w,3));mr[:,:,0]=255;mr[:,:,1]=90+25*(1-rib)+fine;mr[:,:,2]=244
    rough=add_texture(g,b,mr,'coffee_brushed_metal_data')
    mat=g['materials'][21];mat['pbrMetallicRoughness'].update(baseColorFactor=[1,1,1,1],baseColorTexture={'index':colour},metallicFactor=1,roughnessFactor=1,metallicRoughnessTexture={'index':rough})
    normal=np.zeros((h,w,3));ny=.45*np.sin(z*2*np.pi*16);normal[:,:,0]=127.5;normal[:,:,1]=127.5*(1+ny);normal[:,:,2]=127.5*(1+np.sqrt(1-ny*ny))
    bump=add_texture(g,b,normal,'coffee_ribbed_metal_normal');mat['normalTexture']={'index':bump,'scale':.65}
    # Original export's white water volume protrudes above the black housing. Give
    # the retained reservoir a dark translucent finish rather than a white shell.
    g['materials'][10]['pbrMetallicRoughness'].update(baseColorFactor=[.065,.075,.075,1],roughnessFactor=.17)
    g['materials'][10]['extensions']['KHR_materials_transmission']['transmissionFactor']=.45
    for mat in g['materials']:
        name=mat.get('name','').lower();pbr=mat.get('pbrMetallicRoughness',{})
        if 'plastic_black' in name or 'rough_black' in name:pbr.update(baseColorFactor=[.006,.006,.005,1],roughnessFactor=.24)
        if 'steel' in name or 'aluminum' in name:pbr.update(baseColorFactor=[.62,.64,.65,1],roughnessFactor=.23)
    # The available download is an Inissia-like substitute, with a boxy tank and
    # controls unlike the photograph. Reconstruct the visible rounded housing,
    # cup platform and chrome lever; retain only its licensed dispensing fitting.
    for i,n,p,m,anc,v,f in parts:
        if n['name'].endswith('_Object_3'):
            v=v.copy();v[:,:2]=2*np.array([1.766,-3.224])-v[:,:2];v[:,2]+=.041
            norm=gt.accessor(g,b,p['attributes']['NORMAL'])@np.linalg.inv(m[:3,:3]);norm[:,:2]*=-1
            norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-15)
            uv=gt.accessor(g,b,p['attributes']['TEXCOORD_0']).copy()
            mesh(g,b,'Kitchen_coffee_machine2_v7_Licensed_dispensing_fitting',v,f,p['material'],uv,norm)
    center_y=-3.224;radius=.050;spring=1.106;bottom=.935
    theta=np.linspace(0,np.pi,129)
    profile=np.vstack([[-radius,bottom],[radius,bottom],[radius,spring],np.c_[radius*np.cos(theta[1:]),spring+radius*np.sin(theta[1:])]])
    # Smooth semicylindrical roof and straight lower side walls. Split end caps
    # from the curved shell so a flat end does not distort the roof normals.
    shell=[];tri=[]
    for x in np.linspace(1.705,1.891,25):
        shell.extend([[x,center_y+y,z] for y,z in profile])
    count=len(profile)
    for ring in range(24):
        for k in range(count):
            a=ring*count+k;d=ring*count+(k+1)%count;c=d+count;bb=a+count
            tri.extend([[a,d,bb],[bb,d,c]])
    mesh(g,b,'Kitchen_coffee_machine2_v7_Photo_rounded_housing',np.array(shell),np.array(tri),4)
    for x,reverse in [(1.705,True),(1.891,False)]:
        vv=np.c_[np.full(count,x),center_y+profile[:,0],profile[:,1]]
        # Polygon triangulation uses the existing trimesh/Shapely tooling.
        from shapely.geometry import Polygon
        from shapely.ops import triangulate
        pol=Polygon(profile);vv=[];ff=[]
        for t in triangulate(pol):
            if not pol.covers(t.representative_point()):continue
            coords=np.asarray(t.exterior.coords)[:3];idx=len(vv);vv.extend([[x,center_y+y,z] for y,z in coords]);ff.append([idx,idx+2,idx+1] if reverse else [idx,idx+1,idx+2])
        mesh(g,b,'Kitchen_coffee_machine2_v7_'+('Front_arch' if reverse else 'Rear_arch'),np.asarray(vv),np.asarray(ff),4)
    # Broad side plates carry exported normal/roughness maps, with rounded edges.
    for sign in [-1,1]:
        outline=[];hw=.163/2;hh=.151/2;rr=.004
        for cx,cz,start in [(hw-rr,hh-rr,0),(-hw+rr,hh-rr,np.pi/2),(-hw+rr,-hh+rr,np.pi),(hw-rr,-hh+rr,3*np.pi/2)]:
            for a in np.linspace(start,start+np.pi/2,24):outline.append([cx+rr*np.cos(a),cz+rr*np.sin(a)])
        outline=np.asarray(outline);num=len(outline);vv=[];ff=[];cy=center_y+sign*.0505
        for y,inset in [(cy-.0009,.0005),(cy-.0004,0),(cy+.0004,0),(cy+.0009,.0005)]:
            ring=outline.copy();ring[:,0]*=(hw-inset)/hw;ring[:,1]*=(hh-inset)/hh
            vv.extend([[1.798+x,y,1.0195+z] for x,z in ring])
        for ring in range(3):
            for k in range(num):
                a=ring*num+k;d=ring*num+(k+1)%num;ff.extend([[a,a+num,d],[a+num,d+num,d]])
        vv=np.asarray(vv);uv=np.c_[(vv[:,0]-1.7165)/.163,(vv[:,2]-.944)/.151]
        mesh(g,b,'Kitchen_coffee_machine2_v7_Bevelled_side_edge_'+str(sign),vv,np.asarray(ff),21,uv)
        for offset,y in [(0,cy-.0009),(3*num,cy+.0009)]:
            face=np.vstack([[1.798,y,1.0195],vv[offset:offset+num]])
            f=np.array([[0,k+1,(k+1)%num+1] if offset==0 else [0,(k+1)%num+1,k+1] for k in range(num)])
            uv=np.c_[(face[:,0]-1.7165)/.163,(face[:,2]-.944)/.151]
            normal=np.tile([0,-1 if offset==0 else 1,0],(len(face),1))
            mesh(g,b,'Kitchen_coffee_machine2_v7_Photo_brushed_ribbed_side_'+str(sign)+'_'+str(offset),face,f,21,uv,normal)
    # A smooth oval removable capsule bin and a shallow cup platform. The lowest
    # foot stays on the slab, with 7.5 cm of clearance below the dispensing nozzle.
    v,f=lathe([(0,.030),(.002,.036),(.007,.041),(.075,.043),(.088,.046),(.092,.046)],(1.682,center_y,.935),ell=(.96,1))
    uv=np.c_[(v[:,0]-1.635)/.10,(v[:,2]-.935)/.092]
    mesh(g,b,'Kitchen_coffee_machine2_v7_Photo_capsule_bin',v,f,15,uv)
    v,f=lathe([(0,.043),(.001,.046),(.003,.046),(.005,.044)],(1.682,center_y,1.027),ell=(.96,1))
    mesh(g,b,'Kitchen_coffee_machine2_v7_Photo_cup_platform',v,f,4)
    # Thin smooth chrome lever follows the rounded rear/top silhouette.
    from scipy.interpolate import CubicSpline
    control=np.array([[1.845,center_y-.052,1.079],[1.869,center_y-.052,1.116],[1.870,center_y-.045,1.139],[1.86,center_y-.038,1.148],
                      [1.857,center_y,1.149],[1.86,center_y+.038,1.148],[1.870,center_y+.045,1.139],[1.869,center_y+.052,1.116],[1.845,center_y+.052,1.079]])
    path=CubicSpline(np.arange(len(control)),control,axis=0)(np.linspace(0,len(control)-1,200))
    tangent=np.gradient(path,axis=0);tangent/=np.linalg.norm(tangent,axis=1,keepdims=True)
    reference=np.tile([0,0,1.],(len(path),1));axis=np.cross(tangent,reference);axis/=np.linalg.norm(axis,axis=1,keepdims=True);side=np.cross(tangent,axis)
    vv=[];ff=[]
    for j,pos in enumerate(path):
        for k in range(24):
            a=2*np.pi*k/24;vv.append(pos+.0020*(axis[j]*np.cos(a)+side[j]*np.sin(a)))
    for j in range(len(path)-1):
        for k in range(24):
            a=j*24+k;d=j*24+(k+1)%24;ff.extend([[a,d,a+24],[d,d+24,a+24]])
    mesh(g,b,'Kitchen_coffee_machine2_v7_Photo_chrome_lever',np.asarray(vv),np.asarray(ff),0)
    # Closed top capsule hatch and a narrow loading seam, rather than toy-like
    # green buttons on the front face.
    hatch=trimesh.creation.box([.053,.014,.001]);hatch.vertices+=np.array([1.788,center_y,1.1558])
    mesh(g,b,'Kitchen_coffee_machine2_v7_Top_loading_hatch',hatch.vertices,hatch.faces,22)
    search=json.loads((ROOT/'evidence/model_search.json').read_text());source=next(x for x in search if x['uid']=='5a56ac54f7144de4878958cd45cac3cd')
    fit['product']={'uid':source['uid'],'name':source['name'],'author':source['user']['displayName'],'license':'CC-BY-4.0','url':source['viewerUrl']}
    fit['method']='Photo-shaped smooth housing with retained licensed dispensing fitting and texture-backed PBR finishes'
    fit['placement_delta_yaw_degrees']=180
    return save('coffee_machine2_v7',g,b,fit,'Photo-shaped semicylindrical housing, oval capsule bin/cup platform and smooth chrome lever. Dispensing face oriented toward reference camera. Embedded brushed/ribbed metal maps. Licensed dispensing fitting credited to Cafetera Nespresso Japan by furiadesignerone. Exact model identity, unseen tank and controls remain approximate.')

if __name__=='__main__':
    ROOT.mkdir(parents=True,exist_ok=True)
    results=[tea(),frother(),coffee()]
    (ROOT/'replacements.json').write_text(json.dumps(results,indent=2))
    print('TEXTURE_BACKED_REPAIRS_SAVED',[(x['folder'],x['bounds_raw']) for x in results],flush=True)
