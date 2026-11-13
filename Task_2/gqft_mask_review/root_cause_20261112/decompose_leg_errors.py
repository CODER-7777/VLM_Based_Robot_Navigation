import json, glob, numpy as np, collections, math, sys
root = sys.argv[1]
M = ['yaw_local_reference', 'solver_residual', 'solver_learned_weights']
up = np.array([0, -math.cos(math.radians(30)), -math.sin(math.radians(30))])
legs = []
for f in sorted(glob.glob(root + '/ep*/predictions.json')):
    P = json.load(open(f))
    for s in P['segments']:
        if s['id'] == 'full':
            continue
        ref = s['reference']; g = np.array(ref['ground_m']); gy = np.array(ref['yaw_rad'])
        d3 = np.array(ref['displacement_m'])
        row = {'ep': P['episode'], 'leg': s['id'], 'n': len(g) - 1,
               'gt_len': float(np.linalg.norm(np.diff(g, axis=0), axis=1).sum()),
               'gt_turn_deg': float(np.degrees(np.abs(np.angle(np.exp(1j * np.diff(gy)))).sum())),
               'gt_vertical_m': float(np.abs(d3 @ up).max())}
        sg = np.linalg.norm(np.diff(g, axis=0), axis=1)
        tg = np.degrees(np.abs(np.angle(np.exp(1j * np.diff(gy)))))
        kind = np.where((sg < .01) & (tg > 1), 'turn_in_place', np.where(sg < .005, 'still', np.where(sg >= .06, 'fast', 'normal')))
        row['kinds'] = collections.Counter(kind)
        for m in M:
            p = s['predictions'][m]; pg = np.array(p['ground_m']); py = np.array(p['yaw_rad'])
            sp = np.linalg.norm(np.diff(pg, axis=0), axis=1)
            # per-step translation error expressed in each step's own frame is hard; use step-length + heading
            row[m] = {'err': p['metrics']['mean_ground_error_m'], 'end': p['metrics']['endpoint_ground_error_m'],
                      'len': float(sp.sum()),
                      'yaw_end_err_deg': float(np.degrees(np.angle(np.exp(1j * (py[-1] - gy[-1]))))),
                      'turn_deg': float(np.degrees(np.abs(np.angle(np.exp(1j * np.diff(py)))).sum())),
                      'stall_steps': int(((sp < .002) & (sg > .02)).sum()),
                      'len_err_by_kind': {k: float((sp - sg)[kind == k].sum()) for k in set(kind)},
                      'yaw_err_by_kind': {k: float(np.degrees(np.abs(np.angle(np.exp(1j * (np.diff(py) - np.diff(gy)))))[kind == k]).sum()) for k in set(kind)}}
        legs.append(row)
json.dump(legs, open(sys.argv[2], 'w'), default=lambda o: dict(o))
print('legs', len(legs))
tot = collections.Counter()
for r in legs: tot.update(r['kinds'])
print('GT step types over all legs:', dict(tot))
print('GT legs with any vertical motion > 5 cm:', sum(r['gt_vertical_m'] > .05 for r in legs))
for m in M:
    ratio = np.array([r[m]['len'] / r['gt_len'] for r in legs if r['gt_len'] > .3])
    yawe = np.array([abs(r[m]['yaw_end_err_deg']) for r in legs])
    stalls = sum(r[m]['stall_steps'] for r in legs)
    lk = collections.Counter(); yk = collections.Counter()
    for r in legs:
        lk.update(r[m]['len_err_by_kind']); yk.update(r[m]['yaw_err_by_kind'])
    print(f"\n{m}")
    print(f"  path length pred/GT: median {np.median(ratio):.2f}, p10 {np.percentile(ratio,10):.2f}, p90 {np.percentile(ratio,90):.2f}")
    print(f"  end heading error deg: median {np.median(yawe):.1f}, mean {yawe.mean():.1f}, legs >20deg: {(yawe>20).sum()}")
    print(f"  solver stalls (pred step<0.2cm while GT>2cm): {stalls}")
    print('  summed length error (m) by GT step type:', {k: round(v, 2) for k, v in lk.items()})
    print('  yaw error deg per step by type:', {k: round(yk[k] / max(tot[k], 1), 2) for k in yk})
