"""Zero-training ground-plane ego-motion from cached SEA-RAFT flow (feasibility check)."""
import json, glob, os, sys
import numpy as np
from scipy.optimize import least_squares

W, H, F, CX, CY, HGT, P = 960, 540, 198.82250993908562, 480., 270., 1.2, np.deg2rad(30)
s, c = np.sin(P), np.cos(P)
R = np.array([[0, -1, 0], [-s, 0, -c], [c, 0, -s]])  # body(fwd,left,up) -> OpenCV camera
gw, gh = 160, 90
u = (np.arange(gw) + .5) * W / gw - .5
v = (np.arange(gh) + .5) * H / gh - .5
uu, vv = np.meshgrid(u, v)
rays = np.stack([(uu - CX) / F, (vv - CY) / F, np.ones_like(uu)], -1)
n_up = np.array([0, -c, -s])
den = rays @ n_up
lam = np.where(den < -1e-6, -HGT / np.minimum(den, -1e-6), np.inf)
Pc = rays * lam[..., None]                      # ground points, camera0 coords
Pc = np.where(np.isfinite(Pc), Pc, 0.); Pb = Pc @ R                                     # -> body0 coords (R orthonormal)
dist = np.linalg.norm(Pb[..., :2], axis=-1)
ground = np.isfinite(lam) & (dist < float(os.environ.get('MAX_FLOOR_M', '6.0')))

def predict_flow(x, pts):
    dx, dy, dpsi = x
    q = pts - np.array([dx, dy, 0])
    cz, sz = np.cos(dpsi), np.sin(dpsi)
    p1 = np.stack([cz*q[:, 0] + sz*q[:, 1], -sz*q[:, 0] + cz*q[:, 1], q[:, 2]], -1)
    C = p1 @ R.T
    z = np.maximum(C[:, 2], 1e-3)
    return np.stack([F*C[:, 0]/z + CX, F*C[:, 1]/z + CY], -1)

def estimate(flow, conf, valid, x0):
    m = ground & (valid > .5)
    pts, obs0 = Pb[m], np.stack([uu[m], vv[m]], -1)
    obs1 = obs0 + flow[m] * np.array([W, H])
    w = np.sqrt(np.clip(conf[m], 1e-3, None))[:, None]
    res = lambda x: ((predict_flow(x, pts) - obs1) * w).ravel()
    return least_squares(res, x0, loss='soft_l1', f_scale=2.0).x

def body_rel(poses, i0):
    x0, z0, y0 = poses[i0]
    f0, l0 = np.array([np.cos(y0), np.sin(y0)]), np.array([np.sin(y0), -np.cos(y0)])
    d = poses[:, :2] - poses[i0, :2]
    return np.stack([d @ f0, d @ l0], -1), -(poses[:, 2] - y0)

poses = np.load(sys.argv[1], allow_pickle=True)['pose']
for leg in sorted(glob.glob(sys.argv[2] + '/leg*')):
    probe = glob.glob(leg + '/*/probe')[0] if glob.glob(leg + '/*/probe') else glob.glob(leg + '/*')[0]
    d = np.load(glob.glob(probe + '/flow_searaft_160x90.npz')[0] if os.path.isdir(probe) else glob.glob(leg + '/*/flow_searaft_160x90.npz')[0])
    ins = json.load(open(glob.glob(leg + '/*/**/episode_inputs.json', recursive=True)[0]))
    s0, T = ins['window_start_episode_frame'], d['flow'].shape[0]
    gt, gyaw = body_rel(poses[s0:s0 + T + 1], 0)
    pos, yaw, x = np.zeros(2), 0., np.zeros(3); est = [pos.copy()]
    for t in range(T):
        x = estimate(d['flow'][t].astype(np.float64), d['confidence'][t], d['valid'][t], x)
        rot = np.array([[np.cos(yaw), -np.sin(yaw)], [np.sin(yaw), np.cos(yaw)]])
        pos = pos + rot @ x[:2]; yaw += x[2]; est.append(pos.copy())
    est = np.array(est); err = np.linalg.norm(est - gt, axis=1)
    print(f"{os.path.basename(leg)} start={s0} GT end(f,l)={gt[-1].round(3)} est end={est[-1].round(3)} "
          f"mean_err={err[1:].mean():.3f} m end_err={err[-1]:.3f} m  GTyaw={np.degrees(gyaw[-1]):.1f} est={np.degrees(yaw):.1f}")
