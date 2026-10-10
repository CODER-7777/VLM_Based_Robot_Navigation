from pathlib import Path
import sys,json,numpy as np,trimesh,cv2
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'toaster_wall_repair';C=np.array([[1,0,0],[0,0,1],[0,-1,0]],float)
photo=np.asarray(Image.open('/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ/undistorted_color_images/58348305b0f84dd8b161aaf2d5b945ef_i2_4.jpg').convert('RGB'))
# A clean patch of the photographed stone tile, excluding appliances, outlet and grout.
tile=cv2.resize(photo[15:85,220:300],(512,512),interpolation=cv2.INTER_CUBIC)
# Rectify the real decorative diamond; preserve its photographed paint and stone detail.
src=np.float32([[105,40],[177,104],[122,183],[51,117]]);dst=np.float32([[256,78],[434,256],[256,434],[78,256]])
H=cv2.getPerspectiveTransform(src,dst);decor=cv2.warpPerspective(photo,H,(512,512));mask=np.zeros((512,512),np.uint8);cv2.fillConvexPoly(mask,dst.astype(int),255);alpha=cv2.GaussianBlur(mask,(15,15),3)[:,:,None]/255;flower=np.clip(decor*alpha+tile*(1-alpha),0,255).astype(np.uint8)
Image.fromarray(tile).save(W/'clean_tile_sample.png');Image.fromarray(flower).save(W/'decorative_tile_sample.png')
patches=[('tiled_return',[4.405,-5.44,.929],[4.405,-4.80,1.435],(1,2),[1,0,0]),('backsplash',[4.405,-5.44,.929],[4.565,-5.44,1.435],(0,2),[0,1,0]),('return_end',[4.375,-4.80,.929],[4.405,-4.80,1.435],(0,2),[0,1,0])]
scene=trimesh.Scene();raw=[];report=[]
for name,lv,hv,axes,norm in patches:
 lo=np.array(lv);hi=np.array(hv);a,b=axes;ww=max(64,round((hi[a]-lo[a])*1600));hh=round((hi[b]-lo[b])*1600);u,v=np.meshgrid((np.arange(ww)+.5)/ww,(np.arange(hh)+.5)/hh);s=lo[a]+u*(hi[a]-lo[a]);z=hi[b]-v*(hi[b]-lo[b]);pitch=.20;origin=-5.44 if name=='tiled_return' else 4.405
 tx=((s-origin)/pitch)%1;tz=((z-.929)/pitch)%1
 tex=cv2.remap(tile,(tx*511).astype(np.float32),(tz*511).astype(np.float32),cv2.INTER_LINEAR)
 grout=(np.minimum(tx,1-tx)<.004)|(np.minimum(tz,1-tz)<.004);tex[grout]=[163,151,123]
 if name!='return_end':
  center_s=-4.94 if name=='tiled_return' else 4.485;center_z=1.229 if name=='tiled_return' else 1.329
  fx=(s-center_s)/pitch+.5;fz=.5-(z-center_z)/pitch;inside=(fx>=0)&(fx<=1)&(fz>=0)&(fz<=1)
  pat=cv2.remap(flower,(fx*511).astype(np.float32),(fz*511).astype(np.float32),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE);tex[inside]=pat[inside]
 if name=='tiled_return':tex=np.clip(tex.astype(float)*np.array([1.25,1.34,1.43]),0,255).astype(np.uint8)
 Image.fromarray(tex).save(W/(name+'.png'))
 corners=np.tile(lo,(4,1));corners[1,a]=hi[a];corners[2,[a,b]]=hi[[a,b]];corners[3,b]=hi[b];m=trimesh.Trimesh(corners,[[0,1,2],[0,2,3]],process=False)
 if m.face_normals[0]@np.array(norm)<0:m.faces=m.faces[:,::-1]
 raw.append(m.copy());g=m.copy();g.vertices=np.asarray(g.vertices)@C.T;g.visual=trimesh.visual.TextureVisuals(uv=[[0,0],[1,0],[1,1],[0,1]],material=trimesh.visual.material.PBRMaterial(name=name,baseColorTexture=Image.fromarray(tex),metallicFactor=0,roughnessFactor=1,doubleSided=True));scene.add_geometry(g,geom_name=name)
 report.append({'surface':name,'lo':lv,'hi':hv,'texture':'Reconstructed from clean photographed tile plus rectified real decorative motif; grout/pattern placement approximate.'})
# Bridge the missing wooden cabinet join behind the narrow tiled edge.
verts=np.array([[4.375,-4.80,.85],[4.29,-4.755,.85],[4.29,-4.755,1.435],[4.375,-4.80,1.435]])
m=trimesh.Trimesh(verts,[[0,1,2],[0,2,3]],process=False);raw.append(m.copy());g=m.copy();g.vertices=np.asarray(g.vertices)@C.T
wood=Image.fromarray(photo[150:500,1020:1080]);wood.save(W/'cabinet_join.png')
g.visual=trimesh.visual.TextureVisuals(uv=[[0,0],[1,0],[1,1],[0,1]],material=trimesh.visual.material.PBRMaterial(name='cabinet_join',baseColorTexture=wood,metallicFactor=0,roughnessFactor=1,doubleSided=True));scene.add_geometry(g,geom_name='cabinet_join')
report.append({'surface':'cabinet_join','vertices':verts.tolist(),'texture':'Clean wooden frame strip from the reference photograph; local join reconstructed.'})
scene.export(W/'wall_patch.glb');trimesh.util.concatenate(raw).export(W/'wall_patch.ply')
spec={'surfaces':report,'delete_boxes':[[[4.25,-5.51,.931],[4.455,-4.795,1.435]],[[4.405,-5.53,.931],[4.565,-5.35,1.435]]],'reference_toaster':'Black & Decker 2-Slice Toaster, resembling T2030 (user identification); installed Cuisinart substitute unchanged.','texture_method':'Clean real stone tile sample and photo-rectified decorative diamond; reconstructed grout and motif positions are approximate. Limited backsplash width preserves the existing outlet.'}
json.dump(spec,open(W/'patch_spec.json','w'),indent=2);print('PATCH_READY',flush=True)
