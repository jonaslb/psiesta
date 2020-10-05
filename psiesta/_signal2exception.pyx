from libc.signal cimport (
    sighandler_t,
    SIG_DFL,
    signal,
    SIGABRT
)
from contextlib import contextmanager


# There *is* of course similar functionality in Windows, but I haven't bothered
DEF HAS_BACKTRACE = (UNAME_SYSNAME in ("Linux", "Darwin"))


IF HAS_BACKTRACE:
    cdef extern:
        int backtrace(void** buffer, int size)
        char** backtrace_symbols (void *const *buffer, int size)


class SigAbrtError(RuntimeError):
    pass


cdef void signal_handler(int signal):
    IF HAS_BACKTRACE:
        cdef int i
        cdef void *array[10];
        cdef size_t size;
        size = backtrace(array, 10);
        cdef char** text = backtrace_symbols(array, size)
        trace_strings = []
        for i in range(10):
            trace_strings.append((<bytes>text[i]).decode())
        trace = "\n".join(trace_strings)

    if signal == SIGABRT:
        errortext = (
            "Siesta has raised a SIGABRT! This is usually indicative of"
            " catastrophic failure. You need to check the output files in"
            " the calculator directory to see what exactly went wrong."
        )
        IF HAS_BACKTRACE:
            errortext += f"Although, here's a traceback:\n{trace}"
        raise SigAbrtError(errortext)
    else:
        raise NotImplementedError(
            "A signal was raised and given to a handler that doesn't know"
            f" how to handle it. Signal: {signal}"
        )


cdef void disable_sigabrt_raise():
    signal(SIGABRT, SIG_DFL)


cdef void enable_sigabrt_raise():
    signal(SIGABRT, <sighandler_t>signal_handler)


@contextmanager
def raise_on_sigabrt():
    try:
        enable_sigabrt_raise()
        yield
    finally:
        disable_sigabrt_raise()