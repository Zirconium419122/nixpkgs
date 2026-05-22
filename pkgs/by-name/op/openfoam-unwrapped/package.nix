{
  lib,
  stdenv,
  fetchFromGitLab,
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
  scotch,
  symlinkJoin,
}:

stdenv.mkDerivation (attr: {
  pname = "openfoam-unwrapped";
  version = "2512";

  src = fetchFromGitLab {
    owner = "OpenFOAM/core";
    repo = "openfoam";
    tag = "OpenFOAM-v${attr.version}";
    hash = "sha256-uaXA0sFso6W+1jE2/2G0ckQlqRGnP/QBk0aHzP7xTWw=";
  };

  sourceRoot = ".";

  dontUseCmakeConfigure = true;

  dontFixup = true;

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
  ];

  postPatch = let
    scotchCombined = symlinkJoin {
      name = "scotch-combined";
      paths = [ scotch.dev scotch.out ];
    };
  in ''
    patchShebangs .

    substituteInPlace source/etc/config.sh/scotch \
      --replace-fail \
        'SCOTCH_VERSION=scotch_6.1.0' \
        'export SCOTCH_VERSION=scotch-system' \
      --replace-fail \
        'export SCOTCH_ARCH_PATH=$WM_THIRD_PARTY_DIR/platforms/$WM_ARCH$WM_COMPILER$WM_PRECISION_OPTION$WM_LABEL_OPTION/$SCOTCH_VERSION' \
        'export SCOTCH_ARCH_PATH=${scotchCombined}'

    cat source/etc/config.sh/scotch

    export HOME="$PWD/builddir"

    mkdir -p "$HOME/OpenFOAM"
    mkdir -p "$HOME/.OpenFOAM"

    mv source "$HOME/OpenFOAM/OpenFOAM-${attr.version}"
  '';

  buildPhase = ''
    runHook preBuild

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
    cp -r . "$OUT_DIR"

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
