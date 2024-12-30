pkg_check_modules(SCALAPACK REQUIRED IMPORTED_TARGET scalapack)

# Create alias for consistency (expected by Siesta..)
add_library(scalapack ALIAS PkgConfig::SCALAPACK)
add_library(SCALAPACK::SCALAPACK ALIAS PkgConfig::SCALAPACK)
