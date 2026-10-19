"""Save a slower-turn reference video without changing translation speed or poses."""
import copy
import csv
import json
from pathlib import Path
import shutil
import subprocess

import cv2

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/pilot_04'
OUT = ROOT / 'assets/pilot_04_slow'
OUT.mkdir(exist_ok=True)
plan = json.loads((SOURCE / 'plan.json').read_text())
original = json.loads((SOURCE / 'timeline.json').read_text())
fps = plan['camera']['fps']
factor = 4
timeline, frame_map = [], []
for f in original:
    frame_map.append(len(timeline))
    for _ in range(1 if f['event'] == 'walk' else factor):
        new = copy.deepcopy(f)
        new.update(frame=len(timeline), time_s=len(timeline)/fps, source_frame=f['frame'])
        timeline.append(new)
frame_map.append(len(timeline))
plan.update(title='Environment 04 · slow-turn walkthrough', tour_id='pilot04_slow',
            turn_speed_degrees_s=15., video_duration_s=len(timeline)/fps, frame_count=len(timeline),
            rotation_retiming='Stationary turning frames replayed four times; translation unchanged.',
            status='recorded')
if 'inspection_video_interval_s' in plan:
    plan['inspection_video_interval_s'] = [frame_map[round(t*fps)]/fps for t in plan['inspection_video_interval_s']]
for cp in plan['checkpoints']:
    cp['video_frame'] = frame_map[cp['video_frame']]
    cp['video_time_s'] = cp['video_frame']/fps
    cp['yaw_radians'] = timeline[cp['video_frame']]['yaw_radians']
width, height = plan['camera']['resolution']
encoder = subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo',
                            '-pix_fmt','bgr24','-video_size',f'{width}x{height}','-framerate',str(fps),
                            '-i','-','-an','-c:v','libx264','-threads','4','-preset','veryfast','-crf','19',
                            '-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'walkthrough.mp4')], stdin=subprocess.PIPE)
capture = cv2.VideoCapture(str(SOURCE/'walkthrough.mp4'))
try:
    for f in original:
        ok, image = capture.read()
        if not ok:
            raise RuntimeError('Source recording ended before its pose timeline')
        for _ in range(1 if f['event']=='walk' else factor):
            encoder.stdin.write(image.tobytes())
finally:
    capture.release()
    encoder.stdin.close()
if encoder.wait():
    raise RuntimeError('Slower reference encoding failed')
for image in SOURCE.glob('*.jpg'):
    shutil.copy2(image, OUT/image.name)
(OUT/'plan.json').write_text(json.dumps(plan,indent=2))
(OUT/'timeline.json').write_text(json.dumps(timeline))
with (OUT/'checkpoints.csv').open('w') as out:
    fields=['id','distance_m','interval_path_m','interval_euclidean_m','video_time_s','video_frame','regular_2m_checkpoint','panorama','camera_x','camera_y','camera_z','forward_yaw_radians','anchor_labels']
    writer=csv.DictWriter(out,fields);writer.writeheader()
    for cp in plan['checkpoints']:
        row={k:cp[k] for k in fields if k in cp}
        row.update(zip(['camera_x','camera_y','camera_z'],cp['position_camera_habitat']))
        row.update(forward_yaw_radians=cp['yaw_radians'],anchor_labels=';'.join(cp['anchor_labels']))
        writer.writerow(row)
guide=(SOURCE/'RECORDING_AND_REASONING_GUIDE.md').read_text()
guide=guide.replace('80-second',f"{plan['video_duration_s']:.2f}-second").replace('about 6 seconds','about 24 seconds')
guide=guide.replace('/assets/pilot_04/','/assets/pilot_04_slow/')
guide='# Slow-turn version of Environment 04\n\nStationary rotations replay at 15 degrees/second; translation is unchanged. Turning frames are repeated four times, so this is slower playback of the original views, not freshly rendered intermediate angles. The original video remains available in the archived pilot_04 folder.\n\n'+guide
(OUT/'RECORDING_AND_REASONING_GUIDE.md').write_text(guide)
print('Slower reference ready:',plan['video_duration_s'],'seconds;',len(timeline),'frames')
