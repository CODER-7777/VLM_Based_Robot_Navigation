from pathlib import Path
import json,os,subprocess,socket
R=Path('/data/robotics/toshith/rxr_author/refined')
W=R/'toaster_selected';D=W/'dashboard';D.mkdir(exist_ok=True)
assert not json.loads((W/'audit.json').read_text())['issues']
assert (W/'previews/toaster_comparison.jpg').stat().st_mtime>(W/'test.glb').stat().st_mtime
assert (D/'model-viewer.min.js').stat().st_size>100000
scene=D/'scenes/mp3d/2azQ1b91cZZ';scene.mkdir(parents=True,exist_ok=True)
for src in (R/'toaster_wall_repair/dashboard/scenes/mp3d/2azQ1b91cZZ').iterdir():
 target=W/'test.glb' if src.name=='2azQ1b91cZZ.glb' else src.resolve()
 dst=scene/src.name
 if not dst.exists():dst.symlink_to(target,target_is_directory=target.is_dir())
args=json.loads((R/'toaster_wall_repair/dashboard/launch.json').read_text())
args=[a.replace(str(R/'toaster_wall_repair/dashboard'),str(D)).replace('serve_wall.py','serve_selected.py') for a in args]
args[args.index('--port')+1]='8776'
for flag in ['--output','--challenge-output','--baseline-output','--cases-dir']:
 p=Path(args[args.index(flag)+1]);(p if flag=='--cases-dir' else p.parent).mkdir(parents=True,exist_ok=True)
(D/'launch.json').write_text(json.dumps(args,indent=2))
with socket.socket() as sock:
 if sock.connect_ex(('127.0.0.1',8776))==0:raise SystemExit('Port 8776 already in use; leaving it unchanged')
env=dict(os.environ,PYTHONPATH='/home/guest-isl/rishabh/NAVIDA',CUDA_VISIBLE_DEVICES='4',MAGNUM_LOG='quiet',HABITAT_SIM_LOG='quiet')
with (D/'ui.log').open('w') as log:
 process=subprocess.Popen(args,cwd='/home/guest-isl/rishabh/NAVIDA',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(D/'pid').write_text(str(process.pid))
print('SELECTED_TOASTER_DASHBOARD_PID',process.pid)
