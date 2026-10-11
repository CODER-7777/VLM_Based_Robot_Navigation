"""Extend the repair with preserved product geometry and smoothly evaluated parts."""
from pathlib import Path
exec((Path(__file__).with_name('build_replacements.py')).read_text().split('source_rows=')[0])
bpy.context.preferences.filepaths.save_version=0
reports=json.loads((OUT/'replacement_inventory.json').read_text())
reports=[r for r in reports if r['id'] not in ['knife_block','knife_block_round','range_kettle','grinder','phone']]
extra={r['uid']:r for r in json.loads((ROOT/'evidence/additional_downloads.json').read_text())+json.loads((ROOT/'evidence/additional_objaverse_sources.json').read_text())}
def product(uid):return {k:extra[uid][k] for k in ['uid','name','author','license','url']}
def old(slug):
 reset();bpy.ops.import_scene.gltf(filepath=str(ROOT/'current'/(slug+'_old.glb')));obs=objects();clear_other(obs)
 base=json.loads((ROOT/'current'/(slug+'_fit.json')).read_text())['base'];apply(obs,Matrix.Translation(-Vector(base)));return obs,base

def height_only(obs,h):
 v=points(obs);scale=h/(v[:,2].max()-v[:,2].min());apply(obs,Matrix.Scale(scale,4)@Matrix.Translation(Vector((0,0,-v[:,2].min()))))

def evaluated(obs):
 dg=bpy.context.evaluated_depsgraph_get()
 for o in obs:
  mesh=bpy.data.meshes.new_from_object(o.evaluated_get(dg),depsgraph=dg);o.modifiers.clear();o.data=mesh

def bevel(o,width=.0006):
 select([o]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 m=o.modifiers.new('Small_real_edge_radius','BEVEL');m.width=width;m.segments=3;m.limit_method='ANGLE';m.angle_limit=math.radians(45)
 bpy.ops.object.modifier_apply(modifier=m.name)
 m=o.modifiers.new('Preserved_panel_normals','WEIGHTED_NORMAL');m.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=m.name)

def native_bake(obs,m,name):
 b=bsdf(m)
 if b.inputs['Base Color'].links:bake_colour(obs,m,b.inputs['Base Color'].links[0].from_socket,name,1024)
 # Preserve the exported material properties, without baking illumination.
 b.inputs['Roughness'].default_value=.35

# A downloaded real knife set, retaining the artist's subdivision and joinery.
uid='967b767b-cd43-44f8-94c4-e3af008da71b';reset();bpy.ops.wm.open_mainfile(filepath=str(ROOT/'sources'/(uid+'.blend')),use_scripts=False)
keep=['RubberFeet','Holder','Grindstone']+['Knife_'+str(i) for i in range(1,6)]+['Blade_'+str(i) for i in range(1,6)]+['Cube.002','Cube.005','Cube.008','Cube.010','Cube.012']
obs=[o for o in objects() if o.name in keep];clear_other(obs)
for o in obs:
 for mod in o.modifiers:
  if mod.type=='SUBSURF':mod.levels=max(mod.levels,2);mod.render_levels=mod.levels
  # Existing normal-smoothing geometry nodes stay intact until evaluated.
 evaluated([o])
normalise(obs,.301,anchor='floor');smooth(obs)
wood=bpy.data.materials.get('Wood_Holder')
wood_obs=[o for o in obs if wood in list(o.data.materials)];native_bake(wood_obs,wood,'Knife_holder_native_wood')
# Store the licensed wood image so other photo-built wood parts can use it.
wood_image=next(n.image for n in wood.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.name=='Knife_holder_native_wood')
wood_image.filepath_raw=str(OUT/'licensed_wood.png');wood_image.save()
for o in obs:
 for m in o.data.materials:
  if m.name=='Knife_Wood':colour(m,(23,23,22),rough=.27)
  elif m.name=='Blade_Steel':colour(m,(185,186,188),metal=1,rough=.2)
  elif m.name=='Black Plastic':colour(m,(22,22,22),rough=.4)
# Native sharpening stone is a visible front insert, unlike the photo's scissors.
export_fit('knife_block','knife_block_v5',obs,[6.983,-4.29,.929],.301,product(uid),'Downloaded detailed knife holder and five knives, with rounded black handles, steel rivets, baked wood grain and the native sharpening stone. The holder profile and missing scissors differ from the photo.',yaw=-90)

# Stovetop kettle: restore the licensed high-resolution model's three PBR parts.
uid='631ac0b616974530a481b3390fd72b82';obs=import_clean(uid)
body=[o for o in obs if any('Color' in m.name for m in o.data.materials)];subdivide(body,1);normalise(obs,.24)
for o in obs:
 for m in o.data.materials:
  if 'Color' in m.name:colour(m,(188,190,192),metal=1,rough=.105)
  elif 'Steel' in m.name:colour(m,(200,202,204),metal=1,rough=.12)
  else:colour(m,(22,22,23),rough=.29)
export_fit('range_kettle','range_kettle_v5',obs,[6.882,-3.217,.991],.24,product(uid),'Original licensed kettle restored as separate steel and plastic parts, with a subdivided curved body and true reflective PBR metal. The body profile remains a substitute.',yaw=122)

# Oval knife holder: curved, rounded metal handles rather than polygonal rods.
obs,base=old('knife_block_round');body=[o for o in obs if not any('Steel' in m.name for m in o.data.materials)];clear_other(body)
for o in body:
 for m in o.data.materials:
  if 'Wood' in m.name:colour(m,(211,195,158),rough=.35)
  else:colour(m,(24,23,22),rough=.32)
 # High radial resolution is retained; a small bevel preserves the oval rim.
 bevel(o,.0004)
steel=material('Round_block_brushed_steel',(183,185,189),metal=1,rough=.22);black=material('Knife_grip_end',(27,27,26),rough=.35)
knives=[]
# Fit physically sized steel handles inside the existing cap.
for i,(x,y,h) in enumerate([(-.019,-.016,.133),(.002,-.012,.145),(.024,-.014,.134),(-.012,.011,.126),(.017,.012,.091)]):
 grip=lathe('Rounded_steel_handle_'+str(i),[(0,.0055),(.005,.0065),(.028,.007),(.061,.0068),(h-.005,.0058),(h,.001)],steel,64)
 subdivide([grip],1);normalise([grip],h,anchor='bbox');grip.location=(x,y,.18);knives.append(grip)
obs=body+knives;height_only(obs,.325274)
export_fit('knife_block_round','knife_block_round_v5',obs,base,.325274,None,'Photo-built oval holder with smoothly rounded stainless-steel handles. Small rim bevels preserve the holder profile; the exact knife blades and cap slots remain approximate.')

# Keep the photographed grinder's open hopper, rather than substituting a closed crank grinder.
obs,base=old('grinder');woodimage=bpy.data.images.load(str(OUT/'licensed_wood.png'));wood=material('Dark_stained_real_wood',(26,22,17),rough=.34);nt=wood.node_tree;tc=nt.nodes.new('ShaderNodeTexCoord');tex=nt.nodes.new('ShaderNodeTexImage');tex.image=woodimage;tex.projection='BOX';tex.projection_blend=.12;nt.links.new(tc.outputs['Generated'],tex.inputs['Vector']);mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(.035,.028,.018,1);nt.links.new(tex.outputs['Color'],mix.inputs[1]);nt.links.new(mix.outputs[0],bsdf(wood).inputs['Base Color'])
woodparts=[]
for o in obs:
 for m in list(o.data.materials):
  if 'Chrome' in m.name:colour(m,(196,198,200),metal=1,rough=.16)
  elif 'Steel' in m.name:colour(m,(167,168,170),metal=1,rough=.21)
  elif 'Gold' in m.name:colour(m,(139,114,64),metal=.85,rough=.23)
  elif 'Wood' in m.name:assign(o,wood);woodparts.append(o);bevel(o,.0004)
  elif 'Black' in m.name:
   colour(m,(19,18,17),rough=.3);o.data.materials.append(wood);idx=len(o.data.materials)-1
   for f in o.data.polygons:
    z=(o.matrix_world@f.center).z
    if z<.12:f.material_index=idx
   woodparts.append(o);bevel(o,.0006)
 # A dense circular hopper already has sufficient topology; smooth its normals.
native_bake(woodparts,wood,'Grinder_stained_wood');height_only(obs,.2245)
export_fit('grinder','grinder_v5',obs,base,.2245,product('967b767b-cd43-44f8-94c4-e3af008da71b'),'Photo-built open-hopper grinder retained for silhouette fidelity. Licensed wood texture applied to its dark case; edges beveled and metal parts smoothed. The texture source is a knife holder, not a downloaded grinder model.')

# Telephone: preserve its fitted keys, labels and cord; soften actual casing edges.
obs,base=old('phone')
for o in obs:
 for m in o.data.materials:
  bsdf(m).inputs['Roughness'].default_value=.38
 if len(o.data.polygons)<3000:bevel(o,.00025)
height_only(obs,.099)
cred=json.loads((ROOT/'current/phone_fit.json').read_text())['product']
export_fit('phone','phone_v5',obs,base,.099,cred,'Existing licensed desk phone retained with its photo-fitted labels and controls. Casing edges receive a small physical bevel and smooth shading. Alternative free phones were reviewed, but did not improve the photographed layout.')
print('ADDITIONAL_PRODUCTS_BUILT',len(reports),flush=True)
