"""Read sanitized design baselines without requiring private Git history."""
from pathlib import Path
from zipfile import ZipFile


def read_baseline(revision, name):
    archive = Path(__file__).resolve().parent / 'baselines' / f'{revision}.zip'
    with ZipFile(archive) as baseline:
        return baseline.read(name).decode('utf-8')
