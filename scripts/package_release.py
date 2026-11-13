#!/usr/bin/env python3
"""Package the prebuilt Bloedgeas runtime files; no REDkit installation needed."""

import argparse
import hashlib
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = (
    'mods/modVampSword',
    'mods/modGearLevelScaling',
    'dlc/dlcvampsword',
)
REQUIRED = (
    'mods/modVampSword/content/blob0.bundle',
    'mods/modVampSword/content/buffers0.bundle',
    'mods/modVampSword/content/metadata.store',
    'mods/modVampSword/content/texture.cache',
    'mods/modVampSword/content/soundspc.cache',
    'mods/modVampSword/content/scripts/local/bloedgeas.ws',
    'mods/modGearLevelScaling/content/scripts/local/ItemLevelScaling_main.ws',
    'mods/modGearLevelScaling/content/scripts/game/player/playerWitcher.ws',
    'mods/modGearLevelScaling/content/scripts/game/components/inventoryComponent.ws',
    'dlc/dlcvampsword/content/blob0.bundle',
    'dlc/dlcvampsword/content/metadata.store',
    'dlc/dlcvampsword/content/texture.cache',
    'dlc/dlcvampsword/content/soundspc.cache',
    'dlc/dlcvampsword/content/en.w3strings',
    'dlc/dlcvampsword/content/ua.w3strings',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='1.0.0')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', args.version):
        parser.error('--version must be a numeric semantic version, optionally with a suffix')

    payload = {}
    for component in COMPONENTS:
        directory = ROOT / 'installed' / component
        if not directory.is_dir():
            raise SystemExit(f'Missing runtime component: {component}')
        for path in sorted(directory.rglob('*')):
            if path.is_symlink():
                raise SystemExit(f'Refusing symlink in runtime payload: {path}')
            if path.is_file() and path.suffix not in {'.noicon', '.log', '.bak'}:
                name = path.relative_to(ROOT / 'installed').as_posix()
                payload[name] = path.read_bytes()
    for name in REQUIRED:
        if not payload.get(name):
            raise SystemExit(f'Missing or empty required file: {name}')
    runtime_count = len(payload)
    payload['README.md'] = (ROOT / 'README.md').read_bytes()
    payload['SHA256SUMS'] = ''.join(
        f'{digest(data)}  {name}\n' for name, data in sorted(payload.items())
    ).encode('utf-8')

    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / f'Bloedgeas-v{args.version}-Witcher3-5.01c.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name, data in sorted(payload.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 11, 13, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            package.writestr(entry, data)
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise SystemExit('ZIP integrity check failed')
        if set(package.namelist()) != set(payload):
            raise SystemExit('ZIP file list differs from payload')
        for name, data in payload.items():
            if package.read(name) != data:
                raise SystemExit(f'ZIP byte comparison failed: {name}')
    checksum = args.output / 'SHA256SUMS'
    checksum.write_text(f'{digest(archive.read_bytes())}  {archive.name}\n', encoding='utf-8')
    print(f'Created {archive} ({archive.stat().st_size:,} bytes)')
    print(f'Verified {runtime_count} runtime files plus README.md and internal SHA256SUMS')
    print(f'Archive checksum: {checksum}')


if __name__ == '__main__':
    main()
