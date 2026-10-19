"""Plan a floor-restricted room tour and render slow, pose-aligned observations."""
import argparse
import csv
import heapq
import json
import math
from pathlib import Path
import subprocess
import sys

import cv2
import habitat_sim as hs
from habitat_sim.utils.common import quat_from_angle_axis
import numpy as np
from PIL import Image
import quaternion

ap = argparse.ArgumentParser()
ap.add_argument('--catalog', type=Path, required=True)
ap.add_argument('--scan', default='2azQ1b91cZZ')
ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--plan-only', action='store_true')
ap.add_argument('--existing-plan', type=Path)
args = ap.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
scene = json.loads(args.catalog.read_text())['scenes'][args.scan]
FPS, SPEED, TURN, HEIGHT, W, H = 20, .65, 15., 1.5, 1024, 682


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False))


def raw(p):
    return np.array([p[0], p[2], -p[1]], dtype=float)


def heading(a, b):
    d = np.asarray(b) - a
    return math.atan2(-float(d[0]), -float(d[2]))


def delta(a, b):
    return (b - a + math.pi) % (2 * math.pi) - math.pi


cfg = hs.SimulatorConfiguration()
cfg.scene_id = scene['scene_asset']
cfg.gpu_device_id = 0
cfg.enable_physics = True
specs = []
for name, size, fov in [('rgb', [H, W], 85), ('cube', [512, 512], 90)]:
    s = hs.SensorSpec()
    s.uuid = name
    s.sensor_type = hs.SensorType.COLOR
    s.resolution = size
    s.position = [0, 0, 0]
    s.parameters['hfov'] = str(fov)
    specs.append(s)
ac = hs.agent.AgentConfiguration()
ac.sensor_specifications = specs
sim = hs.Simulator(hs.Configuration(cfg, [ac]))
agent = sim.initialize_agent(0)


def set_camera(position, yaw, pitch=0):
    st = hs.AgentState()
    st.position = np.asarray(position, dtype=np.float32)
    st.rotation = quat_from_angle_axis(yaw, np.array([0, 1, 0])) * quat_from_angle_axis(pitch, np.array([1, 0, 0]))
    agent.set_state(st, reset_sensors=True)


def floor_path(a, b, center_y):
    request = hs.ShortestPath()
    request.requested_start = np.asarray(a, dtype=np.float32)
    request.requested_end = np.asarray(b, dtype=np.float32)
    if not sim.pathfinder.find_path(request):
        return None
    pts = np.asarray(request.points, dtype=float)
    if not np.isfinite(pts).all() or np.max(np.abs(pts[:, 1] - center_y)) > .4:
        return None
    return pts


def path_length(points):
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


def at_distance(points, d):
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cum = np.r_[0, np.cumsum(lengths)]
    i = min(len(lengths) - 1, max(0, int(np.searchsorted(cum, d, side='right') - 1)))
    return points[i] + np.clip((d - cum[i]) / lengths[i], 0, 1) * (points[i + 1] - points[i])


def plan_floor():
    regions = {int(k): v for k, v in scene['regions'].items() if v['level'] == 0 and v['name'] != 'stairs'}
    expected_y = float(np.median([r['position'][2] for r in regions.values()]))
    candidates = []
    for vp, p in scene['panoramas'].items():
        if p['region'] not in regions:
            continue
        requested = raw(p['position']) - [0, HEIGHT, 0]
        if abs(requested[1] - expected_y) > .55:
            continue
        floor = np.asarray(sim.pathfinder.snap_point(requested), dtype=float)
        if np.isfinite(floor).all() and np.linalg.norm(floor - requested) < .7 and abs(floor[1] - expected_y) < .4:
            candidates.append(dict(viewpoint=vp, region=p['region'], floor=floor))
    if not candidates:
        raise RuntimeError('No validated ground-floor observation points')
    center_y = float(np.median([p['floor'][1] for p in candidates]))
    # All graph edges are complete navmesh paths validated to stay on this floor.
    graph = {i: [] for i in range(len(candidates))}
    paths = {}
    for i, a in enumerate(candidates):
        for j in range(i):
            b = candidates[j]
            if np.linalg.norm(a['floor'] - b['floor']) > 7.:
                continue
            points = floor_path(a['floor'], b['floor'], center_y)
            if points is None:
                continue
            distance = path_length(points)
            if distance < 1e-5:
                continue
            graph[i].append((j, distance))
            graph[j].append((i, distance))
            paths[i, j] = points
            paths[j, i] = points[::-1]

    def shortest(start):
        dist, prev, pending = {start: 0.}, {}, [(0., start)]
        while pending:
            d, i = heapq.heappop(pending)
            if d > dist[i]:
                continue
            for j, edge in graph[i]:
                nd = d + edge
                if nd < dist.get(j, float('inf')):
                    dist[j], prev[j] = nd, i
                    heapq.heappush(pending, (nd, j))
        return dist, prev

    entry = next((r for r in regions if regions[r]['name'] == 'entryway'), min(regions))
    start = min((i for i, p in enumerate(candidates) if p['region'] == entry),
                key=lambda i: np.linalg.norm(candidates[i]['floor'][[0, 2]] - raw(regions[entry]['position'])[[0, 2]]))
    reachable, _ = shortest(start)
    representatives = {}
    for region, r in regions.items():
        options = [i for i in reachable if candidates[i]['region'] == region]
        if options:
            representatives[region] = min(options, key=lambda i: np.linalg.norm(candidates[i]['floor'][[0, 2]] - raw(r['position'])[[0, 2]]))
    missing = sorted(set(regions) - set(representatives))
    if missing:
        raise RuntimeError('Ground-floor rooms not reachable by floor-restricted paths: ' + str(missing))
    current, distance = start, 0.
    points = [candidates[start]['floor']]
    stops, remaining, legs = [], set(representatives), []
    anchors = {}
    while remaining:
        distances, previous = shortest(current)
        region = min(remaining, key=lambda r: distances.get(representatives[r], float('inf')))
        target = representatives[region]
        chain = [target]
        while chain[-1] != current:
            chain.append(previous[chain[-1]])
        chain.reverse()
        before = distance
        for a, b in zip(chain, chain[1:]):
            segment = paths[a, b]
            for point in segment[1:]:
                if np.linalg.norm(point - points[-1]) > 1e-5:
                    distance += float(np.linalg.norm(point - points[-1]))
                    points.append(point)
        label = str(len(stops) + 1)
        r = regions[region]
        stops.append(dict(label=label, region=region, room=r['name'], distance_m=distance,
                          viewpoint=candidates[target]['viewpoint'], rotate=r['name'] != 'hallway'))
        anchors[label] = candidates[target]['floor'].tolist()
        legs.append(dict(to_anchor=label, region=region, room=r['name'], start_m=before, length_m=distance - before))
        current = target
        remaining.remove(region)
    points = np.asarray(points)
    length = path_length(points)
    distances = sorted([float(v) for v in np.arange(0, length, 2)] + [length] + [s['distance_m'] for s in stops])
    unique = []
    for d in distances:
        if not unique or d - unique[-1] > 1e-4:
            unique.append(d)
    cps = []
    for i, d in enumerate(unique):
        floor = at_distance(points, d)
        labels = [s['label'] for s in stops if abs(s['distance_m'] - d) < 1e-4]
        cps.append(dict(id=f'C{i+1:02d}', distance_m=d, position_floor_habitat=floor.tolist(),
                        position_camera_habitat=(floor + [0, HEIGHT, 0]).tolist(), anchor_labels=labels,
                        regular_2m_checkpoint=abs(d / 2 - round(d / 2)) < 1e-5,
                        interval_path_m=d - unique[i-1] if i else 0.,
                        interval_euclidean_m=float(np.linalg.norm(floor - np.array(cps[-1]['position_floor_habitat']))) if i else 0.))
    return dict(title='2azQ1b91cZZ · ground-floor video tour', scene=args.scan, tour_id='ground_2az',
                authored=True, floor_level=0, floor_y_habitat=center_y, floor_height_tolerance_m=.4,
                ground_floor_regions=sorted(regions), rooms_visited=stops, room_coverage_count=len(stops),
                route_floor_habitat=points.tolist(), route_length_m=length, anchor_floor_habitat=anchors,
                anchor_sequence=[s['label'] for s in stops], anchor_visits=stops, legs=legs, checkpoints=cps,
                inspection_rotation_degrees=360, inspection_locations=sum(s['rotate'] for s in stops),
                physical_gpu=0, note='Authored ground-floor tour. All route points/edges remain within 0.4m of the ground navmesh floor. No stairs or upper-floor route legs.')


def add_props():
    import magnum as mn
    manager = sim.get_object_template_manager()
    for prop in scene['props']:
        handle = 'tour_' + prop['id']
        attr = manager.create_new_template(handle, False)
        attr.render_asset_handle = prop['asset']
        attr.collision_asset_handle = prop['asset']
        attr.orient_up, attr.orient_front = mn.Vector3(0, 1, 0), mn.Vector3(0, 0, -1)
        attr.scale, attr.com = mn.Vector3(1), mn.Vector3(0)
        attr.compute_COM_from_shape = False
        attr.requires_lighting = False
        manager.register_template(attr, handle)
        oid = sim.add_object_by_handle(handle, light_setup_key=hs.gfx.NO_LIGHT_KEY)
        sim.set_object_motion_type(hs.physics.MotionType.KINEMATIC, oid)
        q = prop['rotation_xyzw']
        sim.set_rotation(mn.Quaternion(mn.Vector3(*q[:3]), q[3]), oid)
        sim.set_translation(mn.Vector3(*prop['translation']), oid)
        sim.set_object_motion_type(hs.physics.MotionType.STATIC, oid)


def make_timeline(plan):
    points = np.array(plan['route_floor_habitat'])
    timeline, yaw, distance = [], heading(points[0], points[1]), 0.

    def frame(p, angle, d, event, room=None):
        timeline.append(dict(frame=len(timeline), time_s=len(timeline)/FPS, distance_m=float(d),
                             position_camera_habitat=(np.array(p)+[0, HEIGHT, 0]).tolist(),
                             yaw_radians=float(angle), event=event, room=room))

    def turn(p, change, event, room=None):
        nonlocal yaw
        start = yaw
        count = int(math.ceil(abs(math.degrees(change)) / TURN * FPS))
        for i in range(1, count + 1):
            frame(p, start + change*i/count, distance, event, room)
        yaw += change

    stops = plan['anchor_visits']
    stop_index = 0
    frame(points[0], yaw, 0., 'walk')
    while stop_index < len(stops) and stops[stop_index]['distance_m'] < 1e-4:
        stop = stops[stop_index]
        if stop.get('rotate', stop['label'] == '5'):
            lo = len(timeline)/FPS
            turn(points[0], 2*math.pi, 'inspection_360', stop.get('room'))
            stop['inspection_video_interval_s'] = [lo, len(timeline)/FPS]
        stop_index += 1
    for a, b in zip(points, points[1:]):
        leg = float(np.linalg.norm(b-a))
        turn(a, delta(yaw, heading(a, b)), 'turn_to_path')
        targets = list(np.arange(SPEED/FPS, leg, SPEED/FPS)) + [leg]
        for s in stops:
            rel = s['distance_m'] - distance
            if 1e-5 < rel < leg-1e-5:
                targets.append(rel)
        segment_start = distance
        for local_d in sorted(set(targets)):
            pos = a + (b-a)*local_d/leg
            distance = segment_start + local_d
            frame(pos, yaw, distance, 'walk')
            while stop_index < len(stops) and stops[stop_index]['distance_m'] <= distance + 1e-4:
                stop = stops[stop_index]
                rotate = stop.get('rotate', stop['label'] == '5')
                if rotate:
                    lo = len(timeline)/FPS
                    turn(pos, 2*math.pi, 'inspection_360', stop.get('room'))
                    stop['inspection_video_interval_s'] = [lo, len(timeline)/FPS]
                stop_index += 1
    return timeline


def panorama(position, destination):
    width, height = 2048, 1024
    lon = (np.arange(width)+.5)/width*2*np.pi-np.pi
    lat = np.pi/2-(np.arange(height)+.5)/height*np.pi
    co = np.cos(lat)[:, None]
    directions = np.stack([co*np.sin(lon)[None, :], np.broadcast_to(np.sin(lat)[:, None], (height, width)), -co*np.cos(lon)[None, :]], axis=-1)
    result = np.zeros((height, width, 3), dtype=np.uint8)
    score = np.full((height, width), -1.)
    for yaw, pitch in [(0,0), (math.pi/2,0), (math.pi,0), (-math.pi/2,0), (0,math.pi/2), (0,-math.pi/2)]:
        set_camera(position, yaw, pitch)
        rgb = sim.get_sensor_observations()['cube'][:, :, :3]
        q = quat_from_angle_axis(yaw, np.array([0,1,0])) * quat_from_angle_axis(pitch, np.array([1,0,0]))
        local = directions @ quaternion.as_rotation_matrix(q)
        z = -local[:, :, 2]
        valid = (z>0) & (z>=np.abs(local[:,:,0])-1e-6) & (z>=np.abs(local[:,:,1])-1e-6) & (z>score)
        mx = np.float32((local[:,:,0]/np.maximum(z,1e-6)+1)*256-.5)
        my = np.float32((1-local[:,:,1]/np.maximum(z,1e-6))*256-.5)
        sampled = cv2.remap(rgb, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        result[valid], score[valid] = sampled[valid], z[valid]
    if np.any(score<0):
        raise RuntimeError('Incomplete panorama')
    Image.fromarray(result).save(destination, quality=94)


try:
    if not sim.pathfinder.is_loaded:
        raise RuntimeError('Scene navmesh is missing')
    plan = json.loads(args.existing_plan.read_text()) if args.existing_plan else plan_floor()
    plan.update(camera=dict(height_m=HEIGHT, hfov_degrees=85., resolution=[W,H], fps=FPS),
                nominal_speed_m_s=SPEED, turn_speed_degrees_s=TURN, status='planned')
    timeline = make_timeline(plan)
    plan.update(video='walkthrough.mp4', video_duration_s=len(timeline)/FPS, frame_count=len(timeline))
    for cp in plan['checkpoints']:
        f = min(timeline, key=lambda f: abs(f['distance_m'] - cp['distance_m']))
        cp.update(video_time_s=f['time_s'], video_frame=f['frame'], yaw_radians=f['yaw_radians'],
                  panorama=cp['id']+'_panorama.jpg')
    dump(args.out/'plan.json', plan)
    dump(args.out/'timeline.json', timeline)
    print('PLAN', json.dumps({k:plan.get(k) for k in ['scene','route_length_m','room_coverage_count','floor_y_habitat','video_duration_s','frame_count','turn_speed_degrees_s']}), flush=True)
    if not args.plan_only:
        add_props()
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        command = [ffmpeg,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','-','-an','-c:v','libx264','-threads','4','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(args.out/'walkthrough.mp4')]
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
        try:
            for f in timeline:
                set_camera(f['position_camera_habitat'], f['yaw_radians'])
                rgb = sim.get_sensor_observations()['rgb'][:,:,:3]
                encoder.stdin.write(np.ascontiguousarray(rgb).tobytes())
                if f['frame'] % 1000 == 0:
                    print('VIDEO',f['frame'],'/',len(timeline),flush=True)
        finally:
            encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError('Video conversion failed')
        for cp in plan['checkpoints']:
            panorama(cp['position_camera_habitat'], args.out/cp['panorama'])
            set_camera(cp['position_camera_habitat'], cp['yaw_radians'])
            rgb = sim.get_sensor_observations()['rgb'][:,:,:3]
            Image.fromarray(rgb).save(args.out/(cp['id']+'_forward.jpg'), quality=94)
            print('PANORAMA',cp['id'],flush=True)
        plan['status']='recorded'
        dump(args.out/'plan.json', plan)
        fields=['id','distance_m','interval_path_m','interval_euclidean_m','video_time_s','video_frame','regular_2m_checkpoint','panorama','camera_x','camera_y','camera_z','forward_yaw_radians','anchor_labels']
        with (args.out/'checkpoints.csv').open('w') as out:
            writer=csv.DictWriter(out,fields);writer.writeheader()
            for cp in plan['checkpoints']:
                row={k:cp[k] for k in fields if k in cp}
                row.update(zip(['camera_x','camera_y','camera_z'],cp['position_camera_habitat']))
                row.update(forward_yaw_radians=cp['yaw_radians'],anchor_labels=';'.join(cp['anchor_labels']))
                writer.writerow(row)
        print('COMPLETE',len(timeline),'frames',len(plan['checkpoints']),'panoramas',flush=True)
finally:
    sim.close()
