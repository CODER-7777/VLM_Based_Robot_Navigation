"""Add a translucent, cushion-conforming ambient contact patch to each GLB."""
from pathlib import Path
import json
import numpy as np
import trimesh
from PIL import Image
from analyze_contacts import ROOT, sample_seat


def add_shadow(item):
    key = item['object_id']
    seat = trimesh.load(ROOT/(key+'_seat.ply'), process=False)
    body_path = ROOT/item['asset']
    scene = trimesh.load(body_path, force='scene')
    q = item['rotation_xyzw']
    rot = trimesh.transformations.quaternion_matrix([q[3], *q[:3]])[:3, :3]
    t = np.asarray(item['translation_world'])
    parts = []
    # Use the fitted fabric's original x/z proportions for the soft shadow.
    allverts = []
    for node in scene.graph.nodes_geometry:
        m, name = scene.graph[node]
        v = scene.geometry[name].vertices @ m[:3, :3].T + m[:3, 3]
        allverts.append(v[v[:, 1] < .018])
    lower = np.concatenate(allverts)
    rx = max(.11, float(np.max(np.abs(lower[:, 0])))+.018)
    rz = max(.11, float(np.max(np.abs(lower[:, 2])))+.018)
    nx, nz = 61, 61
    xx = np.linspace(-rx, rx, nx)
    zz = np.linspace(-rz, rz, nz)
    lx, lz = np.meshgrid(xx, zz)
    local = np.column_stack([lx.ravel(), np.zeros(lx.size), lz.ravel()])
    world = local @ rot.T+t
    h, _ = sample_seat(seat, world[:, [0, 2]], -2.9)
    rho2 = (lx.ravel()/rx)**2+(lz.ravel()/rz)**2
    valid = np.isfinite(h) & (rho2 <= 1.25)
    grid = np.full(len(valid), -1, dtype=np.int64)
    grid[valid] = np.arange(valid.sum())
    ids = grid.reshape(nz, nx)
    faces = []
    for j in range(nz-1):
        for i in range(nx-1):
            a, b, c, d = ids[j, i], ids[j, i+1], ids[j+1, i+1], ids[j+1, i]
            if min(a,b,c,d) >= 0:
                faces.extend([[a,b,c],[a,c,d]])
    pts = world[valid].copy()
    pts[:, 1] = h[valid]+.0015
    local_pts = (pts-t) @ rot
    uv = np.column_stack([lx.ravel()[valid]/(2*rx)+.5,
                          .5-lz.ravel()[valid]/(2*rz)])
    alpha = np.clip(.38*np.exp(-3.6*rho2[valid]), 0, 1)
    tex = np.zeros((128,128,4), dtype=np.uint8)
    tex[:,:,:3] = 0
    # Texture V is flipped by glTF conventions; PIL image origin is top-left.
    uu, vv = np.meshgrid(np.linspace(0,1,128), np.linspace(0,1,128))
    tex[:,:,3] = np.uint8(np.clip(.38*np.exp(-3.6*((uu-.5)*2)**2-3.6*((vv-.5)*2)**2)*255,0,255))
    material = trimesh.visual.material.PBRMaterial(
        name='soft_cushion_contact_shadow', baseColorFactor=[255,255,255,255],
        baseColorTexture=Image.fromarray(tex, 'RGBA'), metallicFactor=0.,
        roughnessFactor=1., alphaMode='BLEND', doubleSided=True)
    shadow = trimesh.Trimesh(vertices=local_pts, faces=np.asarray(faces), process=False)
    shadow.visual = trimesh.visual.TextureVisuals(uv=uv, material=material)
    scene.add_geometry(shadow, node_name='soft_contact_shadow', geom_name='soft_contact_shadow')
    out = ROOT/'assets'/(key+'_render_with_shadow.glb')
    scene.export(out)
    item['collision_asset'] = item['asset']
    item['asset'] = 'assets/'+out.name
    item['placement_method'] += ' A faint alpha-blended contact patch lies 1.5 mm over the measured cushion triangles.'
    return {'object_id': key, 'shadow_grid_vertices': int(valid.sum()),
            'shadow_triangles': len(faces), 'ellipse_radii_m': [rx,rz],
            'opacity_center': .38, 'surface_offset_m': .0015,
            'shadow_is_surface_conforming': True}


def main():
    path = ROOT/'placement_request.json'
    request = json.loads(path.read_text())
    reports = [add_shadow(item) for item in request['placements']]
    path.write_text(json.dumps(request, indent=2)+'\n')
    (ROOT/'shadow_checks.json').write_text(json.dumps(reports, indent=2)+'\n')
    print(json.dumps(reports, indent=2), flush=True)


if __name__ == '__main__':
    main()
