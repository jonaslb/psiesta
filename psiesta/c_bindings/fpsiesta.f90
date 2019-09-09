module fpsiesta
  implicit none
  use mpi
  use fsiesta
  use, intrinsic :: iso_c_binding

  private
  public :: fpsiesta_launch, fpsiesta_forces, fpsiesta_quit

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
    call siesta_launch(f_label, mpi_comm=mpi_comm)
    call siesta_units('Ang', 'eV')
  end subroutine fpsiesta_launch

  subroutine fpsiesta_forces(label, na, xa, e, fa) bind(c)
    character(kind=c_char, len=1), intent(in) :: label
    character(len=:), allocatable :: f_label
    integer(c_int), intent(in) :: na
    real(c_double), intent(inout), dimension(na, 3) :: xa
    real(c_double), intent(out) :: e
    real(c_double), intent(out), dimension(na, 3) :: fa
    f_label = c2fstr(label)
    call siesta_forces(f_label, na, xa, energy=e, fa=fa)
  end subroutine fpsiesta_forces()

  subroutine fpsiesta_quit(label) bind(c)
    character(kind=c_char, len=1), intent(in) :: label
    character(len=:), allocatable :: f_label
    f_label = c2fstr(label)
    call siesta_quit(f_label)
  end subroutine
end module fpsiesta
