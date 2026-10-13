"""Audit actual Mach-O load commands on any build host, including Windows."""
import struct
from pathlib import Path


THIN = {b"\xce\xfa\xed\xfe": ("<", 28), b"\xfe\xed\xfa\xce": (">", 28),
        b"\xcf\xfa\xed\xfe": ("<", 32), b"\xfe\xed\xfa\xcf": (">", 32)}
FAT = {b"\xca\xfe\xba\xbe": (">", 20), b"\xbe\xba\xfe\xca": ("<", 20),
       b"\xca\xfe\xba\xbf": (">", 32), b"\xbf\xba\xfe\xca": ("<", 32)}
LOAD_DYLIB = {0xc, 0x80000018, 0x8000001f, 0x20, 0x80000023}
CPU = {"osx-x64": 0x01000007, "osx-arm64": 0x0100000c}


def macho_libraries(path):
    """Return (CPU type, loaded library names) for each slice; ignore LC_ID_DYLIB.

    A dylib's own ID is metadata, not a request to load another file. Reading
    commands directly also avoids filename/architecture headers in otool output.
    Only headers and load commands are read, not large native-library payloads.
    """
    path = Path(path)
    size = path.stat().st_size
    with path.open("rb") as stream:
        def read_at(offset, count):
            if offset < 0 or count < 0 or offset + count > size:
                raise ValueError(f"Truncated Mach-O file: {path}")
            stream.seek(offset)
            value = stream.read(count)
            if len(value) != count:
                raise ValueError(f"Truncated Mach-O file: {path}")
            return value

        magic = stream.read(4)
        if magic in FAT:
            endian, entry_size = FAT[magic]
            count = struct.unpack(endian + "I", read_at(4, 4))[0]
            table = read_at(8, count * entry_size)
            slices = []
            for index in range(count):
                record = struct.unpack_from(endian + ("IIQQII" if entry_size == 32 else "IIIII"),
                                            table, index * entry_size)
                slices.append((record[2], record[3], record[0]))
            if not slices:
                raise ValueError(f"Empty Mach-O universal file: {path}")
        elif magic in THIN:
            slices = [(0, size, None)]
        else:
            return []
        result = []
        for offset, length, expected_cpu in slices:
            if offset + length > size or length < 28:
                raise ValueError(f"Invalid Mach-O slice: {path}")
            magic = read_at(offset, 4)
            if magic not in THIN:
                raise ValueError(f"Invalid Mach-O slice header: {path}")
            endian, header_size = THIN[magic]
            header = read_at(offset, header_size)
            cpu, _, _, count, command_bytes = struct.unpack_from(endian + "5I", header, 4)
            if expected_cpu is not None and cpu != expected_cpu:
                raise ValueError(f"Mach-O slice CPU mismatch: {path}")
            if header_size + command_bytes > length or count * 8 > command_bytes:
                raise ValueError(f"Invalid Mach-O load command table: {path}")
            commands = read_at(offset + header_size, command_bytes)
            cursor, libraries = 0, []
            for _ in range(count):
                if cursor + 8 > len(commands):
                    raise ValueError(f"Truncated Mach-O load command: {path}")
                command, command_size = struct.unpack_from(endian + "II", commands, cursor)
                if command_size < 8 or cursor + command_size > len(commands):
                    raise ValueError(f"Invalid Mach-O load command size: {path}")
                if command in LOAD_DYLIB:
                    if command_size < 24:
                        raise ValueError(f"Invalid Mach-O dylib command: {path}")
                    name_offset = struct.unpack_from(endian + "I", commands, cursor + 8)[0]
                    if not 24 <= name_offset < command_size:
                        raise ValueError(f"Invalid Mach-O library name offset: {path}")
                    name = commands[cursor + name_offset:cursor + command_size]
                    if b"\0" not in name or name.startswith(b"\0"):
                        raise ValueError(f"Invalid Mach-O library name: {path}")
                    libraries.append(name.split(b"\0", 1)[0].decode("utf-8"))
                cursor += command_size
            if cursor != command_bytes:
                raise ValueError(f"Mach-O load command size mismatch: {path}")
            result.append((cpu, tuple(libraries)))
        return result


def audit_macos_bundle(root, rid):
    """Report every wrong-architecture or external absolute load dependency."""
    problems, native_count = [], 0
    for path in Path(root).rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            slices = macho_libraries(path)
        except (ValueError, UnicodeError) as error:
            problems.append(str(error))
            continue
        if not slices:
            continue
        native_count += 1
        if CPU[rid] not in {cpu for cpu, _ in slices}:
            problems.append(f"Missing {rid} architecture: {path}")
        for _, libraries in slices:
            for name in libraries:
                if name.startswith("/") and not name.startswith(("/usr/lib/", "/System/Library/")):
                    problems.append(f"Nonportable native dependency: {path}: {name}")
    if problems:
        raise RuntimeError("\n".join(dict.fromkeys(problems)))
    if not native_count:
        raise RuntimeError(f"No Mach-O binaries found: {root}")
    print(f"Mach-O architectures and native dependencies: {native_count} files PASS", flush=True)
