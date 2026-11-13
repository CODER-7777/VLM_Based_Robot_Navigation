"""Download completed episode arrays/keyframes only; no GPU work or model transfer."""
import argparse
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='guest-isl@172.26.186.222')
    parser.add_argument('--metadata',type=Path,default=HERE/'trained_episode_overlays/CURRENT_RUN.json',
                        help='Explicit run receipt; leave the primary gallery pointer unchanged for experiments')
    args=parser.parse_args()
    meta=json.loads(args.metadata.read_text())
    local=Path(meta['local']);remote=meta['remote']
    code='''from pathlib import Path
import json,tarfile,sys,io
r=Path(%r);data=(r/'manifest.json').read_bytes();manifest=json.loads(data)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as archive:
 info=tarfile.TarInfo('manifest.json');info.size=len(data);archive.addfile(info,io.BytesIO(data))
 if (r/'status.json').exists():archive.add(r/'status.json',arcname='server_status.json')
 if (r/'input_provenance.json').exists():archive.add(r/'input_provenance.json',arcname='input_provenance.json')
 if (r/'inputs').exists():archive.add(r/'inputs',arcname='inputs')
 for episode in manifest['episodes']:
  folder=r/('ep'+str(episode['episode']))
  for f in sorted(folder.rglob('*')):
   if f.is_file() and f.suffix in ['.json','.jpg']:archive.add(f,arcname=str(f.relative_to(r)))
'''%remote
    archive=local/'downloaded_predictions.tar.gz'
    with archive.open('wb') as stream:
        result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12',args.host,
            '/data/robotics/toshith/envs/agentvln/bin/python -B -c '+shlex.quote(code)],
            stdout=stream,stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr.decode())
    with tarfile.open(archive) as bundle:
        if not all((local/item.name).resolve().is_relative_to(local.resolve()) for item in bundle.getmembers()):
            raise ValueError('Unsafe archive member')
        bundle.extractall(local)
    manifest=json.loads((local/'manifest.json').read_text())
    server=json.loads((local/'server_status.json').read_text())
    meta['status']=server['status'];meta['downloaded_episodes']=[e['episode'] for e in manifest['episodes']]
    args.metadata.write_text(json.dumps(meta,indent=2)+'\n')
    (local/'run.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps({'downloaded_episodes':len(manifest['episodes']),'expected':manifest['expected_episode_count'],
                      'downloaded_legs':sum(e['legs'] for e in manifest['episodes']),'server':server},indent=2))


if __name__=='__main__':main()
