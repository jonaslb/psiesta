module fpsiesta
  use, intrinsic :: iso_c_binding
  use mpi
  use fsiesta, only: siesta_launch, siesta_units, siesta_forces, siesta_quit, siesta_get
  use m_energies, only: siesta_fermi_energy => Ef
  use units, only: siesta_eV => eV
  implicit none

  public :: fpsiesta_launch, fpsiesta_forces, fpsiesta_quit
  private

contains
  function c2fstr(s) result(str)
    character(kind=c_char, len=1), intent(in) :: s(*)
    character(len=:), allocatable :: str
    integer n
    n = 1
    do while (s(n) /= c_null_char)
       n = n + 1
    end do
    n = n - 1  ! Don't use nullchar
    allocate(character(len=n) :: str)
    str = transfer(s(1:n), str)
  end function c2fstr

  subroutine fpsiesta_launch(label, mpi_comm) bind(c)
    character(kind=c_char, len=1), intent(in) :: label
    character(len=:), allocatable :: f_label
    integer(c_int), intent(in) :: mpi_comm
    f_label = c2fstr(label)
    call siesta_launch(f_label, 0, mpi_comm)
    call siesta_units('Ang', 'eV')
  end subroutine fpsiesta_launch

  subroutine fpsiesta_forces(label, na, xa, cell, e, fa, stress) bind(c)
    character(kind=c_char, len=1), intent(in) :: label
    character(len=:), allocatable :: f_label
    integer(c_int), intent(in) :: na
    real(c_double), intent(in), dimension(3, na) :: xa
    real(c_double), intent(in), dimension(3, 3) :: cell
    real(c_double), intent(out) :: e
    real(c_double), intent(out), dimension(3, na) :: fa
    real(c_double), intent(out), dimension(3, 3) :: stress
    f_label = c2fstr(label)
    e = 0
    call siesta_forces(f_label, na, xa, cell=cell, energy=e, fa=fa, stress=stress)
  end subroutine fpsiesta_forces

  subroutine fpsiesta_quit(label) bind(c)
    character(kind=c_char, len=1), intent(in) :: label
    character(len=:), allocatable :: f_label
    f_label = c2fstr(label)
    call siesta_quit(f_label)
  end subroutine

  subroutine fpsiesta_run_analyse(label) bind(c)
    character(kind=c_char, len=1), intent(in) :: label
    character(len=:), allocatable :: f_label
    f_label = c2fstr(label)

  end subroutine fpsiesta_run_analyse

  subroutine fpsiesta_get(label, property, value, units) bind(c)
    ! TODO : Siesta currently exposes exactly zero properties through this method.
    ! It is probably better to write bindings directly for each property like fpsiesta_fermi_energy
    character(kind=c_char, len=1), intent(in) :: label, property
    character(len=:), allocatable :: f_label      ! Name of siesta process
    character(len=:), allocatable :: f_property   ! Name of required magnitude
    real(c_double), intent(out)  :: value      ! Value of the magnitude
                                               ! (various dimensions overloaded)
    character(kind=c_char, len=1), intent(out) :: units      ! Name of physical units
    character(len=254) :: f_units
    ! integer(c_int), intent(out) :: unitlen  ! length of units string

    f_label = c2fstr(label)
    f_property = c2fstr(property)
    call siesta_get(f_label, f_property, value, f_units)
    units = trim(f_units) // c_null_char
    ! unitlen = len(units)  ! Fortran knows this, so pass it along for easier handling in C-land?
  end subroutine fpsiesta_get

  subroutine fpsiesta_fermi_energy(label, value) bind(c)
    character(kind=c_char, len=1), intent(in) :: label
    character(len=:), allocatable :: f_label      ! Name of siesta process
    real(c_double), intent(out)  :: value
    f_label = c2fstr(label)  ! not really used here
    value = siesta_fermi_energy / siesta_eV
  end subroutine fpsiesta_fermi_energy
end module fpsiesta
