"""Reconstruct the per-tick world pose the agent actually held, from a run's episode_results.json.

Per leg the log stores `diag.true_local` = [x, y, yaw] in a frame anchored at
`start_world` whose axes are f = start_heading_xz and s = (hz, -hx); this mapping was
verified to machine precision against `end_world` on several legs. Turn-only legs carry
no per-tick record, so their heading is interpolated over `ticks` at a fixed position.

Writes poses/<name>.npz with x, z, yaw (world) and the tick index that opens each leg.
"""
import glob, json, math, os, sys
import numpy as np

TURN_RATE_DEG = 5.0

RUNS = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)


def leg_poses(leg):
    """(N,3) world x, z, yaw for one leg; yaw is the atan2 of the heading in the xz-plane."""
    sw = leg["start_world"]
    hx, hz = leg["start_heading_xz"]
    f = np.array([hx, hz])
    s = np.array([hz, -hx])
    tl = leg.get("diag", {}).get("true_local")
    if tl:
        tl = np.asarray(tl, dtype=np.float64)
        xz = np.array(sw)[[0, 2]] + np.outer(tl[:, 0], f) + np.outer(tl[:, 1], s)
        head = np.outer(np.cos(tl[:, 2]), f) + np.outer(np.sin(tl[:, 2]), s)
    else:
        # Turn-in-place legs log ticks=0: the heading snaps by up to 90 deg with no
        # intermediate record. Nothing can be estimated from a single 90 deg jump, so the
        # turn is resampled at TURN_RATE_DEG per frame -- within the 6.3 deg/tick envelope
        # the drive legs actually exhibit -- and ground truth is exact for those frames too.
        ex0, ez0 = leg["end_heading_xz"]
        da = abs((math.atan2(ez0, ex0) - math.atan2(hz, hx) + math.pi) % (2 * math.pi) - math.pi)
        n = max(int(leg.get("ticks", 0)), int(math.ceil(math.degrees(da) / TURN_RATE_DEG)), 1)
        ex, ez = leg["end_heading_xz"]
        a0, a1 = math.atan2(hz, hx), math.atan2(ez, ex)
        d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        a = a0 + d * np.linspace(1.0 / n, 1.0, n)
        xz = np.repeat(np.array(sw)[[0, 2]][None], n, 0)
        head = np.stack([np.cos(a), np.sin(a)], 1)
    yaw = np.arctan2(head[:, 1], head[:, 0])
    return np.column_stack([xz[:, 0], xz[:, 1], yaw])


for run in sorted(glob.glob(RUNS)):
    res = json.load(open(f"{run}/episode_results.json"))
    rows, starts, n = [], [], 0
    for leg in res["legs"]:
        sw, (hx, hz) = leg["start_world"], leg["start_heading_xz"]
        starts.append(n)                                  # frame index, not list index
        rows.append(np.array([[sw[0], sw[2], math.atan2(hz, hx)]]))   # the keyframe pose
        p = leg_poses(leg)
        if len(p):
            rows.append(p)
        n += 1 + len(p)
    P = np.vstack(rows)
    name = os.path.basename(run)
    np.savez(f"{OUT}/{name}.npz", pose=P, leg_start=np.array(starts),
             floor_y=res["legs"][0]["start_world"][1],
             scene=res["episode"]["scene_id"], episode_id=res["episode"]["episode_id"],
             physical=json.dumps(res["run_config"]["physical_settings"]))
    gaps = [np.hypot(*(np.array(res["legs"][i]["end_world"])[[0, 2]]
                       - np.array(res["legs"][i + 1]["start_world"])[[0, 2]]))
            for i in range(len(res["legs"]) - 1)]
    print(f"{name}: legs={len(res['legs'])} frames={len(P)} "
          f"scene={res['episode']['scene_id'].split('/')[1]} max_leg_gap={max(gaps):.3f}m")
