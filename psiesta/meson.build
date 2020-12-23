subdir('c_bindings')

psiesta_c = custom_target(
    '_psiesta_pyx',
    output : '_psiesta.c',
    input : '_psiesta.pyx',
    command : [cython, '-3', '@INPUT@', '-o', '@OUTPUT@'],
)

psiesta_ext = py3.extension_module(
    '_psiesta',
    [psiesta_c, fpsiesta_files],
    subdir: 'psiesta',
    install: true,
    dependencies: [py3_dep, mpi_dep, libsiesta_dep]
)

pyfiles = files(
    '__init__.py',
    'ase.py',
    'psiesta.py',
)

py3.install_sources(pyfiles, subdir: 'psiesta', pure: false)
