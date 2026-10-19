"""Extract actual chair triangles and measure bag support against their surface."""
from pathlib import Path
import json
import struct
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent
BOUNDS = {
    'bag_brown_sofa': ([-1.5, -3.55, -11.65], [1.0, -2.25, -9.9]),
    'bag_pink_sofa': ([-1.9, -3.55, -17.9], [.1, -2.2, -16.0]),
}


def extract():
    file = ROOT / 'SN83YJsR3w2.glb'
    with file.open('rb') as stream:
        header = stream.read(20)
        size = struct.unpack_from('<I', header, 12)[0]
        doc = json.loads(stream.read(size))
    binary = np.memmap(file, dtype=np.uint8, mode='r', offset=28+size)
    types = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16,
             5125: np.uint32, 5126: np.float32}
    def accessor(index):
        a = doc['accessors'][index]
        view = doc['bufferViews'][a['bufferView']]
        count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
        dt = np.dtype(types[a['componentType']])
        return np.ndarray((a['count'], count), dtype=dt, buffer=binary,
                          offset=view.get('byteOffset', 0)+a.get('byteOffset', 0),
                          strides=(view.get('byteStride', dt.itemsize*count), dt.itemsize))
    pieces = {key: [] for key in BOUNDS}
    for node in doc['nodes']:
        assert not any(k in node for k in ['matrix', 'rotation', 'translation', 'scale'])
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            pos = accessor(primitive['attributes']['POSITION'])
            vertices = np.column_stack([pos[:, 0], pos[:, 2], -pos[:, 1]])
            faces = accessor(primitive['indices']).reshape(-1, 3)
            for key, (lo, hi) in BOUNDS.items():
                lo, hi = np.array(lo), np.array(hi)
                if np.any(vertices.max(axis=0) < lo) or np.any(vertices.min(axis=0) > hi):
                    continue
                triangles = vertices[faces]
                mask = np.all(triangles.max(axis=1) >= lo, axis=1) & np.all(triangles.min(axis=1) <= hi, axis=1)
                if mask.any():
                    mesh = trimesh.Trimesh(vertices=vertices, faces=faces[mask], process=False)
                    mesh.remove_unreferenced_vertices()
                    pieces[key].append(mesh)
    for key, parts in pieces.items():
        mesh = trimesh.util.concatenate(parts)
        mesh.export(ROOT / (key+'_chair.ply'))
        print(key, len(mesh.faces), 'chair triangles', flush=True)


def sample_seat(chair, xz, ceiling):
    origins = np.column_stack([xz[:, 0], np.full(len(xz), ceiling), xz[:, 1]])
    locations, rays, faces = chair.ray.intersects_location(origins, np.tile([0, -1, 0], (len(xz), 1)), multiple_hits=False)
    height = np.full(len(xz), np.nan)
    normals = np.full((len(xz), 3), np.nan)
    height[rays] = locations[:, 1]
    normals[rays] = chair.face_normals[faces]
    normals[normals[:, 1] < 0] *= -1
    return height, normals


def audit():
    previous = ROOT.parent / 'revision_02'
    scene = trimesh.load(previous/'assets/canvas_backpack_baked_clean_40cm.glb', force='scene')
    geometry = []
    for node in scene.graph.nodes_geometry:
        matrix, key = scene.graph[node]
        mesh = scene.geometry[key].copy()
        mesh.apply_transform(matrix)
        geometry.append(mesh)
    bag = trimesh.util.concatenate(geometry)
    result = json.loads((previous/'placed/placement_results.json').read_text())
    reports = []
    for item in result['objects']:
        key = item['object_id']
        chair = trimesh.load(ROOT/(key+'_chair.ply'), process=False)
        q = item['rotation_xyzw']
        rotation = trimesh.transformations.quaternion_matrix([q[3], *q[:3]])[:3, :3]
        points = bag.vertices @ rotation.T + item['object_translation']
        y_min = points[:, 1].min()
        # Chair seat rays start below armrest height to isolate the real cushion.
        ceiling = -3.015 if key == 'bag_brown_sofa' else -2.97
        bottom = points[points[:, 1] <= np.quantile(points[:, 1], .08)]
        heights, normals = sample_seat(chair, bottom[:, [0, 2]], ceiling)
        valid = np.isfinite(heights) & (heights > -3.35)
        distances = bottom[valid, 1]-heights[valid]
        report = {'object_id': key, 'sample_count': int(valid.sum()),
                  'bag_world_minimum_y': float(y_min),
                  'bottom_gap_quantiles_m': np.quantile(distances, [0, .1, .5, .9, 1]).tolist(),
                  'mean_local_seat_normal': np.mean(normals[valid], axis=0).tolist()}
        reports.append(report)
        print(json.dumps(report), flush=True)
    (ROOT/'previous_actual_mesh_contact_audit.json').write_text(json.dumps(reports, indent=2)+'\n')


if __name__ == '__main__':
    extract()
    audit()
