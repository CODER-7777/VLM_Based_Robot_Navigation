"""Exercise automatic audio extraction, download and ZIP using synthetic media only."""
import argparse
import hashlib
from http.client import HTTPConnection
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.template.resolve()))
    spec = importlib.util.spec_from_file_location('screen_audio_test_collector', args.template / 'collector.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix='task5-audio-qa-') as directory:
        root = Path(directory); module.ROOT = root
        sample = root / 'sessions/synthetic/test'; (sample / 'screen').mkdir(parents=True)
        (sample / 'audio').mkdir(); (sample / 'inputs.json').write_text('{}'); (sample / 'manifest.json').write_text('{}')
        old_voice = sample / 'audio/voice_000.mp4'; old_voice.write_bytes(b'pre-existing synthetic voice fixture')
        raw = root / 'synthetic.upload'
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi',
                        '-i', 'color=c=green:s=64x64:r=10', '-f', 'lavfi', '-i', 'sine=frequency=880:sample_rate=48000',
                        '-t', '1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-threads', '2', '-c:a', 'aac',
                        '-f', 'mp4', str(raw)], check=True)
        app = module.Collector.__new__(module.Collector)
        app.event_lock = threading.Lock(); app.jobs = {'synthetic': {'status': 'queued'}}
        app.convert_media('synthetic', sample, raw, 'screen/screen_000.mp4', 'screen', 'video/mp4', {})
        assert app.jobs['synthetic']['status'] == 'ready', app.jobs
        audio = sample / 'audio/screen_000.m4a'; screen = sample / 'screen/screen_000.mp4'
        assert audio.is_file() and audio.stat().st_size > 0
        assert app.jobs['synthetic']['audio_path'] == 'audio/screen_000.m4a'
        digest = hashlib.sha256(screen.read_bytes()).hexdigest()
        audio_digest = hashlib.sha256(audio.read_bytes()).hexdigest()
        again = module.extract_screen_audio(sample, 'screen/screen_000.mp4')
        assert again['already_exists'] and hashlib.sha256(audio.read_bytes()).hexdigest() == audio_digest
        assert hashlib.sha256(screen.read_bytes()).hexdigest() == digest
        assert old_voice.read_bytes() == b'pre-existing synthetic voice fixture'
        assert {item['filename'] for item in module.session_audio(sample)} == {'screen_000.m4a', 'voice_000.mp4'}
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(audio), '-f', 'null', '-'],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        server = module.ThreadingHTTPServer(('127.0.0.1', 0), module.Handler)
        server.app = SimpleNamespace(jobs={})
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            connection = HTTPConnection('127.0.0.1', server.server_address[1], timeout=20)
            connection.request('GET', '/api/media?session=sessions/synthetic/test&file=audio/screen_000.m4a')
            response = connection.getresponse()
            assert response.status == 200 and response.getheader('Content-Type') == 'audio/mp4'
            assert hashlib.sha256(response.read()).hexdigest() == audio_digest
            connection.request('GET', '/api/download?session=sessions/synthetic/test')
            response = connection.getresponse(); assert response.status == 200
            with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
                assert archive.read('audio/screen_000.m4a') == audio.read_bytes()
                assert archive.read('audio/voice_000.mp4') == old_voice.read_bytes()
            connection.close()
        finally: server.shutdown(); server.server_close()
        silent = sample / 'screen/screen_001.mp4'
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(screen), '-an', '-c:v', 'copy', str(silent)], check=True)
        try: module.extract_screen_audio(sample, 'screen/screen_001.mp4')
        except subprocess.CalledProcessError: pass
        else: raise AssertionError('Video without audio must not produce a fake voice clip')
        assert not (sample / 'audio/screen_001.m4a').exists()
        assert not list((sample / 'audio').glob('*.partial.m4a'))
        report = {'passed': True, 'future_conversion_extracts_audio': True, 'audio_download_verified': True,
                  'ZIP_contains_separate_audio': True, 'repeat_extraction_idempotent': True,
                  'screen_video_and_existing_voice_preserved': True, 'silent_source_fails_without_fake_clip': True,
                  'synthetic_media_only': True}
        args.report.write_text(json.dumps(report, indent=2) + '\n'); print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
