"""Exercise release build configuration and the final ZIP/checksum contract."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "release"))
from build_cross_platform import archive_payload, build_intel_torch


class ReleaseBuildTests(unittest.TestCase):
    def test_intel_torch_build_preserves_version_and_uses_supported_apple_blas(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            python = work / "bundled python"
            calls = []

            def run(*command, **kwargs):
                calls.append((command, kwargs))
                if command[1:3] == ("setup.py", "bdist_wheel"):
                    wheel = kwargs["cwd"] / "dist/torch-2.11.0-cp312-cp312-macosx_14_0_x86_64.whl"
                    wheel.parent.mkdir(parents=True)
                    wheel.write_bytes(b"fixture")

            with patch("build_cross_platform.run", side_effect=run), \
                 patch.dict(os.environ, {"BLAS": "Accelerate", "USE_CUDA": "1", "USE_OPENMP": "1"}):
                build_intel_torch(python, work)
            clone, requirements, build, install = calls
            self.assertIn("v2.11.0", clone[0])
            self.assertIn("--recursive", clone[0])
            self.assertEqual(requirements[1]["env"]["PIP_CONSTRAINT"],
                             str(ROOT / "release/macos-intel-constraints.txt"))
            environment = build[1]["env"]
            # v2.11.0 cmake/Dependencies.cmake accepts vecLib, not Accelerate.
            self.assertEqual(environment["BLAS"], "vecLib")
            for feature in ("USE_CUDA", "USE_MPS", "USE_OPENMP", "USE_MKL", "USE_MKLDNN", "USE_DISTRIBUTED"):
                self.assertEqual(environment[feature], "0")
            self.assertEqual(environment["PYTORCH_BUILD_VERSION"], "2.11.0")
            self.assertEqual(install[0][:4], (python, "-m", "pip", "install"))
            self.assertTrue(install[0][-1].is_file())

    def test_intel_build_requires_exactly_one_wheel_before_installing(self):
        for count in (0, 2):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as temporary:
                work = Path(temporary)
                wheels = work / "pytorch/dist"
                wheels.mkdir(parents=True)
                for index in range(count):
                    (wheels / f"torch-{index}.whl").write_bytes(b"fixture")
                with patch("build_cross_platform.run") as run:
                    with self.assertRaisesRegex(RuntimeError, "exactly one wheel"):
                        build_intel_torch(work / "python", work)
                self.assertEqual(run.call_count, 3)

    def test_windows_zip_layout_checksum_and_existing_output_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            payload = Path(temporary) / "app with spaces"
            payload.mkdir()
            (payload / "nam2zoom.exe").write_bytes(b"fixture executable")
            archive_payload(payload, "win-x64")
            archive = payload.with_suffix(".zip")
            with zipfile.ZipFile(archive) as zipped:
                self.assertIsNone(zipped.testzip())
                self.assertEqual(zipped.read("app with spaces/nam2zoom.exe"), b"fixture executable")
            expected = hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
            self.assertEqual(Path(str(archive) + ".sha256").read_text(), expected)
            with self.assertRaises(FileExistsError):
                archive_payload(payload, "win-x64")
