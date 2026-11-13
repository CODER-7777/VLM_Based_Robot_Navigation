"""Write a 2x2 matched pilot plan/commands. Does not train or contact the server."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shlex
import sys

LAB=Path(__file__).resolve().parent
ROOT=LAB.parent/'gqft_algorithm_sharing_vivekananda'
sys.path.insert(0,str(ROOT))
from step2.models.gqft import GQFTConfig


def main():
    out=LAB/'implementation_20261016'
    out.mkdir(exist_ok=True)
    server_root='/data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda'
    staged_root=server_root+'/gqft_mask_review/source_20261016'
    common=['/data/robotics/toshith/envs/agentvln/bin/python','-B','-m','step2.train_gqft',
            '--manifest',server_root+'/results/hsgm_manifest_v1.json','--steps','500',
            '--batch-size','6','--workers','2','--queries','1','--max-history','30',
            '--virtual-extension-px','270','--seed','20260820','--warmup','50',
            '--val-every','100','--checkpoint-every','100','--min-stable-step','500',
            '--init-checkpoint',server_root+'/runs/gqft_spatial_yaw_v1/best.pt',
            '--reinitialize-motion-heads','--predict-yaw','--target-ground-plane','sequence_floor',
            '--mask-coverage-rule','receptive_field','--mask-soft-floor','0.25',
            '--mask-logit-strength','1','--mask-hard-min-coverage','0',
            '--mask-ground-near-m','0.5','--mask-ground-far-m','8','--allow-gpu']
    arms=[]
    for name,mask,integration in [('reference','none','keyframe'),
                                   ('masked_only','soft_confidence_ground','keyframe'),
                                   ('yaw_local_only','none','yaw_local'),
                                   ('masked_yaw_local','soft_confidence_ground','yaw_local')]:
        config=GQFTConfig(max_history=30,canvas_height=810,predict_yaw=True,
                         spatial_mask=mask,mask_coverage_rule='receptive_field',motion_integration=integration)
        command=common+['--spatial-mask',mask,'--motion-integration',integration,
                        '--out',server_root+'/gqft_mask_review/pilots/20261016/'+name]
        arms.append({'name':name,'model_config':asdict(config),'argv':command,
                     'shell_command':'CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=2 PYTHONDONTWRITEBYTECODE=1 '+shlex.join(command)})
    payload={'prepared_only':True,'trained':False,'server_source_root':staged_root,'gpu':'2',
             'checkpoint_sha256':'40729f0f537c28e5b07565aba01133bb594c7781cc59eedf90bc3fafa939ee8d',
             'design':'2x2: mask off/on x keyframe/yaw_local. All arms predict yaw and reset the same delta/logvar heads with the same seed.',
             'budget':'Proposed smoke pilot: four sequential arms x500 steps; not a convergence/generalization claim.',
             'labels':'sequence_floor held fixed; fixed_rig is a separate experiment.',
             'validation':'Training script uses its existing deterministic-per-index mixed-history validation for checkpointing; after pilot use matched reference30/history24 validation separately before comparing with frozen-window scores.',
             'history_gate':'Pilot does not establish sufficient history; run full validation history/ambiguity study before any reporting-only test.',
             'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted((ROOT/'step2').rglob('*.py'))},'arms':arms}
    (out/'pilot_plan.json').write_text(json.dumps(payload,indent=2)+'\n')
    lines=['# Prepared commands; NOT executed. Run sequentially from the isolated staged source root.',
           '# See README.md for local verification, source staging, and protocol limits.',
           'cd '+shlex.quote(staged_root),'']
    for arm in arms:
        lines.extend(['# '+arm['name'],arm['shell_command'],''])
    (out/'PILOT_COMMANDS.txt').write_text('\n'.join(lines))
    print(json.dumps({'prepared_only':True,'arms':[x['name'] for x in arms],'plan':str(out/'pilot_plan.json')},indent=2))


if __name__=='__main__':
    main()
