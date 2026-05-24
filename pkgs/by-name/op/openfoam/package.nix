{
  lib,
  stdenv,
  openfoam-unwrapped,
  flex,
  gnumake,
  openmpi,
  paraview,
  makeWrapper,
}:

stdenv.mkDerivation (attr: {
  pname = "openfoam";
  version = openfoam-unwrapped.version;

  src = openfoam-unwrapped;

  buildInputs = [
    openmpi
  ];

  nativeBuildInputs = [
    makeWrapper
  ];

  installPhase = ''
    OUT_DIR="$src/opt/OpenFOAM-${openfoam-unwrapped.version}"

    wrapDir() {
      local dir="$1"

      for p in "$dir"/*; do
        [ -f "$p" ] || continue
        [ -x "$p" ] || continue

        local name
        name="$(basename "$p")"

        makeWrapper "$p" "$out/bin/$name" \
          --run "
            set +eu

            export PATH='${lib.makeBinPath [
              flex
              gnumake
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
