"""Check the exact bytes served to the demo, including after Linux checkout/build."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for relative in ('frontend/public/real-demo', 'src/bluecho/dashboard/static/real-demo'):
    folder = root / relative
    catalog = json.loads((folder / 'catalog.json').read_text(encoding='utf-8'))
    for sample in catalog:
        for name, expected in sample['files'].items():
            asset = folder / sample['id'] / name
            assert hashlib.sha256(asset.read_bytes()).hexdigest() == expected, str(asset)
        result = json.loads((folder / sample['id'] / 'results.json').read_text(encoding='utf-8'))
        assert result['demo']['kind'] == 'real_sonar_saved_inference'
        assert result['demo']['synthetic'] is False
        assert result['demo']['display_png_sha256'] == sample['files']['original.png']
    print(relative, ': all real sample hashes and provenance verified')
