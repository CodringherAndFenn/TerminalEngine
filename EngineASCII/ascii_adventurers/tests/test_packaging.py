import os
import subprocess
import sys
import unittest
from pathlib import Path

from ascii_adventurers.meta import files

GAME = Path(__file__).resolve().parent.parent


class SaveFolderTest(unittest.TestCase):
    def test_per_os_user_folders(self):
        home = Path("/home/u")
        self.assertEqual(files.user_data_dir("win32", {"APPDATA": "C:/Users/u/AppData/Roaming"}, home),
                         Path("C:/Users/u/AppData/Roaming/AsciiAdventurers"))
        self.assertEqual(files.user_data_dir("darwin", {}, home),
                         home / "Library/Application Support/AsciiAdventurers")
        self.assertEqual(files.user_data_dir("linux", {}, home),
                         home / ".local/share/AsciiAdventurers")
        self.assertEqual(files.user_data_dir("linux", {"XDG_DATA_HOME": "/data"}, home),
                         Path("/data/AsciiAdventurers"))

    def test_source_saves_in_the_folder_builds_in_the_user_folder(self):
        self.assertEqual(files.save_dir(frozen=False, env={}), GAME / "save")
        self.assertEqual(files.save_dir(frozen=True, env={"XDG_DATA_HOME": "/data"}).name,
                         "AsciiAdventurers")
        self.assertEqual(files.save_dir(frozen=True, env={"ASCII_ADVENTURERS_SAVE_DIR": "/tmp/x"}),
                         Path("/tmp/x"))


class BuildInputsTest(unittest.TestCase):
    def test_every_bundled_file_exists(self):
        sys.path.insert(0, str(GAME / "packaging"))
        try:
            import build
        finally:
            sys.path.pop(0)
        args = build.pyinstaller_args()
        self.assertTrue(Path(args[0]).is_file())
        for i, a in enumerate(args):
            if a == "--add-data":
                src = args[i + 1].rsplit(build.SEP, 1)[0]
                self.assertTrue(Path(src).exists(), src)


class SmokeRunTest(unittest.TestCase):
    def test_the_launcher_plays_a_run(self):
        env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
                   ASCII_ADVENTURERS_SAVE_DIR=str(GAME / ".cache" / "smoke-save"))
        out = subprocess.run([sys.executable, str(GAME / "run.py"), "--smoke", "1.5", "--ghosts", "1"],
                             env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        self.assertIn("smoke ok", out.stdout)
        self.assertFalse((GAME / ".cache" / "smoke-save").exists())   # saved nothing


if __name__ == "__main__":
    unittest.main()
