"""Validate downloaded GLBs and render the actual JanSport geometry/texture.

CPU orthographic rasterization; no reconstructed or AI-generated details.
"""
from pathlib import Path
import hashlib
import io
import json
import struct
import numpy as np
import trimesh
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent


def inspect(name):
    data = (ROOT / (name + '.glb')).read_bytes()
    magic, version, size = struct.unpack_from('<4sII', data)
    assert magic == b'glTF' and version == 2 and size == len(data)
    length, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    doc = json.loads(data[20:20 + length])
    bin_start = 20 + length
    bin_length, bin_kind = struct.unpack_from('<II', data, bin_start)
    assert bin_kind == 0x004E4942
    binary = data[bin_start + 8:bin_start + 8 + bin_length]
    assert all('uri' not in b for b in doc.get('buffers', []))
    images = []
    for item in doc.get('images', []):
        assert 'bufferView' in item, 'External texture dependency'
        view = doc['bufferViews'][item['bufferView']]
        start = view.get('byteOffset', 0)
        picture = Image.open(io.BytesIO(binary[start:start + view['byteLength']]))
        picture.load()
        images.append({'resolution': list(picture.size), 'format': picture.format})
    scene = trimesh.load(ROOT / (name + '.glb'), force='scene')
    return {
        'file': name + '.glb', 'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(), 'gltf_version': version,
        'meshes': len(doc.get('meshes', [])),
        'triangles': sum(len(g.faces) for g in scene.geometry.values()),
        'materials': len(doc.get('materials', [])),
        'embedded_images': images, 'self_contained': True,
        'bounds': scene.bounds.tolist(), 'extents': scene.extents.tolist(),
        'required_extensions': doc.get('extensionsRequired', []),
        'asset_metadata': doc['asset'],
        'download_url': 'https://sceneview.github.io/models/platforms/' + name + '.glb',
    }


def render(scene, angle, resolution=700):
    canvas = np.full((resolution, resolution, 3), 242, dtype=np.uint8)
    zbuffer = np.full((resolution, resolution), -np.inf)
    theta = np.deg2rad(angle)
    rotation = np.array([[np.cos(theta), 0, np.sin(theta)],
                         [0, 1, 0], [-np.sin(theta), 0, np.cos(theta)]])
    # Small downward viewing tilt. The asset has Y up.
    tilt = np.deg2rad(8)
    rotation = np.array([[1, 0, 0], [0, np.cos(tilt), -np.sin(tilt)],
                         [0, np.sin(tilt), np.cos(tilt)]]) @ rotation
    scale = resolution * 0.78 / max(scene.extents)
    for node in scene.graph.nodes_geometry:
        transform, key = scene.graph[node]
        mesh = scene.geometry[key]
        world = trimesh.transform_points(mesh.vertices, transform)
        points = (world - scene.bounds.mean(axis=0)) @ rotation.T
        xy = points[:, :2] * np.array([scale, -scale]) + resolution / 2
        uv = mesh.visual.uv
        texture = np.asarray(mesh.visual.material.baseColorTexture.convert('RGB'))
        height, width = texture.shape[:2]
        for face in mesh.faces:
            triangle = xy[face]
            lo = np.maximum(np.floor(triangle.min(axis=0)).astype(int), 0)
            hi = np.minimum(np.ceil(triangle.max(axis=0)).astype(int), resolution - 1)
            if np.any(hi < lo):
                continue
            a, b, c = triangle
            denominator = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
            if abs(denominator) < 1e-10:
                continue
            xx, yy = np.meshgrid(np.arange(lo[0], hi[0]+1)+0.5,
                                 np.arange(lo[1], hi[1]+1)+0.5)
            wa = ((b[1]-c[1])*(xx-c[0]) + (c[0]-b[0])*(yy-c[1])) / denominator
            wb = ((c[1]-a[1])*(xx-c[0]) + (a[0]-c[0])*(yy-c[1])) / denominator
            wc = 1-wa-wb
            depth = wa*points[face[0], 2] + wb*points[face[1], 2] + wc*points[face[2], 2]
            target = np.s_[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
            mask = (wa >= -1e-7) & (wb >= -1e-7) & (wc >= -1e-7) & (depth > zbuffer[target])
            if not mask.any():
                continue
            weights = np.stack([wa[mask], wb[mask], wc[mask]], axis=1)
            texcoord = weights @ uv[face]
            tx = np.clip(np.rint(texcoord[:, 0]*(width-1)).astype(int), 0, width-1)
            ty = np.clip(np.rint((1-texcoord[:, 1])*(height-1)).astype(int), 0, height-1)
            canvas[target][mask] = texture[ty, tx]
            zbuffer[target][mask] = depth[mask]
    return Image.fromarray(canvas)


if __name__ == '__main__':
    report = {name: inspect(name) for name in ['jansport_backpack', 'school_backpack']}
    (ROOT / 'model_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    scene = trimesh.load(ROOT / 'jansport_backpack.glb', force='scene')
    overview = Image.new('RGB', (1400, 1500), 'white')
    for i, angle in enumerate([0, 90, 180, 270]):
        preview = render(scene, angle)
        preview.save(ROOT / f'jansport_view_{angle:03d}.jpg', quality=95)
        x, y = (i % 2)*700, (i//2)*750
        overview.paste(preview, (x, y))
        ImageDraw.Draw(overview).text((x+20, y+715), f'Asset rotation: {angle} degrees', fill='black')
    overview.save(ROOT / 'jansport_four_views.jpg', quality=95)
    print(json.dumps(report, indent=2))
