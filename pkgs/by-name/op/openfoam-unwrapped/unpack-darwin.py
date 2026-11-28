import re
import sys
import tarfile
from collections import defaultdict
from pathlib import Path, PurePosixPath


source_directories = {"applications", "modules", "src"}
source_suffixes = {
    ".c", ".cc", ".cpp", ".cxx", ".cver",
    ".h", ".hh", ".hpp", ".hxx", ".i", ".inl", ".tcc", ".txx",
    ".l", ".y",
}
directory_names = {
    name: f"Foam{name}"
    for name in (
        "BasicChemistryModel",
        "CombustionModel",
        "InterfaceCompositionModel",
        "LduMatrix",
        "LeastSquaresGrad",
        "PrimitivePatch",
        "Reactions",
        "Tensor2D",
    )
}
# This case uses two distinct field names, B and b, at runtime as well.
unsupported_tutorial = PurePosixPath(
    "tutorials/combustion/PDRFoam/flamePropagationWithObstacles"
)


def find_file_renames(paths):
    # Clang searches several lnInclude directories. Case-only spellings can
    # shadow each other there even when they are in distinct source trees.
    spellings = defaultdict(set)
    for path in paths:
        if (
            path.parts
            and path.parts[0] in source_directories
            and path.suffix.casefold() in source_suffixes
        ):
            spellings[path.name.casefold()].add(path.name)

    # The tensor tests also install executables whose names differ only by case.
    file_names = {
        "Test-Tensor2D": "Test-FoamTensor2D",
        "Test-Tensor2D.C": "Test-FoamTensor2D.C",
    }
    used_names = set(spellings)
    for names in spellings.values():
        for name in sorted(names)[:-1]:
            renamed = file_names.get(name, f"Foam{name}")
            if renamed.casefold() in used_names:
                raise ValueError(f"Cannot rename {name}: {renamed} is already used")
            used_names.add(renamed.casefold())
            file_names[name] = renamed
    return file_names


def rename_path(path, path_names):
    return "/".join(path_names.get(part, part) for part in path.split("/"))


def unpack(archive_path, destination):
    source_files = []
    with tarfile.open(archive_path, "r:gz") as archive:
        entries = [
            (member, PurePosixPath(*PurePosixPath(member.name).parts[1:]))
            for member in archive.getmembers()
        ]
        file_names = find_file_renames(
            path for member, path in entries if not member.isdir()
        )
        path_names = file_names | directory_names
        members = []
        names = set()
        for member, path in entries:
            if path == PurePosixPath(".") or path.is_relative_to(unsupported_tutorial):
                continue
            name = rename_path(path.as_posix(), path_names)
            if name.casefold() in names:
                raise ValueError(f"Case-insensitive source path collision: {name}")
            names.add(name.casefold())
            linkname = rename_path(member.linkname, path_names)
            if member.islnk():
                linkname = linkname.split("/", 1)[1]
            members.append(member.replace(name=name, linkname=linkname))
            if member.isfile():
                source_files.append(destination / name)
        archive.extractall(destination, members, filter="data")
    rewrite_references(source_files, file_names, path_names)


def rewrite_references(source_files, file_names, path_names):
    files = "|".join(map(re.escape, file_names))
    directories = "|".join(map(re.escape, directory_names))
    # File names can appear by themselves in #include directives. Directory
    # names need an adjacent slash, so ordinary C++ identifiers stay intact.
    # Leave token-pasted fragments such as Cloud.H in basic ## x ## Cloud.H.
    name_character = r"[\w.+-]"
    references = re.compile(
        (
            rf"##(?:[ \t]|\\\r?\n)*(?:{files})(?!{name_character})"
            rf"|(?<!{name_character})(?:{files})(?!{name_character})"
            rf"|(?<!{name_character})(?:{directories})(?=/)"
            rf"|(?<=/)(?:{directories})(?!{name_character})"
        ).encode()
    )
    replacements = {key.encode(): value.encode() for key, value in path_names.items()}
    for path in source_files:
        original = path.read_bytes()
        if b"\0" in original:
            continue
        updated = references.sub(lambda match: replacements.get(match[0], match[0]), original)
        if updated != original:
            path.write_bytes(updated)


if __name__ == "__main__":
    unpack(sys.argv[1], Path(sys.argv[2]))
