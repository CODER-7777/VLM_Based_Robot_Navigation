"""Probe real sofa coordinates, then render two separate static backpack objects.

Run with the server's Habitat Python. Probe and place are deliberately separate:
inspect probe RGB/depth and enter measured support_world points before placement.
This script never edits original scene assets, annotations, or collector sessions.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def rotation_y(degrees):
    a = math.radians(degrees)
    return np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0],
                     [-math.sin(a), 0, math.cos(a)]])


def unproject(x, y, depth, eye, heading, width=512, height=512, hfov=90):
    """Habitat axial depth, pixel centers, camera -Z forward, world Y up."""
    if not np.isfinite(depth) or depth <= 0:
        raise ValueError('Missing/invalid depth at the selected cushion pixel')
    focal = width / (2 * math.tan(math.radians(hfov)/2))
    local = np.array([(x+.5-width/2)*depth/focal,
                      -(y+.5-height/2)*depth/focal, -depth])
    return np.asarray(eye) + rotation_y(-heading) @ local


def dump(path, value):
    def native(item):
        if isinstance(item, np.ndarray):
            return item.tolist()
        if isinstance(item, np.generic):
            return item.item()
        raise TypeError(type(item).__name__)
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=native)+'\n')


def run(args):
    import habitat_sim as hs
    import magnum as mn
    from habitat_sim.utils.common import quat_from_angle_axis

    request = json.loads(args.request.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    if not args.scene.is_file():
        raise FileNotFoundError(args.scene)
    cfg = hs.SimulatorConfiguration()
    cfg.scene_id = str(args.scene.resolve())
    cfg.gpu_device_id = args.gpu
    cfg.enable_physics = True
    sensors = []
    for name, kind in [('rgb', hs.SensorType.COLOR), ('depth', hs.SensorType.DEPTH)]:
        spec = hs.SensorSpec()
        spec.uuid = name
        spec.sensor_type = kind
        spec.resolution = request['resolution']
        spec.position = [0, 0, 0]
        spec.parameters['hfov'] = str(request['hfov_degrees'])
        sensors.append(spec)
    detail = hs.SensorSpec()
    detail.uuid = 'rgb_detail'
    detail.sensor_type = hs.SensorType.COLOR
    detail.resolution = [1024, 1024]
    detail.position = [0, 0, 0]
    detail.parameters['hfov'] = '65'
    sensors.append(detail)
    agent_cfg = hs.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = sensors
    sim = hs.Simulator(hs.Configuration(cfg, [agent_cfg]))
    try:
        agent = sim.initialize_agent(0)
        def capture(eye, heading, label, target=None):
            state = hs.AgentState()
            state.position = np.asarray(eye, dtype=np.float32)
            if target is None:
                state.rotation = quat_from_angle_axis(-math.radians(heading), np.array([0, 1, 0]))
            else:
                # Camera look-at transformation supplies a world rotation.
                matrix = mn.Matrix4.look_at(mn.Vector3(*eye), mn.Vector3(*target), mn.Vector3.y_axis())
                quaternion = mn.Quaternion.from_matrix(matrix.rotation())
                from habitat_sim.utils.common import quat_from_magnum
                state.rotation = quat_from_magnum(quaternion)
            agent.set_state(state, reset_sensors=True)
            obs = sim.get_sensor_observations()
            rgb = np.asarray(obs['rgb'])[:, :, :3]
            depth = np.asarray(obs['depth'])
            Image.fromarray(rgb).save(args.out/(label+'.png'))
            if label.endswith(('_close', '_side')):
                Image.fromarray(np.asarray(obs['rgb_detail'])[:, :, :3]).save(args.out/(label+'_detail.png'))
            np.save(args.out/(label+'_depth.npy'), depth)
            return rgb, depth

        baseline = {}
        candidates = []
        for heading in [0, 90, 180, 270]:
            rgb, depth = capture(request['camera_eye_habitat'], heading, f'before_{heading:03d}')
            baseline[heading] = rgb
            marked = Image.fromarray(rgb)
            draw = ImageDraw.Draw(marked)
            for item in request['placements']:
                if item['heading_degrees'] != heading:
                    continue
                x, y = item['support_pixel_xy']
                point = unproject(x, y, float(depth[y, x]), request['camera_eye_habitat'],
                                  heading, rgb.shape[1], rgb.shape[0], request['hfov_degrees'])
                neighbors = []
                for dy in [-3, 0, 3]:
                    for dx in [-3, 0, 3]:
                        d = float(depth[y+dy, x+dx])
                        if np.isfinite(d) and d > 0:
                            neighbors.append(unproject(x+dx, y+dy, d, request['camera_eye_habitat'], heading).tolist())
                candidate = dict(item, proposed_support_world=point.tolist(),
                                 depth_m=float(depth[y, x]), neighboring_surface_points=neighbors,
                                 verified=False)
                # Ray query checks rendered depth against actual collision geometry.
                direction = point-np.asarray(request['camera_eye_habitat'])
                result = sim.cast_ray(hs.geo.Ray(mn.Vector3(*request['camera_eye_habitat']),
                                               mn.Vector3(*(direction/np.linalg.norm(direction)))))
                candidate['ray_hits'] = [
                    {'point': list(h.point), 'normal': list(h.normal),
                     'distance': float(h.ray_distance), 'object_id': int(h.object_id)}
                    for h in result.hits[:4]]
                candidates.append(candidate)
                draw.ellipse((x-7, y-7, x+7, y+7), outline='yellow', width=2)
                draw.text((max(2, x-120), max(2, y-24)), item['object_id'], fill='yellow')
            marked.save(args.out/f'probe_marked_{heading:03d}.jpg', quality=95)
        dump(args.out/'support_candidates.json', candidates)
        if args.mode == 'probe':
            cameras = []
            for item in request['placements']:
                support = np.asarray(item['support_world'])
                offset = [-1.5, 1.0, .1] if item['heading_degrees'] == 90 else [.1, 1.0, 1.7]
                eye = support + np.array(offset)
                target = support + np.array([0, .2, 0])
                capture(eye, 0, item['object_id']+'_empty_close', target=target)
                node = agent.scene_node
                cameras.append({'object_id': item['object_id'], 'eye': eye.tolist(),
                                'target': target.tolist(),
                                'camera_to_world': np.asarray(node.absolute_transformation()).tolist()})
            dump(args.out/'close_camera_poses.json', cameras)
            extra = []
            for name, eye, target in [
                ('brown_center_front', [-2.0, -1.9, -10.8], [-.1, -2.9, -10.8]),
                ('brown_overhead', [-.1, -1.2, -10.8], [-.1, -3.2, -10.81]),
                ('brown_other_side', [.8, -1.9, -9.3], [-.2, -3.0, -10.8]),
            ]:
                capture(eye, 0, name, target=target)
                extra.append({'name': name, 'eye': eye, 'target': target,
                              'camera_to_world': np.asarray(agent.scene_node.absolute_transformation()).tolist()})
            dump(args.out/'extra_camera_poses.json', extra)
            print('Probe complete. Inspect support_candidates.json and marked images before entering support_world.', flush=True)
            return

        asset = (args.request.parent/request['asset']).resolve()
        if not asset.is_file():
            raise FileNotFoundError(asset)
        manager = sim.get_object_template_manager()
        template = manager.create_new_template('environment04_schoolbag', False)
        template.render_asset_handle = str(asset)
        template.collision_asset_handle = str(asset)
        template.scale = mn.Vector3(1.0)
        template.orient_up = mn.Vector3(0, 1, 0)
        template.orient_front = mn.Vector3(0, 0, -1)
        template.compute_COM_from_shape = False
        template.com = mn.Vector3(0.0)
        # Matterport room colors are baked into textures. Preserve the scanned
        # bag's texture colors instead of applying the legacy default dark light.
        if hasattr(template, 'requires_lighting'):
            template.requires_lighting = request.get('lighting') == 'soft'
        if hasattr(template, 'force_flat_shading'):
            template.force_flat_shading = True
        manager.register_template(template, 'environment04_schoolbag')
        light_key = hs.gfx.NO_LIGHT_KEY
        if request.get('lighting') == 'soft':
            light_key = 'schoolbag_soft_fill'
            sim.set_light_setup([
                hs.gfx.LightInfo(mn.Vector4(.2, 1.0, .5, 0), mn.Color3(.65, .65, .65), hs.gfx.LightPositionModel.GLOBAL),
                hs.gfx.LightInfo(mn.Vector4(0, 0, 1, 0), mn.Color3(.35, .35, .35), hs.gfx.LightPositionModel.CAMERA)], light_key)
        objects = sim.get_rigid_object_manager() if hasattr(sim, 'get_rigid_object_manager') else None
        placements = []
        for item in request['placements']:
            support = item.get('support_world')
            if support is None or len(support) != 3 or not np.isfinite(support).all():
                raise ValueError('Enter a checked support_world for '+item['object_id'])
            rotation = mn.Quaternion.rotation(mn.Rad(math.radians(item['yaw_degrees'])), mn.Vector3.y_axis())
            if 'rotation_xyzw' in item:
                q = item['rotation_xyzw']
                rotation = mn.Quaternion(mn.Vector3(*q[:3]), q[3])
            if objects is not None:
                obj = objects.add_object_by_template_handle('environment04_schoolbag', light_setup_key=light_key)
                if obj is None:
                    raise RuntimeError('Backpack object instantiation failed')
                object_id = obj.object_id
                obj.motion_type = hs.physics.MotionType.KINEMATIC
                obj.semantic_id = item['semantic_id']
                obj.rotation = rotation
                obj.translation = mn.Vector3(*support)
                node = obj.root_scene_node
            else:
                # The existing navila server uses Habitat's legacy object API.
                object_id = sim.add_object_by_handle('environment04_schoolbag', light_setup_key=light_key)
                if object_id < 0:
                    raise RuntimeError('Legacy backpack object instantiation failed')
                sim.set_object_motion_type(hs.physics.MotionType.KINEMATIC, object_id)
                sim.set_object_semantic_id(item['semantic_id'], object_id)
                sim.set_rotation(rotation, object_id)
                sim.set_translation(mn.Vector3(*support), object_id)
                node = sim.get_object_scene_node(object_id)
            # Correct for any importer COM offset using the rendered scene-node bounds.
            if hasattr(node, 'compute_cumulative_bb'):
                node.compute_cumulative_bb()
            bb = node.cumulative_bb
            lo, hi = np.array(bb.min), np.array(bb.max)
            print('OBJECT_BOUNDS', item['object_id'], 'min', lo, 'max', hi, 'translation', support, flush=True)
            if not np.isfinite(lo).all() or not np.isfinite(hi).all() or np.any(hi <= lo):
                raise RuntimeError('Backpack has missing/nonfinite rendered bounds')
            local_base = mn.Vector3(float((lo[0]+hi[0])/2), float(lo[1]), float((lo[2]+hi[2])/2))
            world_base = np.array(node.absolute_transformation().transform_point(local_base))
            translation = mn.Vector3(*(np.asarray(support)+np.asarray(support)-world_base))
            if 'translation_world' in item:
                translation = mn.Vector3(*item['translation_world'])
            if objects is not None:
                obj.translation = translation
                actual_translation = list(obj.translation)
                obj.motion_type = hs.physics.MotionType.STATIC
            else:
                sim.set_translation(translation, object_id)
                actual_translation = list(sim.get_translation(object_id))
                sim.set_object_motion_type(hs.physics.MotionType.STATIC, object_id)
            if not np.allclose(actual_translation, translation, atol=1e-4):
                raise RuntimeError('Simulator did not apply the backpack translation')
            placements.append(dict(item, simulator_object_id=object_id,
                                   object_translation=actual_translation,
                                   rotation_xyzw=list(rotation.vector)+[float(rotation.scalar)],
                                   support_correction_m=(np.asarray(support)-world_base).tolist(),
                                   used_geometry_contact_fit='translation_world' in item))
            print('OBJECT_PLACED', json.dumps(placements[-1]), flush=True)

        dump(args.out/'object_transforms.json', placements)

        changes = []
        for heading in [0, 90, 180, 270]:
            rgb, _ = capture(request['camera_eye_habitat'], heading, f'after_{heading:03d}')
            difference = np.max(np.abs(rgb.astype(int)-baseline[heading].astype(int)), axis=2)
            changes.append({'heading': heading, 'changed_pixels_gt10': int((difference > 10).sum())})
        navigation = []
        route = json.loads(args.request.with_name('route_source.json').read_text())
        guide = json.loads(args.request.with_name('guide_positions.json').read_text())
        pf = sim.pathfinder
        if not pf.is_loaded:
            raise RuntimeError('The original scene navmesh is unavailable')
        # Camera centers are above the floor. Snap after subtracting the collector
        # camera height and retain the snap displacements for inspection.
        snapped = []
        for position in guide['camera_positions_habitat']:
            query = np.asarray(position)-np.array([0, 1.25, 0])
            point = np.asarray(pf.snap_point(query))
            if not np.isfinite(point).all():
                raise RuntimeError('Failed to snap an original guide viewpoint')
            snapped.append(point)
        def path_to(a, b):
            path = hs.ShortestPath()
            path.requested_start = a
            path.requested_end = b
            if not pf.find_path(path):
                return None
            return {'distance_m': float(path.geodesic_distance),
                    'points': [list(p) for p in path.points]}
        segment_lengths = []
        for a, b in zip(snapped, snapped[1:]):
            segment = path_to(a, b)
            segment_lengths.append(None if segment is None else segment['distance_m'])
        guide_nav_length = None if any(d is None for d in segment_lengths) else sum(segment_lengths)
        for item in placements:
            support = np.asarray(item['support_world'])
            front = np.array([math.sin(math.radians(item['yaw_degrees'])), 0,
                              math.cos(math.radians(item['yaw_degrees']))])
            choices = []
            for radius in [0.7, 1.0, 1.3, 1.6]:
                for angle in np.linspace(0, 2*math.pi, 24, endpoint=False):
                    query = support + np.array([radius*math.cos(angle), -0.5, radius*math.sin(angle)])
                    foot = np.asarray(pf.snap_point(query))
                    if not np.isfinite(foot).all() or abs(foot[1]-(support[1]-0.5)) > 0.6:
                        continue
                    separation = np.linalg.norm(foot[[0, 2]]-support[[0, 2]])
                    if not 0.65 <= separation <= 1.8:
                        continue
                    if (foot-support) @ front / separation < .6:
                        continue
                    segment = path_to(snapped[-1], foot)
                    shortest = path_to(snapped[0], foot)
                    if segment is None or shortest is None:
                        continue
                    choices.append((segment['distance_m'], foot, segment, shortest))
            if not choices:
                navigation.append({'object_id': item['object_id'], 'reachable_approach_found': False})
            else:
                _, foot, segment, shortest = min(choices, key=lambda row: row[0])
                eye = foot+np.array([0, 1.25, 0])
                capture(eye, 0, item['object_id']+'_approach', target=support+np.array([0, .22, 0]))
                navigation.append({'object_id': item['object_id'], 'reachable_approach_found': True,
                                   'standing_goal_habitat': foot.tolist(),
                                   'shortest_from_start': shortest,
                                   'extension_from_original_goal': segment,
                                   'guide_waypoint_navmesh_length_m': guide_nav_length,
                                   'guide_plus_extension_navmesh_length_m': None if guide_nav_length is None else guide_nav_length+segment['distance_m']})
            close_eye = support + 1.3*front + np.array([0, .85, 0])
            capture(close_eye, 0, item['object_id']+'_close', target=support+np.array([0, .2, 0]))
            side = np.array([front[2], 0, -front[0]])
            capture(support + .8*front + 1.0*side + np.array([0, .8, 0]), 0,
                    item['object_id']+'_side', target=support+np.array([0, .2, 0]))
        dump(args.out/'navigation_results.json', {
            'original_guide_length_m': route['route_length_m'],
            'snapped_guide_floor_positions': [p.tolist() for p in snapped],
            'navmesh_guide_segment_lengths_m': segment_lengths,
            'goals': navigation,
            'note': 'Approach reachability does not establish bag visibility; inspect approach renders. The original navmesh is used; no object collision/support claim is inferred from it.'})
        dump(args.out/'placement_results.json', {
            'scene': request['scene'], 'asset': str(asset),
            'asset_sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
            'objects': placements, 'image_changes': changes,
            'status': 'rendered preview; visual support/occlusion validation still required',
            'original_guide_length_m': 47.31053818616118,
            'navigation_report': 'navigation_results.json',
            'original_scene_modified': False})
        if not any(r['changed_pixels_gt10'] for r in changes):
            raise RuntimeError('Neither backpack changed any original goal image')
        print('Two objects added to isolated simulator; previews saved.', flush=True)
    finally:
        sim.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['probe', 'place'], default='probe')
    parser.add_argument('--request', type=Path, default=Path(__file__).with_name('placement_request.json'))
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--gpu', type=int, default=0)
    run(parser.parse_args())
