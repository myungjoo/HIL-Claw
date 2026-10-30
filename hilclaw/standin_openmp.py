"""The check that the ``cpu_standin`` image builds and starts an OpenMP program (ADR-0188 decision 4).

``ARCHITECTURE/decisions/ADR-0188-od18-standin-openmp-in-the-build-set.md``
puts ``-fopenmp`` into the flags of every ``cpu_standin`` kernel build, so an
image without a usable OpenMP builds no kernel at all. :func:`check` finds that
out before a run starts: in a new temporary directory it writes
:data:`SOURCE`, builds it in one new container of the image with
:data:`hilclaw.standin_settings.FLAGS` and
:data:`hilclaw.standin_settings.TRAILING_FLAGS`, starts the result in a second
new container, and removes the directory. Both containers have the options of
ADR-0144 through :func:`hilclaw.standin_container.run_in_container`, one per
build and per process as its decision 3 says.

What this module does not do: it installs, pulls, builds or changes no image
and nothing else on the machine (NFR-4, FR-4); it reads no output of the
containers, so no text of the image reaches a message; it records no thread
count and no runtime version; and it is called only by :mod:`hilclaw.nightly`
(a check at other instance starts is a later slice, ADR-0188 decision 4).
"""

import tempfile
from pathlib import Path

from hilclaw import standin_check, standin_container, standin_settings

SOURCE_NAME = "openmp_probe.c"
"""File name of the probe's source in the temporary directory."""

EXECUTABLE_NAME = "openmp_probe"
"""File name of the probe's executable in the temporary directory."""

SOURCE = b"""\
#include <omp.h>
#ifndef _OPENMP
#error "-fopenmp did not take effect"
#endif
int main(void)
{
    int counted = 0;
    int team = 0;
#pragma omp parallel reduction(+ : counted)
    {
        counted += 1;
#pragma omp master
        team = omp_get_num_threads();
    }
    return team >= 1 && counted == team && omp_get_max_threads() >= 1 ? 0 : 1;
}
"""
"""The probe: status 0 when a parallel region ran with the runtime's own team."""

_NOT_STARTED = (
    OSError,
    LookupError,
    ValueError,
    standin_container.NoNumericUserError,
)


def check(
    image,
    *,
    timeout_s=standin_settings.BUILD_TIME_LIMIT_S,
    removal_timeout_s=standin_check.REMOVAL_TIMEOUT_S,
):
    """Return ``None`` when ``image`` builds and starts the probe, else why it does not.

    ``timeout_s`` is the time limit of each of the two containers and
    ``removal_timeout_s`` that of a forced removal after it. The answer is a
    ``str`` for :func:`message`: the step, ``build`` or ``start``, and what
    happened to it, a status other than 0 (the client's 125 to 127 among
    them), no end within the limit, or a container that could not be started
    or failed after its start, by the class of the error. It holds no text of
    the image or of the containers' output. The directory is removed in every
    case; after a timeout the container is removed by force, and a removal that
    did not succeed is added to the answer.
    """
    steps = (
        (
            "build",
            standin_check.COMPILER,
            (
                *standin_settings.FLAGS,
                standin_check.in_container(SOURCE_NAME),
                *standin_settings.TRAILING_FLAGS,
                "-o",
                standin_check.in_container(EXECUTABLE_NAME),
            ),
        ),
        ("start", standin_check.in_container(EXECUTABLE_NAME), ()),
    )
    try:
        with tempfile.TemporaryDirectory() as build_dir:
            (Path(build_dir) / SOURCE_NAME).write_bytes(SOURCE)
            for step, program, arguments in steps:
                failure = _step(
                    image,
                    build_dir,
                    step,
                    program,
                    arguments,
                    timeout_s,
                    removal_timeout_s,
                )
                if failure is not None:
                    return failure
    except OSError as error:
        return f"the temporary directory failed ({type(error).__name__})"
    return None


def message(failure):
    """Return what the user reads for the answer ``failure`` of :func:`check`."""
    return (
        "the image named by HILCLAW_STANDIN_IMAGE was not shown to build and start "
        f"an OpenMP program: {failure}. Every cpu_standin kernel build takes -fopenmp "
        "(ADR-0188), so without OpenMP no kernel of a run builds. Needed in that image: a "
        "clang that accepts -fopenmp, <omp.h> and an OpenMP runtime it links. "
        "Nothing was installed or changed; add them to the image, or name another "
        "image, and start again."
    )


def _step(image, build_dir, step, program, arguments, timeout_s, removal_timeout_s):
    try:
        result = standin_container.run_in_container(
            image,
            build_dir,
            program,
            arguments,
            timeout_s=timeout_s,
            removal_timeout_s=removal_timeout_s,
        )
    except _NOT_STARTED as error:
        reason = type(error).__name__
        name = getattr(error, "container_name", None)
        if name is not None:
            return f"{step} failed after its start ({reason}); {name} may remain"
        return f"{step} could not be started ({reason})"
    if result.timed_out:
        answer = f"{step} did not finish within {timeout_s} s"
        removal = result.removal
        if removal.timed_out or removal.returncode != 0:
            answer += f"; the forced removal of {result.name} did not succeed"
        return answer
    if result.returncode != 0:
        return f"{step} ended with status {result.returncode}"
    return None
