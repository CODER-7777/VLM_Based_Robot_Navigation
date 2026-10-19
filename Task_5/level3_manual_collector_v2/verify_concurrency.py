#!/usr/bin/env python3
"""Verify an incomplete synthetic media upload does not block movement."""
import http.client
import json
from pathlib import Path
import time
from urllib.parse import urlencode
import urllib.request

ROOT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:8878'


def api(path, data=None):
    request = urllib.request.Request(BASE + path,
        data=None if data is None else json.dumps(data).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    assert not api('/api/state')['active'], 'Do not interrupt a human sample.'
    state = api('/api/start', {
        'annotator': 'v2_concurrency_validation',
        'recording_source': 'automated_upload_concurrency_validation_not_human',
        'relevant_memory_ids': ['uniforms']})
    session = state['session_id']
    fixture = (ROOT / 'voice_000.mp4').read_bytes()
    connection = http.client.HTTPConnection('127.0.0.1', 8878, timeout=15)
    connection.putrequest('POST', '/api/upload?' + urlencode({
        'session': session, 'kind': 'voice', 'mime': 'audio/mp4'}))
    connection.putheader('Content-Length', str(len(fixture)))
    connection.endheaders()
    connection.send(fixture[:100])
    time.sleep(.15)
    started = time.monotonic()
    state = api('/api/action', {'action': 'right'})
    latency = time.monotonic() - started
    assert state['actions'] == 1 and latency < 1, (state['actions'], latency)
    connection.send(fixture[100:])
    response = connection.getresponse()
    upload = json.load(response)
    assert response.status == 200, upload
    connection.close()
    state = api('/api/action', {'action': 'stop'})
    for _ in range(300):
        state = api('/api/state')
        if state['download_url']:
            break
        time.sleep(.1)
    assert state['download_url'] and len(state['audio']) == 1
    assert state['audio'][0]['filename'].endswith('.mp4')
    report = {'all_checks_passed': True,
        'movement_while_upload_body_incomplete': True,
        'action_response_ms': round(latency * 1000, 2),
        'completed_MP4_upload': True, 'human_audio_recorded': False}
    api('/api/delete', {'session_id': session, 'confirm_session': session})
    (ROOT / 'concurrency_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
