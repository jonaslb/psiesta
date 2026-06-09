{
  description = "PSiesta development shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { nixpkgs, ... }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              stdenv.cc
              gfortran
              cmake
              ninja
              pkg-config
              git

              openmpi
              blas
              lapack
              scalapack
              curl
              hdf5
              netcdf
              netcdffortran
              fftw
              libxc
              readline
              zlib

              uv
            ];

            shellHook = ''
              export CC=mpicc
              export CXX=mpicxx
              export FC=mpifort
              export F77=mpifort
              export F90=mpifort
              export LD_LIBRARY_PATH=${pkgs.openmpi}/lib:$LD_LIBRARY_PATH
            '';
          };
        });
    };
}
