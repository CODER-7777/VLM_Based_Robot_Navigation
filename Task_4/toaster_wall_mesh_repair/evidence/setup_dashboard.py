from pathlib import Path
import os,json,subprocess
R=Path('/data/robotics/toshith/rxr_author');A=R/'refined/toaster_upgrade/dashboard';W=R/'refined/toaster_wall_repair';D=W/'dashboard';D.mkdir(exist_ok=True)
assert not json.load(open(W/'audit.json'))['issues']
assert (W/'previews/toaster_comparison.jpg').stat().st_mtime>(W/'test.glb').stat().st_mtime
scene=D/'scenes/mp3d/2azQ1b91cZZ';scene.mkdir(parents=True,exist_ok=True)
for src in (A/'scenes/mp3d/2azQ1b91cZZ').iterdir():
 target=W/'test.glb' if src.name=='2azQ1b91cZZ.glb' else src.resolve();dst=scene/src.name
 if not dst.exists():dst.symlink_to(target,target_is_directory=target.is_dir())
s=(A/'serve_toaster.py').read_text().replace('refined/toaster_upgrade','refined/toaster_wall_repair').replace("'version': 'toaster_upgrade'","'version': 'toaster_wall_repair'").replace('Toaster realism upgrade loaded','Toaster corner mesh repair loaded').replace('free Cuisinart model with kitchen-photo reflections.','tiled wall and cabinet join repaired.').replace('Real photograph | previous repaired toaster | new toaster','Real photograph | before wall repair | repaired corner').replace('http://localhost:8767/','http://localhost:8770/').replace('Previous repaired dashboard (route preserved)','Previous toaster dashboard (route preserved)')
s=s.replace('<p>Model: siotech2011','<p>Reference: Black &amp; Decker 2-Slice Toaster, resembling T2030. Installed model remains a Cuisinart substitute. Tile pattern placement is reconstructed.</p><p>Model: siotech2011')
(D/'serve_wall.py').write_text(s)
args=[v.replace(str(A),str(D)).replace('serve_toaster.py','serve_wall.py') for v in json.load(open(A/'launch.json'))];args[args.index('--port')+1]='8772'
for flag in ['--output','--challenge-output','--baseline-output','--cases-dir']:
 p=Path(args[args.index(flag)+1]);(p if flag=='--cases-dir' else p.parent).mkdir(parents=True,exist_ok=True)
json.dump(args,open(D/'launch.json','w'),indent=2)
env=dict(os.environ,PYTHONPATH='/home/guest-isl/rishabh/NAVIDA',CUDA_VISIBLE_DEVICES='4',MAGNUM_LOG='quiet',HABITAT_SIM_LOG='quiet')
with open(D/'ui.log','w') as log:proc=subprocess.Popen(args,cwd='/home/guest-isl/rishabh/NAVIDA',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(D/'pid').write_text(str(proc.pid));print('WALL_DASHBOARD_PID',proc.pid)
