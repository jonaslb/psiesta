project(
    'PSiesta',
    version: '0.3.0',
    default_options: [
        'mpi=enabled'  # Subprojects can switch this, but we require it
    ]
)
add_languages('c', 'fortran', required: true)

py_mod = import('python')
py3 = py_mod.find_installation('python3')
py3_dep = py3.dependency(required: true)

py_version = py3.language_version()
if py_version.version_compare('< 3.6')
    error('Old python detected')
endif

cython = find_program('cython', required: true)

mpi_dep = dependency('mpi', language: 'fortran', required: true)

libsiesta_dep = dependency('siesta', required: false)
if not libsiesta_dep.found()
    siestaproj = subproject('siesta')
    libsiesta_dep = siestaproj.get_variable('siesta_dep')
endif

subdir('psiesta')
