def test_imports_compiled_extension():
    import psiesta
    import psiesta._psiesta

    assert psiesta.FilePSiesta is not None
    assert psiesta._psiesta.FSiesta is not None
