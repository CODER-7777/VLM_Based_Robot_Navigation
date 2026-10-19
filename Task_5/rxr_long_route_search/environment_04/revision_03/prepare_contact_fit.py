"""Fit a scanned soft bag's lower fabric to actual cushion triangles.

No physics settling is claimed. UVs and upper-body geometry are preserved;
the lower 12 cm are blended onto the measured support height field.
"""
from pathlib import Path
import json
import shutil
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from analyze_contacts import sample_seat

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent/'revision_02'


def main():
    (ROOT/'assets').mkdir(exist_ok=True)
    request = json.loads((OLD/'placement_request.json').read_text())
    reports = []
    for item in request['placements']:
        key = item['object_id']
        chair = trimesh.load(ROOT/(key+'_chair.ply'), process=False)
        centers = chair.triangles_center
        mask = ((chair.face_normals[:, 1] > .7) & (centers[:, 1] > -3.28)
                & (centers[:, 1] < (-3.04 if 'pink' in key else -3.03)))
        if 'brown' in key:
            mask &= (centers[:, 2] < -10.4) & (centers[:, 0] > -.85) & (centers[:, 0] < .2)
        seat = chair.submesh([mask], append=True)
        seat.export(ROOT/(key+'_seat.ply'))
        seat_center = np.average(centers[mask], axis=0, weights=chair.area_faces[mask])
        # Move only along the seat's lateral axis, retaining the backrest contact.
        q = item['rotation_xyzw']
        rotation = trimesh.transformations.quaternion_matrix([q[3], *q[:3]])[:3, :3]
        translation = np.array(item['translation_world'])
        a = np.radians(item['yaw_degrees'])
        side = np.array([np.cos(a), 0., -np.sin(a)])
        lateral_shift = side * ((seat_center-translation) @ side)
        translation += lateral_shift
        if 'pink' in key:
            # Clear the raised inner arm/back corner with the entire base rim.
            translation += .025*np.array([np.sin(a), 0., np.cos(a)])
        # Bottom-plane center starts at the real support, not the old high root.
        h, _ = sample_seat(seat, translation[[0, 2]][None, :], -2.9)
        assert np.isfinite(h[0]), (key, translation)
        translation[1] = h[0]+.0005
        scene = trimesh.load(OLD/'assets/canvas_backpack_baked_clean_40cm.glb', force='scene')
        fitted = trimesh.Scene()
        all_base, changes, missed, normals = [], [], 0, []
        for node in scene.graph.nodes_geometry:
            transform, name = scene.graph[node]
            mesh = scene.geometry[name].copy()
            mesh.apply_transform(transform)
            local = mesh.vertices.copy()
            world = local @ rotation.T + translation
            lower = local[:, 1] < .12
            heights, normal = sample_seat(seat, world[lower][:, [0, 2]], -2.9)
            missing = ~np.isfinite(heights)
            missed += int(missing.sum())
            # Fail on any unsupported base vertex; do not hide an armrest collision.
            assert not np.any(missing & (local[lower, 1] < .012)), (key, 'unsupported base')
            if missing.any():
                # Only upper transition fabric may overhang; extend its nearest
                # actual seat triangle plane for a smooth blend.
                tree = cKDTree(seat.triangles_center[:, [0, 2]])
                _, nearest = tree.query(world[lower][missing][:, [0, 2]])
                normal[missing] = seat.face_normals[nearest]
                delta = world[lower][missing]-seat.triangles_center[nearest]
                heights[missing] = world[lower][missing, 1]-(delta*normal[missing]).sum(axis=1)/normal[missing, 1]
            base_normal = rotation[:, 1]
            plane_y = translation[1] - ((world[lower, 0]-translation[0])*base_normal[0]
                                      +(world[lower, 2]-translation[2])*base_normal[2])/base_normal[1]
            t = np.clip((local[lower, 1]-.008)/.112, 0., 1.)
            blend = 1-t*t*(3-2*t)
            displacement = (heights+.0005-plane_y)*blend
            # Compress the uneven scanned lower hem into a soft resting base.
            # The map is monotone, reaches identity at 8 cm and leaves the top alone.
            hem_t = np.clip(local[lower, 1]/.08, 0., 1.)
            hem_scale = .1+.9*hem_t*hem_t*(3-2*hem_t)
            displacement += local[lower, 1]*(hem_scale-1)/base_normal[1]
            world[lower, 1] += displacement
            changes.extend(displacement.tolist())
            mesh.vertices = (world-translation) @ rotation
            # Recompute geometric normals after the soft fabric deformation.
            mesh._cache.clear()
            _ = mesh.vertex_normals
            fitted.add_geometry(mesh, node_name=node, geom_name=name)
            base = local[:, 1] < .004
            all_base.append(world[base])
            normals.extend(normal[local[lower, 1] < .004].tolist())
        asset = 'assets/'+key+'_cushion_fitted.glb'
        fitted.export(ROOT/asset)
        base = np.concatenate(all_base)
        heights, _ = sample_seat(seat, base[:, [0, 2]], -2.9)
        gap = base[:, 1]-heights
        assert np.isfinite(gap).all()
        assert gap.min() > -.001 and gap.max() < .007, (key, gap.min(), gap.max())
        item['asset'] = asset
        item['translation_world'] = translation.tolist()
        item['support_world'] = [float(translation[0]), float(h[0]), float(translation[2])]
        item['placement_method'] = 'Actual cushion triangles; laterally centered; lower 12 cm of soft fabric conformed to triangle heights while preserving the upper bag lean and photo UVs.'
        item['support_measurement'] = 'Exact source scene triangles transformed from MP3D Z-up to Habitat Y-up.'
        report = dict(object_id=key, seat_triangles=int(mask.sum()),
                      seat_area_m2=float(seat.area), lateral_shift_m=lateral_shift.tolist(),
                      base_vertex_count=len(base), base_gap_min_max_m=[float(gap.min()), float(gap.max())],
                      base_gap_median_m=float(np.median(gap)),
                      mean_contact_normal=np.mean(normals, axis=0).tolist(),
                      lower_fabric_vertical_deformation_min_max_m=[float(min(changes)), float(max(changes))],
                      transition_vertices_outside_seat_patch=missed,
                      method='Mesh height-field fit; no dynamics/physics stability claim.')
        reports.append(report)
        print(json.dumps(report), flush=True)
    request['asset'] = request['placements'][0]['asset']
    request['status'] = 'revision 3 actual cushion contact fit; pending rendered inspection'
    request['note'] = 'Individual photo-textured 3D meshes with a soft lower-fabric correction; source scene unchanged.'
    (ROOT/'placement_request.json').write_text(json.dumps(request, indent=2)+'\n')
    (ROOT/'contact_checks.json').write_text(json.dumps(reports, indent=2)+'\n')
    for name in ['route_source.json', 'guide_positions.json', 'model_sources.json']:
        shutil.copy2(OLD/name, ROOT/name)


if __name__ == '__main__':
    main()
