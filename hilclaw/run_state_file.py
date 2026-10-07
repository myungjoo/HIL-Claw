"""The write of ``runs/<run_id>/STATE.json``: one replacement by the steps of ADR-0013.

``ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md`` fixes how the
runtime state file of a run comes to be on disk (decision 2): the whole content
first, a new temporary file beside the final one, its content brought to stable
storage, one move over the final name, and the temporary file removed when a
step fails. This module is those steps over :func:`hilclaw.run_state.dump`
(the content) and :func:`hilclaw.layout.run_file` (the path). The temporary
file is ``STATE.json.<token>.tmp`` in the run directory (decision 3).

Conventions of this module, which the records do not fix:

- The checks come in this order: ``run_id``, then the values (the content is
  built), then ``data_root``, then the file system. Nothing is created before
  the last of them.
- ``data_root`` is a ``str`` or a path, is not resolved and must be an existing
  directory (:class:`FileNotFoundError` or :class:`NotADirectoryError`
  otherwise); it is never created. ``runs/`` and the run directory are created
  when missing and stay when a later step fails.
- ``<token>`` is the process id, a hyphen and 16 random hexadecimal characters.
- A step that fails raises its :class:`OSError` unchanged, as the other writers
  of the package do. A directory under the final name is found by the move,
  which fails; a symbolic link there is replaced, not followed.
- The temporary file is removed after any exception, an interrupt included. A
  removal that fails is not reported in the place of the failure it follows.
- Only the file this call created is removed: a file of the name form that
  another replacement left is not listed, read, moved or removed (decision 4).
- The new file has the mode a newly created file gets from the process.

Limits (decision 5): the death of the writing process leaves the previous
content or the new one, and nothing is promised for the loss of the machine;
the directory entry is not flushed. This holds where a rename inside one
directory replaces a file in one step, the POSIX systems of C-7: nothing is
stated for a network file system or for native Windows. Two writers at once
are not prevented: each moves a whole content and the later move wins.

It reads no file, the previous ``STATE.json`` included, and carries no member
over (decision 7). It takes no lock, makes no commit, restores nothing from the
history, writes no other file and is not a tool: who calls it is open (OD-23,
the rest of OD-17, sub-questions 10, 12 and 15 of OD-8).
"""

import contextlib
import os
import secrets
from pathlib import Path

from hilclaw import layout, run_state


def replace(data_root, run_id, round, view, others=None):
    """Put the content of these values under ``runs/<run_id>/STATE.json``; return ``None``.

    The content is ``hilclaw.run_state.dump(round, view, others)``, exactly
    what is given. It replaces the file as a whole, or is the first file of the
    run. Until the move the final name holds what it held, and it is never
    opened for writing.

    Raises :class:`hilclaw.layout.InvalidPathValueError` for an invalid
    ``run_id`` and :class:`hilclaw.run_state.InvalidStateError` for values
    :func:`hilclaw.run_state.dump` refuses, both before the file system is
    touched; :class:`FileNotFoundError` or :class:`NotADirectoryError` for a
    ``data_root`` that is no existing directory; and the :class:`OSError` of
    the step that failed (the creation of a directory or of the temporary file,
    the write, the flush, the move). The final name is then as it was and the
    temporary file of this call is removed.
    """
    layout.check_run_id(run_id)
    content = run_state.dump(round, view, others)
    path = layout.run_file(data_root, run_id, "STATE.json")
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    path.parent.mkdir(parents=True, exist_ok=True)
    token = f"{os.getpid()}-{secrets.token_hex(8)}"
    temporary = path.with_name(f"{path.name}.{token}.tmp")
    created = False
    try:
        with open(temporary, "xb") as f:
            created = True
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    except BaseException:
        if created:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
        raise
