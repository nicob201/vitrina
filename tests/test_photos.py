import random
import tempfile
import unittest
from pathlib import Path

from vitrina.photos import PhotoLibrary


def all_paths(lib):
    return [lib.path(i) for i in range(lib.count())]


class PhotoLibraryTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        for name in ("a.jpg", "B.JPEG", "c.png", "d.webp", "e.HEIC", "f.txt", ".hidden.jpg"):
            (self.dir / name).write_bytes(b"")
        (self.dir / "sub").mkdir()
        (self.dir / "sub" / "g.jpg").write_bytes(b"")
        (self.dir / "folder.jpg").mkdir()
        self.lib = PhotoLibrary(self.dir, random.Random(1))
        self.lib.rescan()

    def tearDown(self):
        self._tmp.cleanup()

    def test_only_supported_images(self):
        self.assertEqual(sorted(p.name for p in all_paths(self.lib)), ["B.JPEG", "a.jpg", "c.png", "d.webp"])

    def test_symlink_to_a_non_image_is_ignored(self):
        # foto.jpg -> some private file must not be served to the network.
        with tempfile.TemporaryDirectory() as other:
            secret = Path(other) / "secret.txt"
            secret.write_text("private")
            (self.dir / "foto.jpg").symlink_to(secret)
            self.lib.rescan()
            self.assertNotIn(self.dir / "foto.jpg", all_paths(self.lib))

    def test_symlink_to_an_image_is_kept(self):
        with tempfile.TemporaryDirectory() as other:
            real = Path(other) / "real.png"
            real.write_bytes(b"")
            (self.dir / "link.jpg").symlink_to(real)
            self.lib.rescan()
            self.assertIn(self.dir / "link.jpg", all_paths(self.lib))

    def test_order_is_kept_when_files_do_not_change(self):
        first = all_paths(self.lib)
        self.lib.rescan()
        self.assertEqual(all_paths(self.lib), first)

    def test_new_file_is_picked_up(self):
        (self.dir / "z.jpg").write_bytes(b"")
        self.lib.rescan()
        self.assertEqual(self.lib.count(), 5)
        self.assertIn(self.dir / "z.jpg", all_paths(self.lib))

    def test_deleted_file_is_dropped(self):
        (self.dir / "a.jpg").unlink()
        self.lib.rescan()
        self.assertNotIn(self.dir / "a.jpg", all_paths(self.lib))

    def test_missing_or_unset_folder_is_empty(self):
        for lib in (PhotoLibrary(None), PhotoLibrary(self.dir / "nope")):
            lib.rescan()
            self.assertEqual(lib.count(), 0)
            self.assertIsNone(lib.path(0))

    def test_path_out_of_range_is_none(self):
        for i in (-1, self.lib.count(), 999):
            self.assertIsNone(self.lib.path(i))


if __name__ == "__main__":
    unittest.main()
