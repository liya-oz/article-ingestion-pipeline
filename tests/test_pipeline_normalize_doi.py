import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from pipeline import normalize_doi

@pytest.mark.parametrize("inp,expected", [
    (None, ""),                             # None -> empty string
    ("", ""),                               # empty -> empty string
    ("   \t\n", ""),                        # whitespace-only -> empty string
    ("doi:10.1007/s10671-016-9199-2", "10.1007/s10671-016-9199-2"),
    ("DOI:10.1007/S10671-016-9199-2", "10.1007/s10671-016-9199-2"),  # case-insensitive prefix + lowercase result
    ("  DOI:10.1007/s10671-016-9199-2  ", "10.1007/s10671-016-9199-2"),  # trim whitespace
    ("10.1007/S10671-016-9199-2", "10.1007/s10671-016-9199-2"),  # no prefix -> only lowercase
    ("doi:doi:10.1/ABC", "doi:10.1/abc"),   # remove at most one leading "doi:"
])
def test_normalize_doi(inp, expected):
    assert normalize_doi(inp) == expected