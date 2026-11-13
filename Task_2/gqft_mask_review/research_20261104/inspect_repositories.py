"""Read public repository metadata/source for the literature review; never run it."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
REPOS = {
    'abdo-eldesokey/nconv': ['README.md', 'modules/nconv.py'],
    'NVIDIA/partialconv': ['README.MD', 'models/partialconv2d.py'],
    'JiahuiYu/generative_inpainting': ['README.md', 'inpaint_ops.py'],
    'castacks/tartanvo': ['README.md', 'Datasets/utils.py', 'TartanVO.py', 'Network/VOFlowNet.py'],
    'princeton-vl/DPVO': ['README.md', 'dpvo/net.py', 'dpvo/patchgraph.py', 'dpvo/ba.py'],
    'kawine/contextual': ['README.md', 'analyze.py'],
    'vyraun/Half-Size': ['README.md'],
    'facebookresearch/RankMe': [],
    'alexgkendall/caffe-posenet': ['README.md'],
}


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'GQFT-research-audit', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def inspect(repo, selected):
    folder = ROOT/'repositories'/repo.replace('/', '__')
    folder.mkdir(parents=True, exist_ok=True)
    result = {'repository': repo, 'url': 'https://github.com/'+repo,
              'checked_utc': datetime.now(timezone.utc).isoformat(),
              'execution': 'Source inspected as text only; no install, model download or execution.'}
    try:
        metadata = json.loads(fetch('https://api.github.com/repos/'+repo))
        result.update(http_status=200, default_branch=metadata['default_branch'],
                      description=metadata.get('description'), archived=metadata['archived'],
                      license=metadata.get('license'), homepage=metadata.get('homepage'))
        commit = json.loads(fetch('https://api.github.com/repos/'+repo+'/commits/'+metadata['default_branch']))
        sha = commit['sha']; result['commit_sha'] = sha
        tree = json.loads(fetch('https://api.github.com/repos/'+repo+'/git/trees/'+sha+'?recursive=1'))
        paths = [row['path'] for row in tree['tree'] if row['type'] == 'blob']
        result['tree_paths'] = paths
        result['tree_truncated'] = tree.get('truncated', False)
        if repo == 'abdo-eldesokey/nconv':
            selected = [name for name in selected if name in paths]+[name for name in paths if name.endswith('.py') and 'nconv' in Path(name).name.lower()][:2]
        if repo == 'vyraun/Half-Size':
            selected += [p for p in paths if p.endswith('.py') and not p.startswith('word-embeddings-benchmarks/')][:3]
        licenses = [p for p in paths if '/' not in p and Path(p).name.lower().startswith(('license','copying'))]
        selected = list(dict.fromkeys(selected+licenses))
        result['files'] = []
        for name in selected:
            if name not in paths:
                result['files'].append({'path': name, 'status': 'not present at audited revision'})
                continue
            raw = 'https://raw.githubusercontent.com/'+repo+'/'+sha+'/'+name
            content = fetch(raw)
            target = folder/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            result['files'].append({'path': name, 'status': 'downloaded for static reading',
                'url': 'https://github.com/'+repo+'/blob/'+sha+'/'+name,
                'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)})
        (folder/'metadata.json').write_text(json.dumps(result, indent=2)+'\n')
    except urllib.error.HTTPError as error:
        result.update(http_status=error.code, error=str(error))
        (folder/'metadata.json').write_text(json.dumps(result, indent=2)+'\n')
    except Exception as error:
        result['error'] = repr(error)
        (folder/'metadata.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(inspect, repo, files) for repo, files in REPOS.items()]
        for job in as_completed(jobs):
            result = job.result(); results.append(result)
            print(result['repository'], result.get('http_status'), result.get('commit_sha', ''), result.get('error', ''), flush=True)
    (ROOT/'repository_audit.json').write_text(json.dumps(sorted(results, key=lambda row: row['repository']), indent=2)+'\n')


if __name__ == '__main__':
    main()
