"""Regression: validation-created geometry must support subsequent backpropagation."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--unpatched', type=Path, required=True)
    parser.add_argument('--device', default='cpu', choices=['cpu', 'cuda'])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source))
    from step2.geometry import CameraModel
    from step2.ground_solver import GroundPlaneSolver
    from step2.models.gqft import GQFT, GQFTConfig, gqft_loss
    spec = importlib.util.spec_from_file_location('unpatched_solver', args.unpatched)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    cam = CameraModel(width=960, height=540, fx=198.82250993908562,
                      fy=198.82250993908562, cx=480., cy=270.,
                      camera_height_m=1.2, pitch_down_deg=30.)
    torch.manual_seed(0)
    flow = torch.zeros(2, 4, 90, 160, device=args.device)
    flow[:, :2] = torch.randn_like(flow[:, :2])*.0001 + .001
    flow[:, 2:] = 1
    before = old.GroundPlaneSolver(cam, max_floor_m=1., learned_weights=True).to(args.device)
    after = GroundPlaneSolver(cam, max_floor_m=1., learned_weights=True).to(args.device)
    after.load_state_dict(before.state_dict())
    with torch.inference_mode():
        prior, _ = before(flow)
        current, _ = after(flow)
    checks = {'unchanged_validation_motion': torch.equal(prior, current),
              'cached_geometry_is_normal': all(not t.is_inference() for g in after._grid_cache.values() for t in g.values())}
    try:
        motion, _ = before(flow)
        motion.square().sum().backward()
        checks['original_bug_reproduced'] = False
    except RuntimeError as error:
        checks['original_bug_reproduced'] = 'Inference tensors cannot be saved for backward' in str(error)
    motion, _ = after(flow)
    motion.square().sum().backward()
    gradient = after.weight_net[-1].weight.grad
    checks['solver_gradients_finite_nonzero'] = gradient is not None and bool(torch.isfinite(gradient).all()) and bool(gradient.abs().sum() > 0)
    padded = flow.clone()
    padded[1] = 0
    after.zero_grad(set_to_none=True)
    motion, info = after(padded)
    (motion.square().sum()+info['residual_rms_px'].sum()).backward()
    g = after.weight_net[-1].weight.grad
    checks['empty_frame_rms_backward_finite'] = g is not None and bool(torch.isfinite(g).all())
    checks['empty_frame_diagnostic_zero'] = float(info['residual_rms_px'][1].detach()) == 0.
    config = GQFTConfig(predict_yaw=True, motion_integration='yaw_local',
                        motion_prior='ground_solver', ground_learned_weights=True,
                        ground_max_floor_m=1., canvas_height=810)
    model = GQFT(config, cam).to(args.device).eval()
    x = flow.reshape(1, 2, 4, 90, 160)
    history = torch.ones(1, 2, dtype=torch.bool, device=args.device)
    query = flow.new_tensor([[[480., 809.]]])
    norm = query/flow.new_tensor([959., 539.])
    with torch.inference_mode():
        model(x, history, query, norm)
    model.train()
    with torch.autocast(args.device, dtype=torch.bfloat16, enabled=args.device == 'cuda'):
        out = model(x, history, query, norm)
        batch = {'displacement': flow.new_zeros(1, 3, 3),
                 'target_yaw': flow.new_zeros(1, 3, 1),
                 'target_uv': norm[:, :, None].expand(1, 1, 3, 2),
                 'target_valid': torch.ones(1, 1, 3, dtype=torch.bool, device=args.device),
                 'history_mask': history}
        loss = gqft_loss(out, batch)['loss']
    loss.backward()
    g = model.ground_solver.weight_net[-1].weight.grad
    checks['full_model_validation_then_backward'] = bool(torch.isfinite(loss)) and g is not None and bool(torch.isfinite(g).all())
    model.zero_grad(set_to_none=True)
    padded_history = history.clone()
    padded_history[0, 1] = False
    batch['history_mask'] = padded_history
    with torch.autocast(args.device, dtype=torch.bfloat16, enabled=args.device == 'cuda'):
        out = model(padded.reshape_as(x), padded_history, query, norm)
        padded_loss = gqft_loss(out, batch)['loss']
    padded_loss.backward()
    checks['full_model_padded_backward_finite'] = all(
        p.grad is None or bool(torch.isfinite(p.grad).all()) for p in model.parameters())
    result = {'device': args.device, 'torch': torch.__version__, 'checks': checks, 'loss': float(loss.detach())}
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
