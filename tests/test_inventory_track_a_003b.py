from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.inventory_track_a_003b import parse_imports, tree_digest


class InventoryTrackA003bTests(unittest.TestCase):
    def test_static_import_inventory_does_not_execute_source(self) -> None:
        source = b"import numpy as np\nfrom scipy.ndimage import label\nraise RuntimeError('no')\n"
        self.assertEqual(parse_imports(source, "candidate.py"), ["numpy", "scipy"])

    def test_tree_digest_is_deterministic_and_excludes_dot_git(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "nested").mkdir()
            (root / ".git").mkdir()
            (root / "a.txt").write_bytes(b"a")
            (root / "nested" / "b.txt").write_bytes(b"b")
            (root / ".git" / "secret").write_bytes(b"not candidate bytes")

            expected = hashlib.sha256(
                b"a.txt\x001\x00ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb\n"
                b"nested/b.txt\x001\x003e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d\n"
            ).hexdigest()
            self.assertEqual(tree_digest(root), (expected, 2, 2))


if __name__ == "__main__":
    unittest.main()
