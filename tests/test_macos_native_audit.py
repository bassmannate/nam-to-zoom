"""Audit real Mach-O commands, including IDs, universal slices and corrupt files."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "release"))
from macos_native import macho_libraries, audit_macos_bundle, CPU


def library_command(command, name, endian="<"):
    encoded = name.encode() + b"\0"
    length = (24 + len(encoded) + 7) // 8 * 8
    return struct.pack(endian + "6I", command, length, 24, 0, 0, 0) + encoded.ljust(length - 24, b"\0")


def thin(cpu, commands, endian="<", bits=64):
    table = b"".join(commands)
    header = struct.pack(endian + "7I", 0xfeedfacf if bits == 64 else 0xfeedface,
                         cpu, 0, 6, len(commands), len(table), 0)
    return header + (bytes(4) if bits == 64 else b"") + table


def universal(slices, endian=">", bits=32):
    entry_size = 32 if bits == 64 else 20
    offset = 8 + len(slices) * entry_size
    entries, payload = [], []
    for cpu, value in slices:
        fields = (cpu, 0, offset, len(value), 0) + ((0,) if bits == 64 else ())
        entries.append(struct.pack(endian + ("IIQQII" if bits == 64 else "IIIII"), *fields))
        payload.append(value)
        offset += len(value)
    return struct.pack(endian + "II", 0xcafebabf if bits == 64 else 0xcafebabe, len(slices)) + b"".join(entries + payload)


class MacosNativeAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "app with spaces"
        self.root.mkdir()

    def write(self, value, name="lib.dylib"):
        path = self.root / name
        path.write_bytes(value)
        return path

    def test_avalonia_install_id_is_not_a_load_dependency(self):
        identity = "/usr/local/lib/libAvalonia.Native.OSX.dylib"
        dependencies = ["/usr/lib/libSystem.B.dylib", "@rpath/libexample.dylib",
                        "@loader_path/../lib/libpython3.12.dylib", "@executable_path/libtest.dylib",
                        "/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit"]
        commands = [library_command(0xd, identity)] + [library_command(0xc, name) for name in dependencies]
        path = self.write(universal([(cpu, thin(cpu, commands)) for cpu in CPU.values()]))
        self.assertEqual(macho_libraries(path), [(cpu, tuple(dependencies)) for cpu in CPU.values()])
        for rid in CPU:
            audit_macos_bundle(self.root, rid)

    def test_real_load_of_absolute_id_still_fails(self):
        name = "/usr/local/lib/libAvalonia.Native.OSX.dylib"
        self.write(thin(CPU["osx-arm64"], [library_command(0xd, name), library_command(0xc, name)]))
        with self.assertRaisesRegex(RuntimeError, "Nonportable native dependency"):
            audit_macos_bundle(self.root, "osx-arm64")

    def test_bad_dependencies_in_second_slice_and_all_load_types(self):
        commands = [library_command(command, f"/opt/homebrew/build (local)/lib{command}.dylib")
                    for command in (0xc, 0x80000018, 0x8000001f, 0x20, 0x80000023)]
        self.write(universal([(CPU["osx-x64"], thin(CPU["osx-x64"], [])),
                              (CPU["osx-arm64"], thin(CPU["osx-arm64"], commands))]))
        with self.assertRaises(RuntimeError) as error:
            audit_macos_bundle(self.root, "osx-arm64")
        self.assertEqual(str(error.exception).count("Nonportable native dependency"), 5)
        self.assertIn("build (local)", str(error.exception))

    def test_wrong_architecture_is_rejected(self):
        self.write(thin(CPU["osx-x64"], []))
        with self.assertRaisesRegex(RuntimeError, "Missing osx-arm64 architecture"):
            audit_macos_bundle(self.root, "osx-arm64")

    def test_byte_orders_and_header_formats(self):
        for endian in ("<", ">"):
            for bits in (32, 64):
                with self.subTest(endian=endian, bits=bits):
                    cpu = CPU["osx-x64"]
                    value = thin(cpu, [library_command(0xc, "/usr/lib/libSystem.B.dylib", endian)], endian, bits)
                    path = self.write(universal([(cpu, value)], endian, bits))
                    self.assertEqual(macho_libraries(path), [(cpu, ("/usr/lib/libSystem.B.dylib",))])

    def test_truncated_or_corrupt_commands_fail_closed(self):
        cpu = CPU["osx-arm64"]
        command = library_command(0xc, "/usr/lib/libSystem.B.dylib")
        corrupt = [thin(cpu, [command])[:-1], thin(cpu, [struct.pack("<II", 0xc, 0)]),
                   thin(cpu, [struct.pack("<6I", 0xc, 24, 999, 0, 0, 0)]),
                   universal([(cpu, thin(cpu, []))])[:-1],
                   universal([(CPU["osx-x64"], thin(cpu, []))])]
        for value in corrupt:
            with self.subTest(value=value[:8]):
                path = self.write(value)
                with self.assertRaises(ValueError):
                    macho_libraries(path)
                with self.assertRaises(RuntimeError):
                    audit_macos_bundle(self.root, "osx-arm64")

    def test_non_native_files_are_ignored_but_empty_bundle_fails(self):
        self.assertEqual(macho_libraries(self.write(b"plain text", "README.md")), [])
        with self.assertRaisesRegex(RuntimeError, "No Mach-O"):
            audit_macos_bundle(self.root, "osx-arm64")


if __name__ == "__main__":
    unittest.main()
