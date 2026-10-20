"""Make five small, recognizable review props as native 3-D assets (metres, Y up)."""
from pathlib import Path
import json
import math
import numpy as np
import trimesh as t
from PIL import Image,ImageDraw

OUT=Path(__file__).resolve().parent/'assets'

def box(size, pos, color):
    m=t.creation.box(size);m.apply_translation(pos);m.visual.vertex_colors=color;return m

def ball(size,pos,color):
    m=t.creation.icosphere(subdivisions=3);m.apply_scale(size);m.apply_translation(pos);m.visual.vertex_colors=color;return m

def rod(a,b,r,color):
    a,b=np.array(a),np.array(b);m=t.creation.cylinder(radius=r,segment=[a,b],sections=12);m.visual.vertex_colors=color;return m

def ring(cx,cz,rx,rz):
    return [rod((cx+rx*math.cos(a),.006,cz+rz*math.sin(a)),(cx+rx*math.cos(b),.006,cz+rz*math.sin(b)),.002,[55,35,30,255])
            for a,b in zip(np.linspace(0,2*math.pi,33)[:-1],np.linspace(0,2*math.pi,33)[1:])]

def main():
    OUT.mkdir(exist_ok=True)
    meshes={}
    calc=[box((.085,.014,.16),(0,.007,0),[28,34,46,255]),box((.067,.002,.035),(0,.015,-.046),[130,166,153,255])]
    for r in range(5):
        for c in range(4):
            calc.append(box((.013,.003,.012),(-.027+c*.018,.016,-.01+r*.025),[235,164,64,255] if c==3 else [209,215,221,255]))
    meshes['calculator']=calc
    glasses=ring(-.031,0,.028,.020)+ring(.031,0,.028,.020)
    glasses += [rod((-.005,.006,0),(.005,.006,0),.002,[55,35,30,255]),rod((-.059,.006,0),(-.060,.008,.115),.002,[55,35,30,255]),rod((.059,.006,0),(.060,.008,.115),.002,[55,35,30,255])]
    meshes['glasses']=glasses
    shoe=[ball((.049,.025,.135),(0,.031,0),[238,237,228,255]),ball((.046,.037,.097),(0,.055,-.016),[35,77,141,255]),ball((.031,.009,.033),(0,.090,.057),[20,23,29,255])]
    for x in (-.032,.032):
        for z in (-.09,-.04,.04,.09):shoe.append(rod((x,.008,z),(x,.022,z),.007,[220,221,215,255]))
    for z in (-.065,-.045,-.025,-.005):
        middle=.055+.037*math.sqrt(max(.05,1-((z+.016)/.097)**2))+.003
        edge=.055+.037*math.sqrt(max(.05,1-((z+.016)/.097)**2-(.022/.046)**2))+.003
        shoe += [rod((-.022,edge,z),(0,middle,z+.003),.002,[240,240,236,255]),rod((0,middle,z+.003),(.022,edge,z+.006),.002,[240,240,236,255])]
    meshes['cleat']=shoe
    book=[box((.18,.018,.235),(0,.012,0),[230,225,202,255]),box((.19,.003,.245),(0,.002,0),[39,91,90,255]),box((.19,.003,.245),(0,.023,0),[39,91,90,255])]
    for r in range(9):
        for c in range(7):
            book.append(box((.012,.0008,.012),(-.055+c*.018,.025,-.065+r*.016),[245,242,220,255] if (r+c)%5 else [33,48,46,255]))
    meshes['crossword_book']=book
    # Folded cardigan: soft knit body, folded sleeves, V-neck and button opening.
    cardigan=[ball((.16,.019,.115),(0,.021,0),[159,73,83,255]),ball((.073,.013,.105),(-.078,.030,0),[159,73,83,255]),ball((.073,.013,.105),(.078,.030,0),[159,73,83,255])]
    sleeve=ball((.125,.010,.031),(0,0,0),[166,80,90,255]);sleeve.apply_transform(t.transformations.rotation_matrix(.32,[0,1,0]));sleeve.apply_translation((-.025,.042,.013));cardigan.append(sleeve)
    cardigan += [rod((-.055,.043,-.093),(0,.047,-.045),.009,[159,73,83,255]),rod((0,.047,-.045),(.055,.043,-.093),.009,[159,73,83,255])]
    texture=Image.new('RGB',(256,256),(146,67,79));draw=ImageDraw.Draw(texture)
    for y in range(0,256,4):
        for x in range(0,256,4):
            draw.line((x,y,x+2,y+2,x+4,y),fill=(160,79,91),width=1)
            draw.point((x,y+3),fill=(128,57,69))
    material=t.visual.material.PBRMaterial(baseColorTexture=texture,roughnessFactor=1.0,doubleSided=True)
    for m in cardigan:
        uv=(m.vertices[:,[0,2]]+np.array([.4,.3]))/np.array([.8,.6]);m.visual=t.visual.TextureVisuals(uv=uv,material=material)
    for z in (-.025,.025,.075):cardigan.append(ball((.0045,.003,.0045),(.008,.047,z),[225,203,185,255]))
    meshes['cardigan']=cardigan
    for name,parts in meshes.items():
        scene=t.Scene()
        for i,m in enumerate(parts):scene.add_geometry(m,node_name=f'{name}_{i}')
        (OUT/f'{name}.glb').write_bytes(scene.export(file_type='glb'))
        (OUT/f'{name}.object_config.json').write_text(json.dumps(dict(render_asset=f'{name}.glb',collision_asset=f'{name}.glb',COM=[0,0,0],requires_lighting=False,margin=0.0),indent=2))
    print('Built',', '.join(meshes))

if __name__=='__main__':main()
