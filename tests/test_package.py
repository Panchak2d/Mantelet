import importlib.metadata
import re

import mantelet


def test_version_has_three_numbers():
    assert re.fullmatch(r"\d+\.\d+\.\d+", mantelet.__version__)


def test_version_matches_installed_package():
    assert mantelet.__version__ == importlib.metadata.version("mantelet")
