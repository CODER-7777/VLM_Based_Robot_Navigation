"""Validate config and start the gateway using tmux or the user service manager."""
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
import sys
import time
from gateway import configuration

base=Path(__file__).resolve().parent
path=Path(sys.argv[1]).resolve()
cfg=configuration(path)
for field in ['tls_certificate','tls_private_key']:
    if not Path(cfg[field]).is_file():raise SystemExit('Missing '+field+' file.')
argv=['/usr/bin/python3','-u','-B',str(base/'gateway.py'),'--config',str(path)]
if shutil.which('tmux'):
    session='task5-campus-collector'
    exists=subprocess.run(['tmux','has-session','-t','='+session],capture_output=True).returncode==0
    if not exists:
        subprocess.run(['tmux','new-session','-d','-s',session,'-c',str(base),'exec '+shlex.join(argv)],check=True)
    print(('Reusing' if exists else 'Started')+' tmux session: '+session)
    print('Logs: tmux attach -t '+session)
elif shutil.which('systemd-run') and subprocess.run(['systemctl','--user','show-environment'],capture_output=True).returncode==0:
    unit='data-from-dashboard-collector.service'
    active=subprocess.run(['systemctl','--user','is-active','--quiet',unit]).returncode==0
    if not active:
        state=subprocess.run(['systemctl','--user','show',unit,'--property=LoadState','--value'],capture_output=True,text=True)
        if state.stdout.strip()=='not-found':
            subprocess.run(['systemd-run','--user','--unit='+unit,'--working-directory='+str(base),
                            '--property=Restart=on-failure','--property=RestartSec=5',*argv],check=True)
        else:subprocess.run(['systemctl','--user','restart',unit],check=True)
    print(('Reusing' if active else 'Started')+' user service: '+unit)
    print('Logs: journalctl --user -u '+unit+' -f')
else:raise SystemExit('A running systemd user manager or tmux is required to keep the server running.')
print('Configured campus URL: '+cfg['public_origin'])
for _ in range(100):
    try:
        with socket.create_connection((cfg['bind'],cfg['port']),timeout=.5):pass
        print('Listening on the configured address. Test HTTPS and recording from a contributor browser before sharing.')
        break
    except OSError:time.sleep(.1)
else:raise SystemExit('Listener did not become ready. Inspect the logs shown above.')
