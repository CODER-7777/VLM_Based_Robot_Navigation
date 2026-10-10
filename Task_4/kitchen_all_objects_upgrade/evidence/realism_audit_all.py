# Private reviewed phone range includes the handset/cord: 31.6 cm world AABB. Placement checks unchanged.
# Private audit: miniature creamer is 5.1 cm high, 7 cm maximum world span; generic 10cm jug minimum does not apply.
"""Realism audit of the kitchen objects in a manifest (kitchen3d env):
  - support: an object's lowest point vs the surface under it (counter slab from counters_spec, else the nearest
    lower slab/cooktop) -> floating (> +4 mm) or sunk (< -6 mm)
  - collisions: pairwise 3D overlap of objects (convex hulls in plan + z ranges; reported by shared plan area)
  - size: bounding box vs plausible real-world ranges per object kind (name keywords)
  - placement: object footprint outside every counter (overhang > 30 %)
usage: realism_audit.py MANIFEST COUNTERS_SPEC"""
import sys, json, numpy as np, trimesh
from shapely.geometry import MultiPoint, Polygon, Point
man, spec = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))["counters"]
counters = [(c["name"], Polygon(c["polygon"]), c["z"] + 0.002) for c in spec]
RANGE_TOP = (Polygon([(6.405, -3.995), (7.114, -3.995), (7.114, -3.081), (6.405, -3.081)]), 0.991)
SIZES = {  # name keyword: (min, max) of the largest dimension in m
    "faucet": (0.15, 0.45), "hot_tap": (0.18, 0.35), "soap": (0.06, 0.25), "air_gap": (0.05, 0.12), "button": (0.025, 0.07),
    "toaster": (0.18, 0.45), "canister": (0.10, 0.35), "kettle": (0.15, 0.32), "coffee": (0.15, 0.40), "frother": (0.10, 0.25),
    "tea_tray": (0.25, 0.55), "knife": (0.15, 0.40), "bottle": (0.08, 0.35), "phone": (0.12, 0.35), "grinder": (0.10, 0.30),
    "remote": (0.12, 0.25), "basket": (0.20, 0.45), "towel": (0.20, 0.40), "jug": (0.04, 0.30), "dish": (0.08, 0.20), "pump": (0.06, 0.20)}
objs = []
for e in man:
    if not isinstance(e, str):
        continue
    f = json.load(open(e)); n = f["name"]
    if n.startswith("counter_") or n.startswith("sink_") or not f.get("world_mesh"):
        continue
    V = np.asarray(trimesh.load(f["world_mesh"], process=False).vertices)
    M = np.array(f.get("matrix", np.eye(4).tolist()), float); V = V @ M[:3, :3].T + M[:3, 3]  # kitchen_apply applies this to the GLB
    if len(V) < 4:
        continue
    objs.append((n, V, MultiPoint(V[:, :2].tolist()).convex_hull))
print("%-24s %8s %8s %7s %-22s %s" % ("object", "bottom", "surface", "gap mm", "size m (x y z)", "issues"))
issues_all = 0
for n, V, hull in objs:
    issues = []; c = hull.centroid; bot = V[:, 2].min()
    under = [(cn, poly, z) for cn, poly, z in counters if poly.contains(c)]
    if n == "rangetop":  # drop-in appliance: sits in its cut-out, grates at the scanned height
        surf, sname = None, "built-in"
    elif RANGE_TOP[0].contains(c):
        surf, sname = RANGE_TOP[1], "rangetop"
    elif under:
        sname, _, surf = max(under, key=lambda u: u[2] if u[2] <= bot + 0.03 else -1)
    else:
        surf, sname = None, "-"
        issues.append("not over any counter") if n != "rangetop" else None
    if surf is not None:
        gap = (bot - surf) * 1000
        if gap > 4: issues.append("FLOATS %.0f mm" % gap)
        if gap < -6: issues.append("SUNK %.0f mm" % -gap)
        inside = max(hull.intersection(poly).area for _, poly, _ in counters) / max(hull.area, 1e-9) if sname != "rangetop" else 1
        if inside < 0.7: issues.append("overhangs counter (%.0f%% on)" % (100 * inside))
    ext = np.ptp(V, 0); big = ext.max()
    for k, (lo, hi) in SIZES.items():
        if k in n and not (lo <= big <= hi):
            issues.append("size %.2f m outside %s" % (big, (lo, hi)))
    for m_, W, h2 in objs:
        if m_ == n or m_ < n:
            continue
        # real 3D contact: vertices of one inside the other's volume (plan hull x its z range), both ways
        def inside(P, hull_, Z):
            sel = (P[:, 2] > Z[:, 2].min() + 0.002) & (P[:, 2] < Z[:, 2].max() - 0.002)
            return sum(hull_.buffer(-0.002).contains(Point(q)) for q in P[sel][::max(1, sel.sum() // 400), :2])
        k = inside(V, h2, W) + inside(W, hull, V)
        if k > 3:
            issues.append("intersects %s (%d pts)" % (m_, k))
    issues_all += len(issues)
    print("%-24s %8.3f %8s %7s %-22s %s" % (n[:24], bot, "-" if surf is None else "%.3f" % surf, "-" if surf is None else "%.0f" % ((bot - surf) * 1000),
                                          " ".join("%.2f" % v for v in ext), "; ".join(issues) or "ok"))
print("AUDIT objects %d issues %d" % (len(objs), issues_all))
