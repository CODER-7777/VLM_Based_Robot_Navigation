"""Bounded tray and backsplash revision. Writes only in the personal workspace."""
from pathlib import Path
import copy, json, sys
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
import trimesh

OLD = Path('/data/robotics/toshith/vivekananda/kitchen_appliance_refinement_20261011')
ROOT = Path('/data/robotics/toshith/vivekananda/kitchen_tray_background_repair')
sys.path.insert(0, str(OLD/'scripts'))
import glb_tools as gt
sys.path.insert(0, str(OLD))
import build_finishes as bf
bf.ROOT = ROOT
REV = 'kitchen_workspace_v8_tray_20261011'

def outline(width, length, radius, segments=32):
    points=[]
    for cx,cy,start in [(width/2-radius,length/2-radius,0),
                        (-width/2+radius,length/2-radius,np.pi/2),
                        (-width/2+radius,-length/2+radius,np.pi),
                        (width/2-radius,-length/2+radius,3*np.pi/2)]:
        angle=start+np.arange(segments)*np.pi/(2*segments)
        points.extend(np.c_[cx+radius*np.cos(angle),cy+radius*np.sin(angle)])
    return np.array(points)

def build_tray():
    oldfit=json.loads((OLD/'objects/tea_tray_v7/fit.json').read_text())
    g,source_blob=gt.read(Path(oldfit['glb']));parts=list(gt.parts(g,source_blob,True));b=bytearray(source_blob)
    bf.reset_raw(g,parts)
    g['materials'][0]['pbrMetallicRoughness'].update(baseColorFactor=[.92,.915,.895,1],metallicFactor=0,roughnessFactor=.20)
    g['materials'][0]['extensions']={'KHR_materials_clearcoat':{'clearcoatFactor':.7,'clearcoatRoughnessFactor':.13}}
    g['extensionsUsed']=sorted(set(g.get('extensionsUsed',[])+['KHR_materials_clearcoat']))
    for _,n,p,m,anc,v,f in parts:
        if 'Ceramic_Tray' in n['name']:continue
        uv=gt.accessor(g,source_blob,p['attributes']['TEXCOORD_0']).copy() if 'TEXCOORD_0' in p['attributes'] else None
        norm=gt.accessor(g,source_blob,p['attributes']['NORMAL']).copy()@np.linalg.inv(m[:3,:3])
        norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-12)
        bf.mesh(g,b,n['name'].replace('_v7','_v8'),v,f,p['material'],uv,norm)
    # A closed porcelain basin, with a flat supporting base and a curved lip.
    rings=[(.190,.372,.037,.935),(.199,.381,.041,.935),
           (.213,.397,.048,.939),(.225,.409,.053,.952),
           (.227,.411,.054,.957),(.226,.410,.054,.959),
           (.220,.404,.052,.960),(.213,.397,.049,.9585),
           (.209,.393,.047,.955),(.199,.383,.044,.9455),
           (.191,.375,.040,.942),(.184,.368,.038,.9419817328)]
    vertices=[]
    for w,l,r,z in rings:
        xy=outline(w,l,r)+np.array([1.6695,-3.935])
        vertices.extend(np.c_[xy,np.full(len(xy),z)])
    vertices=np.array(vertices);n=128;faces=[]
    for j in range(len(rings)-1):
        for k in range(n):
            a=j*n+k;d=j*n+(k+1)%n
            faces.extend([[a,d,a+n],[d,d+n,a+n]])
    vertices=np.vstack([vertices,[1.6695,-3.935,.935],[1.6695,-3.935,.9419817328]])
    for k in range(n):
        faces.extend([[len(vertices)-2,(k+1)%n,k],
                      [len(vertices)-1,(len(rings)-1)*n+k,(len(rings)-1)*n+(k+1)%n]])
    faces=np.array(faces)
    tray=trimesh.Trimesh(vertices,faces,process=False)
    # Original ring winding is outward along the shell, with underside/top caps.
    if tray.volume<0:faces=faces[:,::-1];tray=trimesh.Trimesh(vertices,faces,process=False)
    assert tray.is_watertight and tray.is_winding_consistent
    bf.mesh(g,b,'Kitchen_tea_tray_v8_Closed_rounded_porcelain_tray',vertices,faces,0,
            normals=bf.smooth_normals(vertices,faces))
    note='Closed smooth porcelain tray with a curved rounded-rectangle rim, flat base on z=0.935 and basin supporting the retained glazed tea set. Tray is within the actual counter; local scan ghosts are removed in the room. Teapot silhouette and decorative glaze remain approximate.'
    fit=bf.save('tea_tray_v8',g,b,oldfit,note)
    fit.update(name='tea_tray_v8',revision=REV,method='Smooth watertight tray reconstruction; licensed glazed teapot retained',tray_dimensions_m=[.227,.411,.025],tray_watertight=True,tray_winding_consistent=True,source_fit=str(OLD/'objects/tea_tray_v7/fit.json'))
    (ROOT/'objects/tea_tray_v8/fit.json').write_text(json.dumps(fit,indent=2))
    (ROOT/'evidence/tray_geometry.json').write_text(json.dumps({'watertight':True,'consistent_winding':True,'base_z':float(vertices[:,2].min()),'basin_z':.9419817328,'rim_z':.960,'dimensions_m':np.ptp(vertices,axis=0).tolist(),'vertices':len(vertices),'triangles':len(faces),'counter_rear_x':1.55,'tray_rear_x':float(vertices[:,0].min()),'retained_teapot_sugar_geometry':True},indent=2))

def build_background():
    g={'asset':{'version':'2.0'},'nodes':[],'meshes':[],'materials':[],'scenes':[{'nodes':[]}],'scene':0};b=bytearray();bf.reset_raw(g,[])
    cat=json.loads((OLD/'comparison/items/catalog.json').read_text())
    camera=next(x for x in cat['items'] if x['id']=='tea_tray')['camera']
    photo_path='/data/robotics/toshith/rxr_author/refined/toaster_home_tour/comparison/items/d70e05c20c15468eb93117d496285f82_i2_0.jpg'
    photo=Image.open(photo_path).convert('RGB')
    arr=np.array(photo);K=np.array(camera['K']);w2c=np.linalg.inv(camera['c2w_raw_gl'])
    # Sample one unobstructed decorative tile motif left of the photographed tea set.
    sy0,sy1=-4.435,-4.241;sz0,sz1=.935,1.044
    yy,zz=np.meshgrid(np.linspace(sy0,sy1,1024),np.linspace(sz1,sz0,512))
    points=np.stack([np.full_like(yy,1.547),yy,zz,np.ones_like(yy)],axis=-1)
    pc=points@w2c.T;pc[:,:,1:3]*=-1;xy=pc[:,:,:3]@K.T;xy=xy[:,:,:2]/xy[:,:,2,None]
    xy[:,:,0]*=photo.width/camera['width'];xy[:,:,1]*=photo.height/camera['height']
    assert xy.min()>=0 and xy[:,:,0].max()<photo.width and xy[:,:,1].max()<photo.height
    rgb=np.stack([map_coordinates(arr[:,:,k].astype(float),[xy[:,:,1],xy[:,:,0]],order=1,mode='nearest') for k in range(3)],axis=-1)
    # Small seam blend at the motif endpoints; the central photographic detail is retained.
    for k in range(12):
        mean=(rgb[:,k]+rgb[:,-1-k])/2;t=(12-k)/12
        rgb[:,k]=rgb[:,k]*(1-t)+mean*t;rgb[:,-1-k]=rgb[:,-1-k]*(1-t)+mean*t
    tex=bf.add_texture(g,b,rgb,'rectified_original_tile_motif')
    g['samplers'][g['textures'][tex]['sampler']]['wrapS']=10497
    g['materials']=[{'name':'Original_photo_tile_strip_unlit','pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'baseColorTexture':{'index':tex},'metallicFactor':0,'roughnessFactor':1},'extensions':{'KHR_materials_unlit':{}},'doubleSided':False},
                    {'name':'Tile_panel_edges','pbrMetallicRoughness':{'baseColorFactor':[.58,.47,.30,1],'metallicFactor':0,'roughnessFactor':1},'extensions':{'KHR_materials_unlit':{}}}]
    g['extensionsUsed']=['KHR_materials_unlit']
    x0,x1=1.539,1.549;y0,y1=-4.25,-3.53;z0,z1=.935,1.044
    v=np.array([[x1,y0,z0],[x1,y1,z0],[x1,y1,z1],[x1,y0,z1]])
    f=np.array([[0,1,2],[0,2,3]]);uv=np.array([[0,1],[(y1-y0)/(sy1-sy0),1],[(y1-y0)/(sy1-sy0),0],[0,0]])
    bf.mesh(g,b,'Kitchen_wall_tea_background_v8_Photo_tile_face',v,f,0,uv)
    shell=trimesh.creation.box(extents=[x1-x0,y1-y0,z1-z0]);shell.apply_translation([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2])
    # Omit the front face already represented with its photographic UVs.
    keep=~np.all(np.abs(shell.vertices[shell.faces][:,:,0]-x1)<1e-8,axis=1)
    bf.mesh(g,b,'Kitchen_wall_tea_background_v8_Closed_back_and_edges',shell.vertices,shell.faces[keep],1)
    dest=ROOT/'objects/wall_tea_background_v8';dest.mkdir(parents=True,exist_ok=True)
    gt.write(dest/'world_pbr.glb',g,b)
    fit={'name':'wall_tea_background_v8','glb':str(dest/'world_pbr.glb'),'base':[(x0+x1)/2,(y0+y1)/2,z0],'height':z1-z0,'bounds_raw':[[x0,y0,z0],[x1,y1,z1]],'revision':REV,'notes':'Local missing backsplash band reconstructed below the raised bar. One unobstructed motif from the existing calibrated dataset photograph is rectified and repeated; lighting is already in that photographic texture. Hidden pattern continuity and placement are approximate.','method':'Closed planar local backsplash repair with rectified dataset tile texture','product':None,'source_photo':photo_path,'sample_world_y':[sy0,sy1],'geometry_changed':True,'materials_changed':True}
    shell.export(dest/'world.ply');fit['world_mesh']=str(dest/'world.ply');(dest/'fit.json').write_text(json.dumps(fit,indent=2))
    (ROOT/'evidence/background_patch.json').write_text(json.dumps(fit,indent=2))

def clip_plane(poly, axis, value, greater):
    if len(poly)<3:return []
    output=[]
    for i,a in enumerate(poly):
        c=poly[(i+1)%len(poly)];da=(a[axis]-value)*(1 if greater else -1);dc=(c[axis]-value)*(1 if greater else -1)
        ina=da>=-1e-10;inc=dc>=-1e-10
        if ina:output.append(a)
        if ina!=inc:output.append(a+(c-a)*(da/(da-dc)))
    return output

def clean_scan():
    g,blob=gt.read(OLD/'home_pbr_products.glb');b=bytearray(blob)
    lower=np.array([1.50,-4.25,.932]);upper=np.array([1.80,-3.50,1.0439]);changes=[]
    for i,node,primitive,m,anc,v,f in list(gt.parts(g,blob)):
        if any(x.startswith('Kitchen_') or x.startswith('WallRepair_') for x in [node.get('name','')]+anc):continue
        tri=v[f];hit=np.all(tri.max(1)>lower,axis=1)&np.all(tri.min(1)<upper,axis=1)
        if not hit.any():continue
        attributes=primitive['attributes'];keys=[x for x in attributes if x!='POSITION'];arrays=[v]+[gt.accessor(g,blob,attributes[k]) for k in keys]
        # Interpolate existing UVs and normals at exact clipping intersections.
        full=np.concatenate(arrays,axis=1);newv=[];newf=[];removed=0
        def add_polygon(poly):
            if len(poly)<3:return
            start=len(newv);newv.extend(poly)
            for k in range(1,len(poly)-1):
                positions=np.array([poly[0][:3],poly[k][:3],poly[k+1][:3]])
                if np.linalg.norm(np.cross(positions[1]-positions[0],positions[2]-positions[0]))>1e-12:newf.append([start,start+k,start+k+1])
        for index,face in enumerate(f):
            if not hit[index]:add_polygon(list(full[face]));continue
            poly=list(full[face]);pieces=[]
            for axis in range(3):
                outside=clip_plane(poly,axis,lower[axis],False);pieces.append(outside);poly=clip_plane(poly,axis,lower[axis],True)
                outside=clip_plane(poly,axis,upper[axis],True);pieces.append(outside);poly=clip_plane(poly,axis,upper[axis],False)
            removed+=len(poly)>=3
            for piece in pieces:add_polygon(piece)
        if not removed:continue
        if not newf:
            oldmesh=g['meshes'][node['mesh']]
            remaining=[p for p in oldmesh['primitives'] if p is not primitive]
            if not remaining:node.pop('mesh')
            else:
                node['mesh']=len(g['meshes']);g['meshes'].append(dict(oldmesh,primitives=copy.deepcopy(remaining)))
            changes.append({'node':node.get('name'),'node_index':i,'triangles_intersecting_region':int(hit.sum()),'triangles_with_inside_parts_removed':removed,'old_triangles':len(f),'new_triangles':0})
            continue
        # Copy the mesh/primitive before mutation so any shared instances remain intact.
        oldmesh=g['meshes'][node['mesh']];newmesh=copy.deepcopy(oldmesh)
        pi=next(k for k,p in enumerate(oldmesh['primitives']) if p is primitive)
        node['mesh']=len(g['meshes']);g['meshes'].append(newmesh);primitive=newmesh['primitives'][pi]
        newv=np.array(newv);pos=(newv[:,:3]-m[:3,3])@np.linalg.inv(m[:3,:3]).T
        primitive['attributes']['POSITION']=bf.add_array(g,b,pos,'VEC3')
        start=3
        for key,array in zip(keys,arrays[1:]):
            data=newv[:,start:start+array.shape[1]];start+=array.shape[1]
            if key=='NORMAL':data/=np.maximum(np.linalg.norm(data,axis=1,keepdims=True),1e-12)
            primitive['attributes'][key]=bf.add_array(g,b,data,'VEC'+str(data.shape[1]))
        primitive['indices']=bf.add_array(g,b,np.array(newf).reshape(-1,1),'SCALAR',5125)
        changes.append({'node':node.get('name'),'node_index':i,'triangles_intersecting_region':int(hit.sum()),'triangles_with_inside_parts_removed':removed,'old_triangles':len(f),'new_triangles':len(newf)})
    gt.write(ROOT/'cleaned_source.glb',g,b)
    report={'source':str(OLD/'home_pbr_products.glb'),'source_sha256':gt.sha(OLD/'home_pbr_products.glb'),'deletion_box_raw':[lower.tolist(),upper.tolist()],'changes':changes,'method':'Exact half-space clipping of original scan triangles, retaining and interpolating outside geometry and UVs. All Kitchen_ and WallRepair_ repair nodes are excluded.','shared_files_modified':False}
    assert changes
    (ROOT/'evidence/scan_cleanup.json').write_text(json.dumps(report,indent=2))
    print('BOUNDED_SCAN_CLEANUP',changes,flush=True)

if __name__=='__main__':
    for d in ['objects','textures','evidence']:(ROOT/d).mkdir(exist_ok=True)
    build_tray();build_background();clean_scan()
    print('TRAY_AND_BACKGROUND_BUILT',flush=True)
