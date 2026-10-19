"""Package every recorded checkpoint image for a single dashboard download."""
import argparse
import json
from pathlib import Path
import zipfile

DEFAULT_ASSETS = Path(__file__).resolve().parents[1] / 'assets/pilot_04'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=DEFAULT_ASSETS)
    parser.add_argument('--filename', default='checkpoint_images_all_30.zip')
    args = parser.parse_args()
    ASSETS = args.assets.resolve()
    plan = json.loads((ASSETS / 'plan.json').read_text())
    images = []
    for checkpoint in plan['checkpoints']:
        identifier = checkpoint['id']
        images.extend([
            (ASSETS / checkpoint['panorama'], f'checkpoints/{identifier}/panorama.jpg'),
            (ASSETS / (identifier + '_forward.jpg'), f'checkpoints/{identifier}/forward.jpg'),
        ])
    for path, _ in images:
        if not path.is_file():
            raise FileNotFoundError(path)
    target = ASSETS / args.filename
    temporary = target.with_suffix('.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_STORED) as archive:
        for path, name in images:
            archive.write(path, name)
        for filename in ('plan.json', 'checkpoints.csv'):
            archive.write(ASSETS / filename, filename)
        archive.write(ASSETS / 'RECORDING_AND_REASONING_GUIDE.md', 'RECORDING_AND_REASONING_GUIDE.md')
        archive.write(ASSETS.parent / 'reasoning_template.txt', 'reasoning_template.txt')
        archive.writestr('README.txt',
            f"{plan['title']} ({plan['scene']}) - recorded checkpoint images\n"
            f"{len(plan['checkpoints'])} checkpoints, {len(images)} JPEG images.\n\n"
            "Each checkpoints/Cxx/ folder contains:\n"
            "- panorama.jpg: full 360-degree equirectangular image (2048x1024).\n"
            "- forward.jpg: forward camera image at that checkpoint.\n\n"
            "Images are already rendered from Habitat; you do not need to record them.\n"
            "Open panorama.jpg in a 360-degree viewer to look around; in a normal image\n"
            "viewer it appears as a flattened panoramic image.\n\n"
            "checkpoints.csv gives distances, camera coordinates and video times.\n"
            "plan.json gives the complete authored route and checkpoint metadata.\n"
            "Regular checkpoints are spaced 2m along the path, with additional anchors.\n"
            "Repeated locations on the return leg have separate checkpoint IDs.\n"
            f"The {plan['video_duration_s']:.2f}-second walkthrough video is downloaded separately from the dashboard.\n")
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None
        assert len([n for n in archive.namelist() if n.endswith('.jpg')]) == len(images)
    temporary.replace(target)
    print(f'{target}: {len(images)} images, {target.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
