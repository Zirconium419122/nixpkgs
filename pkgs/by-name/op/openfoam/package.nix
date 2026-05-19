{
  lib,
  stdenv,
  bash,
  fetchFromGitLab,
  makeWrapper,
  gcc,
  cmake,
  gnumake,
  binutils,
  zlib,
  gnum4,
  boost,
  fftw,
  flex,
  openmpi,
}:

stdenv.mkDerivation (attr: {
  pname = "OpenFOAM";
  version = "2512";

  src = fetchFromGitLab {
    owner = "OpenFOAM/core";
    repo = "openfoam";
    tag = "OpenFOAM-v${attr.version}";
    hash = "sha256-uaXA0sFso6W+1jE2/2G0ckQlqRGnP/QBk0aHzP7xTWw=";
  };

  sourceRoot = ".";

  dontUseCmakeConfigure = true;

  buildInputs = [
    zlib
    boost
    fftw
    openmpi
    openmpi.dev
  ];

  nativeBuildInputs = [
    gcc
    cmake
    gnumake
    binutils
    flex
    gnum4
    openmpi.dev
    makeWrapper
  ];

  postPatch = ''
    patchShebangs .

    export HOME="$PWD/builddir"

    mkdir -p "$HOME/OpenFOAM"
    mkdir -p "$HOME/.OpenFOAM"

    mv source "$HOME/OpenFOAM/OpenFOAM-${attr.version}"
  '';

  buildPhase = ''
    runHook preBuild

    set -x

    cd "$HOME/OpenFOAM/OpenFOAM-${attr.version}"

    set +eu
    source ./etc/bashrc
    set -eu

    ./Allwmake -j "$NIX_BUILD_CORES" -q -s

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    OUT_DIR="$out/opt/OpenFOAM-${attr.version}"

    mkdir -p "$OUT_DIR"

    cp -r bin "$OUT_DIR"
    cp -r platforms "$OUT_DIR"
    cp -r etc "$OUT_DIR"
    cp -r applications "$OUT_DIR"
    cp -r src "$OUT_DIR"
    cp -r wmake "$OUT_DIR"
    cp -r doc "$OUT_DIR"
    cp -r tutorials "$OUT_DIR"

    mkdir -p "$out/bin"
    for p in "$OUT_DIR"/bin/*; do
      name="$(basename "$p")"
      makeWrapper "$p" "$out/bin/$name" \
        --set WM_PROJECT_DIR "$OUT_DIR" \
        --set WM_PROJECT_VERSION "${attr.version}" \
        --set FOAM_ETC "$OUT_DIR/etc" \
        --set FOAM_APPBIN "$OUT_DIR/platforms/linux64GccDPInt32Opt/bin" \
        --set FOAM_LIBBIN "$OUT_DIR/platforms/linux64GccDPInt32Opt/lib" \
        --set WM_THIRD_PARTY_DIR "$OUT_DIR/ThirdParty"
    done

    cat > $out/bin/openfoam <<EOF
      #!/${bash}/bin/bash
      export WM_PROJECT_DIR=$OUT_DIR
      export WM_PROJECT_VERSION=${attr.version}
      export FOAM_ETC=\$WM_PROJECT_DIR/etc
      export FOAM_APPBIN=\$WM_PROJECT_DIR/platforms/linux64GccDPInt32Opt/bin
      export FOAM_LIBBIN=\$WM_PROJECT_DIR/platforms/linux64GccDPInt32Opt/lib

      exec "\$@"
    EOF

    chmod +x $out/bin/openfoam

    runHook postInstall
  '';

  meta = {
    description = "It takes 30 minutes to compile...";
    homepage = "https://openfoam.com";
    license = lib.licenses.gpl3;
    maintainers = with lib.maintainers; [ Zirconium419122 ];
    platforms = with lib.platforms; unix;
  };
})
