from pathlib import Path
import os, signal, socket, subprocess, time
p=Path('/data/robotics/toshith/vivekananda/kitchen_tray_background_repair/panoramas')
s=p/'panorama_server.py'
x=s.read_text().replace("REPAIRS = Path('/data/robotics/toshith/vivekananda/kitchen_appliance_refinement_20261011')", "REPAIRS = Path('/data/robotics/toshith/vivekananda/kitchen_tray_background_repair')")
assert 'REPAIRS = Path(\'/data/robotics/toshith/vivekananda/kitchen_tray_background_repair\')' in x
s.write_text(x)
for f in list((p/'images').glob('*_after.jpg'))+list((p/'images').glob('*_comparison.jpg')):f.unlink()
pid=int(Path('/data/robotics/toshith/vivekananda/kitchen_tray_background_repair/panorama_preview.pid').read_text())
os.kill(pid,signal.SIGTERM)
for _ in range(100):
 with socket.socket() as c:free=c.connect_ex(('127.0.0.1',8793))!=0
 if free:break
 time.sleep(.1)
assert free
log=(p/'logs/preview.log').open('a')
env=dict(os.environ,KITCHEN_PANORAMA_PORT='8793',PYTHONDONTWRITEBYTECODE='1')
proc=subprocess.Popen(['/data/robotics/toshith/envs/kitchen3d/bin/python','-u',str(s)],cwd=p,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
Path('/data/robotics/toshith/vivekananda/kitchen_tray_background_repair/panorama_preview.pid').write_text(str(proc.pid));print('V8_PANORAMA_PREVIEW',proc.pid)
