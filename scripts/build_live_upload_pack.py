"""Copy verified real samples into a small, separately attributed local upload pack."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=Path, required=True)
    parser.add_argument('--watertank', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    records = json.loads((args.samples / 'manifest.json').read_text(encoding='utf-8'))['samples']
    rows = []
    for record in records:
        sid = record['id']
        if sid not in ('pipeline_positive', 'pipeline_empty') and not sid.startswith('fls_'):
            continue
        source = args.samples / record['path']
        assert digest(source) == record['sha256'], sid
        fls = sid.startswith('fls_')
        labels = sorted({t['class_name'] for t in (record['truth'] or [])})
        if fls:
            filename = record['original_source'].split('/')[-1]
            originals = list(args.watertank.rglob(filename))
            assert any(digest(p) == record['sha256'] for p in originals), filename
        folder = out / ('FLS_Debris' if fls else 'SSS_Pipeline')
        folder.mkdir(exist_ok=True)
        name = (sid + '_' + '-and-'.join(labels) if fls else sid) + '.png'
        destination = folder / name
        decoded = repo / 'frontend/public/real-demo' / ('pipeline' if sid == 'pipeline_positive' else 'seabed') / 'original.png'
        shutil.copyfile(source if fls else decoded, destination)
        with Image.open(source) as a, Image.open(destination) as b:
            assert a.convert('RGB').tobytes() == b.convert('RGB').tobytes()
            width, height = b.size
        rows.append(dict(file=destination.relative_to(out).as_posix(), model='fls11-debris' if fls else 'sss-pipeline-v3', modality='FLS_ARIS' if fls else 'SSS_LF', source_labels=labels, source_path=str(source), source_sha256=digest(source), sha256=digest(destination), width=width, height=height, licence='CC BY-NC-SA 4.0' if fls else 'CC BY 4.0', location='Unavailable: no verified per-image coordinates', change='Byte-identical original PNG' if fls else 'Lossless PNG decoding; RGB pixels verified identical'))
    assert len(rows) == 10 and len({r['sha256'] for r in rows}) == 10
    jpg = out / 'JPEG_Format_Examples'
    jpg.mkdir()
    for sid in ('pipeline', 'seabed', 'propeller', 'bottle'):
        with Image.open(repo / 'frontend/public/real-demo' / sid / 'original.png') as image:
            image.convert('RGB').save(jpg / (sid + '.jpg'), quality=96, subsampling=0)
    (out / 'source_manifest.json').write_text(json.dumps(dict(unique_images=10, additional_jpeg_encodings=4, images=rows), indent=2), encoding='utf-8')
    shutil.copyfile(repo / 'frontend/public/real-demo/ATTRIBUTION.md', out / 'DATA_ATTRIBUTION.md')
    guide = '''# BluEcho live presentation images

Ten different REAL sonar images are in SSS_Pipeline and FLS_Debris. Upload these PNGs: no drawn boxes or simulated objects. JPEG_Format_Examples contains four smaller JPEG versions of existing scenes, not four additional observations.

Open https://bluecho-sih-2026.vercel.app and choose New inspection. Upload an image, confirm its sensor and model, then run inspection. This performs real inference; Try demo instead loads saved results.

- SSS_Pipeline: SSS_LF / side-scan low frequency; model sss-pipeline-v3.
- FLS_Debris: FLS_ARIS / forward-looking ARIS; model fls11-debris.
- JPEG examples: pipeline/seabed use SSS; propeller/bottle use FLS. These are smaller lossy previews, so results can differ. Prefer full-resolution PNGs.

Start with pipeline_positive.png, then fls_4_hook-and-propeller.png or fls_7_shampoo-bottle.png. Change models when switching sensor folders. Try can, chain, carton, valve, standing-bottle and tire/bottle scenes for variety. Names reflect source annotations, not guaranteed predictions. pipeline_empty.png previously returned no detections; this does not prove a safe seafloor.

First inference may download a model. Keep the tab open. Batch only images from the SAME sensor/model. Review candidates and export PDF or evidence ZIP reports.

These samples lack verified per-image coordinates. Locations must remain unavailable. These are development/water-tank observations, not independent accuracy tests. Bottle labels do not prove plastic material. Scores are uncalibrated.

## Sources and licences

SubPipe: https://zenodo.org/records/12666132, CC BY 4.0. Marine Debris FLS: https://zenodo.org/records/15101686, CC BY-NC-SA 4.0. Preserve DATA_ATTRIBUTION.md and the noncommercial/share-alike terms for FLS images and derivatives. For the noncommercial SIH research demonstration.

PNG source pixels were verified identical; JPEGs preserve original dimensions with quality 96 encoding. source_manifest.json records original paths, labels, hashes and geometry.

## Team BluEcho — Smart India Hackathon 2026

Khushi Mhamane, Sharon Melhi, Kirti Rajput, Peeyush Rampal, Aditya Banerjee, and Aditya SS Varma.
'''
    (out / 'START_HERE.md').write_text(guide, encoding='utf-8')
    archive = out.parent / (out.name + '.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob('*')):
            if path.is_file():
                z.write(path, Path(out.name) / path.relative_to(out))
    print(json.dumps(dict(folder=str(out), zip=str(archive), unique_images=len(rows), jpg_examples=4, zip_bytes=archive.stat().st_size), indent=2))


if __name__ == '__main__':
    main()
