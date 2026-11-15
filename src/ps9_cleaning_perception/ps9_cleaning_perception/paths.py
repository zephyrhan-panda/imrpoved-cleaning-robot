"""Resolve bundled assets from a colcon installation or a source checkout."""

from pathlib import Path
import sys


def asset_path(relative: str) -> Path:
    roots = []
    try:
        from ament_index_python.packages import (
            get_package_share_directory, PackageNotFoundError,
        )
    except ImportError:
        pass
    else:
        try:
            roots.append(Path(get_package_share_directory('ps9_cleaning_perception')))
        except PackageNotFoundError:
            pass
    roots.extend([Path(__file__).resolve().parent.parent,
                  Path(sys.prefix) / 'share' / 'ps9_cleaning_perception'])
    for root in roots:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f'Bundled asset not found: {relative}; build/source the workspace.')
