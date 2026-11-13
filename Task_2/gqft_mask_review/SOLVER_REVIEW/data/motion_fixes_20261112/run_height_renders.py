"""Render only complete, unambiguous support plans, into a separate dataset."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]


def main():
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='4':raise RuntimeError('GPU4 is the authorized device')
    audit=ROOT/'height_audit_habitat'
    summary=json.loads((audit/'height_summary.json').read_text())
    out=ROOT/'height_corrected_v1'
    report={'scope':'Mesh-reconstructed 1.2m counterfactual RGB; originals preserved; no training or fitted output scale',
            'completed':[],'blocked':[],'status':'running'}
    for item in summary['episodes']:
        ep=item['episode']
        if item['status_counts']!={'measured':item['frames']}:
            report['blocked'].append({'episode':ep,'reason':'Uncertain floor support; no interpolation or guessed heights',
                                      'status_counts':item['status_counts']})
            continue
        command=['/data/robotics/toshith/vln_baselines/envs/habitat38/bin/python','-B',
                 str(ROOT/'render_corrected_frames.py'),'--poses-file',item['pose_file'],
                 '--audit-file',str(audit/('ep%d_height_audit.json'%ep)),'--out-root',str(out)]
        subprocess.run(command,check=True)
        report['completed'].append(ep)
        (ROOT/'height_render_status.json').write_text(json.dumps(report,indent=2)+'\n')
    report['status']='completed_safe_subset'
    (ROOT/'height_render_status.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
