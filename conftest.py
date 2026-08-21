"""Pytest isolation for the application database and installation licensing."""

from __future__ import annotations

import atexit
import os
from pathlib import Path
import shutil
import tempfile


ROOT = Path(__file__).resolve().parent

# Never let the test suite mutate the tracked/local runtime database.  App
# configuration is resolved during import, so this must run before test modules
# import ``app``.
if not os.environ.get('GASTRO_DATA_DIR'):
    _test_data_dir = Path(tempfile.mkdtemp(prefix='gastro25-tests-'))
    _source_db = ROOT / 'gastro_booking.db'
    if _source_db.exists():
        shutil.copy2(_source_db, _test_data_dir / 'gastro_booking.db')
    os.environ['GASTRO_DATA_DIR'] = str(_test_data_dir)
    atexit.register(shutil.rmtree, _test_data_dir, ignore_errors=True)

# Activation has its own deployment flow; ordinary route tests should not be
# redirected away from the functionality they are exercising.
os.environ.setdefault('GASTRO_DISABLE_LICENSING', '1')
