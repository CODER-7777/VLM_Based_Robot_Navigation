"""Record source-image/pose identities after frozen all-episode inference completes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args();root=args.run.resolve()
    manifest=json.loads((root/'manifest.json').read_text())
    assert len(manifest['episodes'])==manifest['expected_episode_count']
    output=root/'inputs/poses';output.mkdir(parents=True,exist_ok=True)
    files={};source_images=[]
    for ep in manifest['episodes']:
        data=root/ep['data'];record=json.loads(data.read_text())
        assert sha(data)==ep['sha256']
        files[str(data.relative_to(root))]=sha(data)
        poses=Path(record['poses_path']);copy=output/poses.name
        shutil.copy2(poses,copy)
        assert sha(copy)==record['poses_sha256']
        files[str(copy.relative_to(root))]=sha(copy)
        frame_root=poses.parent.parent/'frames'/poses.stem
        for segment in record['segments']:
            original=frame_root/segment['frame_start_name']
            background=root/segment['background']
            files[segment['background']]=sha(background)
            source_images.append({'episode':ep['episode'],'segment':segment['id'],
                                  'original_png':str(original),'original_sha256':sha(original),
                                  'display_jpeg':segment['background'],'display_sha256':sha(background),
                                  'conversion':'JPEG quality86, dimensions and projection coordinates preserved'})
    record={'files':files,'keyframes':source_images,'poses_copied_without_changes':True,
            'scope':'Source identities only; no GPU, inference, alignment or training'}
    (root/'input_provenance.json').write_text(json.dumps(record,indent=2)+'\n')
    print('INPUT_PROVENANCE_RECORDED',len(manifest['episodes']),len(source_images),len(files))


if __name__=='__main__':main()
