"""Assemble actual photo and mesh-render evidence; no generated or retouched pixels."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json

ROOT=Path(__file__).resolve().parent.parent
catalog=json.loads((ROOT/'evidence/catalog.json').read_text())['items']
assets=ROOT/'images/assets';assets.mkdir(exist_ok=True)
photo_dir=ROOT/'images/real_photos'
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
cell_width,cell_height=660,255
sheet=Image.new('RGB',(cell_width*3,cell_height*((len(catalog)+2)//3)), '#153c2c')
draw=ImageDraw.Draw(sheet)
for index,item in enumerate(catalog):
    photo=Image.open(photo_dir/item['photo']).convert('RGB')
    render=Image.open(ROOT/'images'/('photo_'+item['photo'].replace('.jpg','.png'))).convert('RGB')
    crop=tuple(round(v*1.6) for v in item['crop'])
    real_crop=photo.crop(crop);render_crop=render.crop(crop)
    real_crop.save(assets/(item['id']+'_real.jpg'),quality=95)
    render_crop.save(assets/(item['id']+'_pbr.jpg'),quality=95)
    render.save(assets/(item['id']+'_room.jpg'),quality=94)
    x=(index%3)*cell_width;y=(index//3)*cell_height
    draw.text((x+8,y+6),item['label'],font=font,fill='white')
    room=Image.open(ROOT/'images'/('room_'+item['id']+'.png')).convert('RGB')
    for offset,(image,label) in enumerate([(real_crop,'Real photo'),(render_crop,'Current mesh'),(room,'In room')]):
        image.thumbnail((212,205),Image.Resampling.LANCZOS)
        sheet.paste(image,(x+offset*220+(212-image.width)//2,y+43+(205-image.height)//2))
        draw.text((x+offset*220+5,y+25),label,font=font,fill='#c9e3d5')
sheet.save(ROOT/'images/all_items_review.jpg',quality=95)
print('COMPARISONS_BUILT',len(catalog),flush=True)
