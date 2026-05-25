{
  lib,
  stdenv,
  openfoam-unwrapped,
  flex,
  openmpi,
  paraview,
  makeWrapper,
}:

stdenv.mkDerivation (attr: {
  pname = "openfoam";
  version = openfoam-unwrapped.version;

  dontUnpack = true;

  buildInputs = [
    openmpi
  ];

  nativeBuildInputs = [
    makeWrapper
  ];

  installPhase = ''
    OUT_DIR="${openfoam-unwrapped}/opt/OpenFOAM-${openfoam-unwrapped.version}"

    wrapDir() {
      local dir="$1"

      for f in "$dir"/*; do
        [ -f "$f" ] || continue
        [ -x "$f" ] || continue

        local name
        name="$(basename "$f")"

        makeWrapper "$f" "$out/bin/$name" \
          --run "
            set +eu

            export PATH='${lib.makeBinPath [
              flex
              paraview
            ]}:$PATH'

            source '$OUT_DIR/etc/bashrc'
          "
      done
    }

    mkdir -p "$out/bin"

    wrapDir "$OUT_DIR/bin"
    wrapDir "$OUT_DIR/platforms/linux64GccDPInt32Opt/bin"
  '';

  meta = openfoam-unwrapped.meta;
})
