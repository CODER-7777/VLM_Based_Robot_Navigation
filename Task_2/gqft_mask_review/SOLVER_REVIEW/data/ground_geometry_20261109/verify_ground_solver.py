"""CPU checks for the optional ground-plane solver mode. Run from anywhere:

  gqft_algorithm_sharing_vivekananda/.venv/bin/python gqft_mask_review/ground_geometry_20261109/verify_ground_solver.py [legacy_model_copy.py]

Passing a copy of models/gqft.py from before this change also checks that default
(legacy) outputs are bit-identical.
"""
import glob
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
TASK2 = HERE.parents[1]
REPO = TASK2 / "gqft_algorithm_sharing_vivekananda"
sys.path.insert(0, str(REPO))

from step2.geometry import CameraModel  # noqa: E402
from step2.ground_solver import GroundPlaneSolver  # noqa: E402
from step2.models.gqft import GQFT, GQFTConfig, gqft_loss  # noqa: E402
from step2.checkpoint import load_gqft_checkpoint, initialize_gqft  # noqa: E402

CAM = CameraModel(width=960, height=540, fx=198.82250993908562, fy=198.82250993908562,
                  cx=480., cy=270., camera_height_m=1.2, pitch_down_deg=30.)
results = {}


def check(name, ok, detail=""):
    results[name] = {"pass": bool(ok), "detail": detail}
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def synthetic_flow(solver, motion):
    g = solver.grid(90, 160, "cpu")
    uv, _ = solver._project(motion, g["body"], g["R"])
    flow = torch.zeros(len(motion), 4, 90, 160)
    flow[:, :2] = ((uv - g["uv0"][None]) / torch.tensor([960., 540.])).transpose(1, 2).reshape(-1, 2, 90, 160)
    flow[:, 2], flow[:, 3] = .3, 1.
    return flow


def batch(b=2, t=6, seed=0):
    gen = torch.Generator().manual_seed(seed)
    solver = GroundPlaneSolver(CAM)
    motion = torch.rand(b * t, 3, generator=gen) * torch.tensor([.08, .04, .2]) - torch.tensor([0., .02, .1])
    flow = synthetic_flow(solver, motion).reshape(b, t, 4, 90, 160)
    q = torch.tensor([[480., 500.], [300., 450.]]).expand(b, -1, -1).clone()
    return {"flow": flow, "history_mask": torch.ones(b, t, dtype=torch.bool), "query_uv": q,
            "query_norm": q / torch.tensor([959., 539.]), "motion": motion.reshape(b, t, 3),
            "displacement": torch.zeros(b, t + 1, 3), "target_yaw": torch.zeros(b, t + 1, 1),
            "target_uv": torch.rand(b, 2, t + 1, 2, generator=gen),
            "target_valid": torch.ones(b, 2, t + 1, dtype=torch.bool)}


def run(model, x):
    return model(x["flow"], x["history_mask"], x["query_uv"], x["query_norm"])


GROUND = GQFTConfig(predict_yaw=True, motion_integration="yaw_local", motion_prior="ground_solver",
                    canvas_height=540)

# 1. exact recovery of known planar motion
s = GroundPlaneSolver(CAM)
truth = torch.tensor([[.07, -.02, .10], [.05, 0., -.12], [0., 0., 0.]])
est, _ = s(synthetic_flow(s, truth))
check("synthetic_motion_recovered", torch.allclose(est, truth, atol=1e-4), f"max err {float((est-truth).abs().max()):.2e}")

# 2. no usable floor -> finite, zero motion
empty = torch.zeros(2, 4, 90, 160)
e, info = s(empty)
check("no_floor_is_finite_zero", torch.isfinite(e).all() and e.abs().max() < 1e-6, str(info["weight_sum"].tolist()))

# 3. defaults unchanged (no new parameters; optional bit-identity against old source)
torch.manual_seed(0)
legacy_keys = set(GQFT(GQFTConfig(predict_yaw=True), CAM).state_dict())
check("default_has_no_solver_params", not any(k.startswith(("ground_solver", "solver_embed")) for k in legacy_keys))
if len(sys.argv) > 1:
    spec = importlib.util.spec_from_file_location("old_gqft", sys.argv[1])
    old = importlib.util.module_from_spec(spec)
    sys.modules["old_gqft"] = old
    spec.loader.exec_module(old)
    x = batch()
    for cfg in (dict(), dict(predict_yaw=True), dict(predict_yaw=True, motion_integration="yaw_local"),
                dict(spatial_pooling="mean_max")):
        torch.manual_seed(1); a = GQFT(GQFTConfig(**cfg), CAM).eval()
        torch.manual_seed(1); bm = old.GQFT(old.GQFTConfig(**cfg), CAM).eval()
        with torch.no_grad():
            oa, ob = run(a, x), run(bm, x)
        same = all(torch.equal(oa[k], ob[k]) for k in ob if torch.is_tensor(ob[k]))
        check(f"legacy_bit_identical_{cfg or 'default'}", same)

# 4. ground mode starts exactly at the solver
torch.manual_seed(2)
m = GQFT(GROUND, CAM).eval()
x = batch()
with torch.no_grad():
    out = run(m, x)
check("init_equals_solver_motion", torch.allclose(out["solver_motion"], x["motion"], atol=1e-4))
check("init_yaw_equals_solver", torch.allclose(out["delta_yaw"][..., 0], x["motion"][..., 2], atol=1e-4))

# 5. gradients reach learned weights, embedding and residual heads
cfg = GQFTConfig(**{**GROUND.__dict__, "ground_learned_weights": True})
torch.manual_seed(3)
m = GQFT(cfg, CAM).train()
x = batch()
x["displacement"] = torch.randn(2, 7, 3) * .05
x["target_yaw"] = torch.randn(2, 7, 1) * .1
# Noisy flow: with perfectly consistent flow every weighting gives the same answer (zero gradient).
x["flow"][:, :, :2] += torch.randn(x["flow"][:, :, :2].shape, generator=torch.Generator().manual_seed(4)) * 2e-3
loss = gqft_loss(run(m, x), x)["loss"]
loss.backward()
names = ["ground_solver.weight_net.4.weight", "solver_embed.weight", "delta_head.2.weight", "yaw_head.2.weight"]
grads = {n: p.grad for n, p in m.named_parameters()}
check("loss_finite", bool(torch.isfinite(loss.detach())), f"{float(loss.detach()):.4f}")
print({n: None if grads[n] is None else float(grads[n].abs().sum()) for n in names})
check("gradients_reach_new_modules", all(grads[n] is not None and torch.isfinite(grads[n]).all()
                                         and grads[n].abs().sum() > 0 for n in names))

# 6. strict checkpoint round trip and warm start rules
with tempfile.TemporaryDirectory() as d:
    path = Path(d) / "g.pt"
    torch.save({"architecture": "GQFT", "model": m.state_dict(), "model_config": cfg.__dict__,
                "camera_model": CAM.__dict__}, path)
    loaded, _ = load_gqft_checkpoint(path)
    check("ground_checkpoint_strict_roundtrip", loaded.config == cfg)
    src = GQFT(GQFTConfig(predict_yaw=True, canvas_height=540), CAM)
    ck = {"architecture": "GQFT", "model": src.state_dict(),
          "model_config": GQFTConfig(predict_yaw=True, canvas_height=540).__dict__, "camera_model": CAM.__dict__}
    dst = GQFT(GROUND, CAM)
    try:
        initialize_gqft(dst, ck)
        check("warm_start_requires_head_reset", False)
    except ValueError:
        check("warm_start_requires_head_reset", True)
    dst = GQFT(GROUND, CAM)
    initialize_gqft(dst, ck, reinitialize_motion_heads=True)
    enc_same = torch.equal(dst.flow_encoder.net[0][0].weight, src.flow_encoder.net[0][0].weight)
    heads_zero = dst.delta_head[2].weight.abs().sum() == 0 and dst.yaw_head[2].weight.abs().sum() == 0
    check("warm_start_loads_encoder_resets_residual_heads", enc_same and heads_zero)
    bad = dict(ck, model={k: v for k, v in ck["model"].items() if not k.startswith("temporal.layers.0")})
    try:
        initialize_gqft(GQFT(GROUND, CAM), bad, reinitialize_motion_heads=True)
        check("warm_start_rejects_other_missing_weights", False)
    except ValueError:
        check("warm_start_rejects_other_missing_weights", True)

# 7. episode 629: real SEA-RAFT flow vs recorded poses (diagnostic, not a benchmark)
root = TASK2 / "gqft_mask_review/transfers/20261104_gqft_restore/local_backup/gqft_algorithm_sharing_vivekananda/analysis/masked_attention_v1/episodes/ep629"
poses = np.load(TASK2 / "gqft_mask_review/inputs/ep629/b10_A_drivefix_idx3_20260829_114756.npz")["pose"]
ep = {}
for leg in sorted(root.glob("leg*")):
    z = np.load(next(leg.rglob("flow_searaft_160x90.npz")))
    ins = json.load(open(next(leg.rglob("episode_inputs.json"))))
    f = np.concatenate([z["flow"] * z["valid"][..., None], z["confidence"][..., None], z["valid"][..., None]], -1)
    f = torch.from_numpy(f).permute(0, 3, 1, 2).float()
    mo, _ = GroundPlaneSolver(CAM)(f)
    pos, yaw, est = np.zeros(2), 0., [np.zeros(2)]
    for dx, dy, dp in mo.double().numpy():
        pos = pos + np.array([[np.cos(yaw), -np.sin(yaw)], [np.sin(yaw), np.cos(yaw)]]) @ [dx, dy]
        yaw += dp
        est.append(pos.copy())
    s0 = ins["window_start_episode_frame"]
    p = poses[s0:s0 + len(mo) + 1]
    y0, dd = p[0, 2], p[:, :2] - p[0, :2]
    gt = np.stack([dd @ [np.cos(y0), np.sin(y0)], dd @ [np.sin(y0), -np.cos(y0)]], -1)
    err = np.linalg.norm(np.array(est) - gt, axis=1)
    rv = json.load(open(next((TASK2 / "gqft_mask_review/ep629" / leg.name).rglob("review.json"))))
    ep[leg.name] = {"solver_mean_m": float(err[1:].mean()), "solver_end_m": float(err[-1]),
                    "gqft_attention_yaw_mean_m": rv["metrics"]["unmasked"]["mean_ground_error_m"],
                    "gqft_attention_yaw_end_m": rv["metrics"]["unmasked"]["endpoint_ground_error_m"]}
    print(leg.name, {k: round(v, 3) for k, v in ep[leg.name].items()})
wins = sum(v["solver_mean_m"] < v["gqft_attention_yaw_mean_m"] for v in ep.values())
print(f"DIAGNOSTIC (not a pass/fail gate): solver lower mean ground error on {wins}/{len(ep)} legs; "
      "cutoff 1.5 m was chosen on these same windows, so this is exploratory only")

json.dump({"checks": results, "episode629": ep}, open(HERE / "verification.json", "w"), indent=2)
print(f"{sum(r['pass'] for r in results.values())}/{len(results)} checks passed")
