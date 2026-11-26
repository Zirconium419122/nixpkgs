import re
import sys
import tarfile
from pathlib import Path, PurePosixPath


# wmake flattens these files into lnInclude, where both spellings must survive.
# Keep the C++ type names and rename only files and references to their paths.
extensions = {
    "BasicChemistryModel": ("C", "H"),
    "BasicChemistryModelI": ("H",),
    "Barycentric": ("H",),
    "Barycentric2D": ("H",),
    "BarycentricTensor": ("H",),
    "CombustionModel": ("C", "H"),
    "CompactSpatialTensor": ("H",),
    "CompressibleTurbulenceModel": ("C", "H"),
    "DSMCCloud": ("H",),
    "DSMCParcel": ("C", "H"),
    "DiagTensor": ("H",),
    "DiagonalPreconditioner": ("C", "H"),
    "DiagonalSolver": ("C", "H"),
    "Dictionary": ("H",),
    "IncompressibleTurbulenceModel": ("C", "H"),
    "Instant": ("H",),
    "InterfaceCompositionModel": ("C", "H"),
    "KinematicCloud": ("C", "H"),
    "LduInterfaceField": ("H",),
    "LduInterfaceFieldPtrsList": ("H",),
    "LduMatrix": ("C", "H"),
    "LduMatrixATmul": ("C",),
    "LduMatrixOperations": ("C",),
    "LduMatrixPreconditioner": ("C",),
    "LduMatrixSmoother": ("C",),
    "LduMatrixSolver": ("C",),
    "LduMatrixUpdateMatrixInterfaces": ("C",),
    "LeastSquaresGrad": ("C", "H"),
    "LeastSquaresGrads": ("C",),
    "LeastSquaresVectors": ("C", "H"),
    "NoPreconditioner": ("C", "H"),
    "PatchToPatchInterpolation": ("H",),
    "PhaseLimitStabilization": ("C",),
    "PrimitivePatch": ("H",),
    "PrimitivePatchInterpolation": ("H",),
    "Probes": ("C", "H"),
    "ReactingCloud": ("C", "H"),
    "ReactingHeterogeneousCloud": ("C", "H"),
    "ReactingMultiphaseCloud": ("C", "H"),
    "SmoothSolver": ("C", "H"),
    "SolverPerformance": ("C", "H"),
    "SpatialTensor": ("H",),
    "SpatialVector": ("H",),
    "SphericalTensor": ("H",),
    "SphericalTensor2D": ("H",),
    "SprayCloud": ("C", "H"),
    "SymmTensor": ("H",),
    "SymmTensor2D": ("H",),
    "Tensor": ("H",),
    "Tensor2D": ("H",),
    "ThermoCloud": ("C", "H"),
    "TurbulenceModel": ("C", "H"),
    "Vector": ("H",),
    "Vector2D": ("H",),
    "fvcDDt": ("C", "H"),
}
file_names = {
    f"{stem}.{extension}": f"Foam{stem}.{extension}"
    for stem, suffixes in extensions.items()
    for extension in suffixes
}
file_names.update(
    {
        "Test-Tensor2D": "Test-FoamTensor2D",
        "Test-Tensor2D.C": "Test-FoamTensor2D.C",
    }
)
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
path_names = file_names | directory_names

# This case uses two distinct field names, B and b, at runtime as well.
unsupported_tutorial = PurePosixPath(
    "tutorials/combustion/PDRFoam/flamePropagationWithObstacles"
)


def rename_path(path):
    return "/".join(path_names.get(part, part) for part in path.split("/"))


def unpack(archive_path, destination):
    source_files = []
    with tarfile.open(archive_path, "r:gz") as archive:
        members = []
        names = set()
        for member in archive.getmembers():
            path = PurePosixPath(*PurePosixPath(member.name).parts[1:])
            if path == PurePosixPath(".") or path.is_relative_to(unsupported_tutorial):
                continue
            name = rename_path(path.as_posix())
            if name.casefold() in names:
                raise ValueError(f"Case-insensitive source path collision: {name}")
            names.add(name.casefold())
            linkname = rename_path(member.linkname)
            if member.islnk():
                linkname = linkname.split("/", 1)[1]
            members.append(member.replace(name=name, linkname=linkname))
            if member.isfile():
                source_files.append(destination / name)
        archive.extractall(destination, members, filter="data")
    return source_files


def rewrite_references(source_files):
    files = "|".join(map(re.escape, file_names))
    directories = "|".join(map(re.escape, directory_names))
    # File names can appear by themselves in #include directives. Directory
    # names need an adjacent slash, so ordinary C++ identifiers stay intact.
    name_character = r"[\w.+-]"
    references = re.compile(
        (
            rf"(?<!{name_character})(?:{files})(?!{name_character})"
            rf"|(?<!{name_character})(?:{directories})(?=/)"
            rf"|(?<=/)(?:{directories})(?!{name_character})"
        ).encode()
    )
    replacements = {key.encode(): value.encode() for key, value in path_names.items()}
    for path in source_files:
        original = path.read_bytes()
        if b"\0" in original:
            continue
        updated = references.sub(lambda match: replacements[match[0]], original)
        if updated != original:
            path.write_bytes(updated)


if __name__ == "__main__":
    rewrite_references(unpack(sys.argv[1], Path(sys.argv[2])))
