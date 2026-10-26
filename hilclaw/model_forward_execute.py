"""Build-and-run path of the bf16 forward pass of ADR-0166: check, builds, one run.

``ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md`` is the rule
(decisions 4, 6 and 7, code slice 5), with
``ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`` (decision 3
"Loading", decisions 5 and 6). This module joins
:mod:`hilclaw.model_forward_check`, :mod:`hilclaw.model_build` and
:mod:`hilclaw.model_forward_run`. :func:`execute` takes these steps, in order:

1. The whole-generation check of :func:`hilclaw.model_forward_check.check` at
   the dtype ``"bf16"``. If its result is not ``ok``, the result carries it
   and nothing is built, written or started: no kernel, kernel unfit and
   invalid input of ADR-0153 decision 5.
2. The distinct kernels of the check's ``calls``, in the order they first
   appear there; kernel ``i`` is library ``i`` of the program's command line.
3. The per-pass library table of :func:`hilclaw.model_forward_run.encode_input`:
   for each call site and pass, the index of the kernel the check bound to
   that call site's shape at that pass.
4. A build directory of its own outside both checkouts, made and removed as
   :func:`hilclaw.model_execute.execute` does; each kernel is built with
   :func:`hilclaw.model_build.build_kernel_library`, then the forward program
   with :func:`hilclaw.model_build.build_forward_program`. The first failed
   build is the outcome **build failed**, a
   :class:`hilclaw.model_execute.BuildFailed`; nothing after it is built or
   run.
5. The input file is written with
   :func:`hilclaw.model_forward_run.encode_input` and the program is run once
   with :func:`hilclaw.model_forward_run.run_forward_program`; a run that
   failed is the outcome **run failed**, carried by its
   :class:`hilclaw.model_forward_run.ForwardProgramResult` as returned.

Conventions of this module (readings of ADR-0166, not rules of the record):

- Two kernels are the same when they are the same object or compare equal as
  :class:`hilclaw.model_binding.KernelReference` values (sources, contract
  and flags): equality, not hashing, since a ``contract`` may be a ``dict``.
  Two references to one source file spelled differently are two kernels and
  are built twice.
- The shape of call site s at pass p is the one the ``*_shape`` function of
  :mod:`hilclaw.model_binding` gives for that pass: T = S rows at pass 0 and
  1 row after, ``lm_head`` 1 row at every pass for ``"last"``, and ``sdpa``
  over l = P + T positions (S at pass 0, S + p at pass p). After an ``ok``
  check every such shape is among the ``calls``; one that is not raises
  :class:`KeyError`, an error of this module, not an outcome.
- ``given`` ``None`` (the generation mode) or a ``given`` that is no sequence
  is handed to the check with ``generation_length`` 0, since it gives no
  length; the check reports or raises it.
- A ``program_flags`` item that holds ``HILCLAW_MODEL_BF16`` is not refused:
  ``model_forward.c`` reads no macro, so it cannot select anything there.
- The build directory, its removal and the argument checks of ``prefix``,
  ``parent`` and ``keep_out`` are those of :mod:`hilclaw.model_execute`,
  reused: a removal that fails or is refused raises nothing and shows as
  ``removed`` false.

What this module does not do: it has no generation mode or token selection rule
(ADR-0176 decision 5, a later code slice) and no model-level reference or
tolerance, which are :mod:`hilclaw.model_reference`'s (ADR-0176); it gives no
default to any model parameter, RoPE constant (HQ-0070) or time limit, and sets
no cache capacity; it chooses no flag of a kernel or of the program, no
container and no environment; it casts no array; it has no fallback to another
kernel; it stores, keeps or retries nothing; and it writes nothing outside its
build directory.
"""

import os
import tempfile
from typing import NamedTuple

from hilclaw import model_binding, model_build, model_forward_check, model_forward_run
from hilclaw.model_execute import (
    BuildFailed,
    _checked_keep_out,
    _checked_parent,
    _checked_prefix,
    _is_sequence,
    _remove,
)

PREFIX = "hilclaw-forward-"
"""Name prefix of every build directory this module makes."""

_PROGRAM_NAME = "model_forward"
_INPUT_NAME = "input.bin"
_SHAPES = {
    **dict.fromkeys(model_binding.CALL_SITES, model_binding.gemm_shape),
    **dict.fromkeys(model_binding.RMSNORM_CALL_SITES, model_binding.rmsnorm_shape),
    **dict.fromkeys(
        model_binding.ELEMENTWISE_ADD_CALL_SITES, model_binding.elementwise_add_shape
    ),
    **dict.fromkeys(model_binding.SWIGLU_CALL_SITES, model_binding.swiglu_shape),
    **dict.fromkeys(model_binding.ROPE_CALL_SITES, model_binding.rope_shape),
}


class ForwardExecution(NamedTuple):
    """Outcome of one :func:`execute` call.

    ``check`` is the :class:`hilclaw.model_binding.BindingCheck` of the
    whole-generation check. When it is not ``ok``, ``build_failed`` and
    ``run`` are ``None`` and ``removed`` is ``None``: no directory was made.
    Otherwise ``build_failed`` is ``None`` or a
    :class:`hilclaw.model_execute.BuildFailed`; ``run`` is ``None`` when a
    build failed, else the
    :class:`hilclaw.model_forward_run.ForwardProgramResult` of the run as
    returned; ``removed`` is whether the build directory no longer exists
    afterwards.
    """

    check: model_binding.BindingCheck
    build_failed: BuildFailed | None
    run: model_forward_run.ForwardProgramResult | None
    removed: bool | None


def execute(
    dimensions,
    binding,
    *,
    eps,
    rope,
    weights,
    prompt,
    given,
    lm_head_rows,
    build_timeout_s,
    run_timeout_s,
    program_flags=(),
    program_trailing_flags=(),
    compiler=None,
    env=None,
    prefix=(),
    parent=None,
    keep_out=(),
):
    """Check, build and run one bf16 generation of the forward program; return a :class:`ForwardExecution`.

    ``dimensions``, ``binding``, ``eps``, ``rope``, ``weights``, ``prompt``,
    ``given`` and ``lm_head_rows`` are the arguments of
    :func:`hilclaw.model_forward_check.check`, which gets them with the dtype
    ``"bf16"`` and ``generation_length`` the length of ``given``. The
    binding's kernels are :class:`hilclaw.model_binding.KernelReference`
    values, each built with its own ``sources`` and ``flags``,
    ``build_timeout_s``, ``compiler`` and ``env``; the forward program is
    built with ``program_flags``, ``program_trailing_flags``,
    ``build_timeout_s``, ``compiler`` and ``env``, and run with
    ``run_timeout_s`` and ``env``. ``prefix`` is a sequence of paths put in
    front of the built program's path; empty, the program is started by its
    path. ``parent`` is the existing directory the build directory is made
    in (``None``: :func:`tempfile.gettempdir`); it must not be or lie inside
    the directory that holds this package or a directory of the sequence of
    paths ``keep_out``. No model parameter, setting or time limit has a
    default.

    Raised before anything is made: first what the check raises, unchanged;
    then, as :func:`hilclaw.model_execute.execute` raises them,
    :class:`TypeError` or :class:`ValueError` for ``prefix``, ``keep_out``
    and ``parent``; then :class:`TypeError` for ``program_flags`` that is not
    a ``tuple`` or ``list`` of ``str``. These are raised whatever the check's
    outcomes. The :class:`OSError` of making the directory (a missing
    ``parent``) is raised as it is. What a build, the input's encoding or
    writing or the run raises is passed on unchanged after the directory was
    removed.
    """
    generation_length = len(given) if _is_sequence(given) else 0
    check = model_forward_check.check(
        dimensions,
        binding,
        dtype="bf16",
        eps=eps,
        rope=rope,
        weights=weights,
        prompt=prompt,
        given=given,
        generation_length=generation_length,
        lm_head_rows=lm_head_rows,
    )
    prefix = _checked_prefix(prefix)
    roots = _checked_keep_out(keep_out)
    place = _checked_parent(parent, roots)
    if not isinstance(program_flags, (tuple, list)) or not all(
        isinstance(flag, str) for flag in program_flags
    ):
        raise TypeError("program_flags: must be a tuple or list of str")
    if not check.ok:
        return ForwardExecution(check, None, None, None)
    kernels = _distinct_kernels(check.calls)
    libraries = _library_table(
        dimensions,
        check.calls,
        kernels,
        prompt_length=len(prompt),
        generation_length=generation_length,
        lm_head_rows=lm_head_rows,
    )
    directory = tempfile.mkdtemp(prefix=PREFIX, dir=place)
    try:
        build_failed, run = _build_and_run(
            directory,
            kernels,
            prefix,
            build_timeout_s=build_timeout_s,
            compiler=compiler,
            env=env,
            program_flags=program_flags,
            program_trailing_flags=program_trailing_flags,
            input_arguments={
                "eps": eps,
                "rope": rope,
                "weights": weights,
                "prompt": prompt,
                "given": given,
                "lm_head_rows": lm_head_rows,
                "libraries": libraries,
                "library_count": len(kernels),
            },
            dimensions=dimensions,
            run_timeout_s=run_timeout_s,
        )
    except BaseException:
        _remove(directory, roots)
        raise
    return ForwardExecution(check, build_failed, run, _remove(directory, roots))


def _distinct_kernels(calls):
    kernels = []
    for _, _, kernel in calls:
        if kernel not in kernels:
            kernels.append(kernel)
    return tuple(kernels)


def _library_table(
    dimensions, calls, kernels, *, prompt_length, generation_length, lm_head_rows
):
    bound = {(site, shape): kernels.index(kernel) for site, shape, kernel in calls}
    table = {}
    for site in model_forward_run.CALL_SITES:
        indices = []
        for p in range(generation_length):
            rows = prompt_length if p == 0 else 1
            if site == "sdpa":
                positions = prompt_length + p
                shape = model_binding.sdpa_shape(dimensions, site, rows, positions)
            else:
                if site == "lm_head" and lm_head_rows == "last":
                    rows = 1
                shape = _SHAPES[site](dimensions, site, rows)
            indices.append(bound[(site, shape)])
        table[site] = indices
    return table


def _build_and_run(
    directory,
    kernels,
    prefix,
    *,
    build_timeout_s,
    compiler,
    env,
    program_flags,
    program_trailing_flags,
    input_arguments,
    dimensions,
    run_timeout_s,
):
    libraries = []
    for index, kernel in enumerate(kernels):
        library = os.path.join(directory, f"kernel-{index}.so")
        build = model_build.build_kernel_library(
            kernel.sources,
            library,
            timeout_s=build_timeout_s,
            flags=kernel.flags,
            compiler=compiler,
            env=env,
        )
        if not build.ok:
            return BuildFailed(index, build), None
        libraries.append(library)
    program = os.path.join(directory, _PROGRAM_NAME)
    build = model_build.build_forward_program(
        program,
        timeout_s=build_timeout_s,
        flags=program_flags,
        trailing_flags=program_trailing_flags,
        compiler=compiler,
        env=env,
    )
    if not build.ok:
        return BuildFailed(None, build), None
    input_file = os.path.join(directory, _INPUT_NAME)
    data = model_forward_run.encode_input(dimensions, **input_arguments)
    with open(input_file, "xb") as stream:
        stream.write(data)
    run = model_forward_run.run_forward_program(
        (*prefix, program) if prefix else program,
        input_file,
        libraries,
        dimensions=dimensions,
        prompt_length=len(input_arguments["prompt"]),
        generation_length=len(input_arguments["given"]),
        lm_head_rows=input_arguments["lm_head_rows"],
        timeout_s=run_timeout_s,
        env=env,
    )
    return None, run
