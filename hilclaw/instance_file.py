"""The write of ``runs/<run_id>/instance.json``: one write by the steps of ADR-0025.

``ARCHITECTURE/decisions/ADR-0025-od8-instance-file-write.md`` fixes by which
steps the bytes of the instance record of a run come to be under their final
name (decision 3): the whole content first, valid and in the written form; a
new temporary file beside the final name; its content brought to stable
storage; one last step that gives the final name only if that name does not
exist and otherwise changes nothing; and the temporary file removed when a
step fails before the name is given. This module is those steps over
:func:`hilclaw.instance.parse` (the validity of the content) and
:func:`hilclaw.layout.run_file` (the path). The temporary file is
``instance.json.<token>.tmp`` in the run directory (decision 6). The last step
is a hard link from the temporary name to the final name, followed by the
removal of the temporary name. There is no fallback to a replacing rename:
where the link is not possible the write fails and has put nothing under the
final name.

Conventions of this module, which the record does not fix:

- The content is given as ``bytes`` and is written as given: this module
  builds no bytes from a document.
- The checks come in this order: ``run_id``, then the validity of the content,
  then its written form, then ``data_root``, then the file system. Nothing is
  created before the last of them.
- What :func:`hilclaw.instance.parse` raises for a content passes through
  unchanged. A valid content that is not in the written form of ADR-0018
  decision 2 raises :class:`WrittenFormError`. The written form is checked as:
  the content ends with a line feed and holds no carriage return byte. No
  member order, indentation or number of lines is checked.
- ``data_root`` is a ``str`` or a path, is not resolved and must be an existing
  directory (:class:`FileNotFoundError` or :class:`NotADirectoryError`
  otherwise); it is never created. ``runs/`` and the run directory are created
  when missing and stay when a later step fails.
- ``<token>`` is the process id, a hyphen and 16 random hexadecimal characters.
- A final name that the last step finds taken raises :class:`NameTakenError`,
  which is no :class:`OSError`. Every other step that fails raises its
  :class:`OSError` unchanged, as the other writers of the package do; a
  temporary name in use and a file in the place of a directory are among
  them, and may be a :class:`FileExistsError`.
- The temporary file is removed after any exception raised before the final
  name is given, an interrupt included. A removal that fails is not reported
  in the place of the failure it follows. Once the final name is given, a
  removal that fails is not reported at all: the write has happened and the
  temporary name stays as a second name of the file (decision 3 step 5). An
  interrupt that arrives after the link leaves the file under the final name.
- Only the file this call created is removed: a file of the name form that
  another write left is not listed, read, removed or given the final name
  (decision 6).
- The new file has the mode a newly created file gets from the process.
- The directories above the final name are used as the operating system
  resolves them, as :func:`hilclaw.instance.read` reads through them.

Limits (decision 7): when the final name was not taken before the write, the
death of the writing process leaves no file under it or the whole one; a name
that was taken holds what it held. Nothing is promised for the loss of the
machine, and the directory entry is not flushed. This holds on the POSIX systems
of C-7 whose file system gives the hard link: nothing is stated for a network
file system, for a Windows drive seen from WSL or for native Windows. Two
writers at once are not prevented: one is given the name, the other finds it
taken, and the file is never a mixture of the two. The name is given once
only against another write by these steps: nothing here prevents a process
from writing, replacing or removing the file by other means.

It composes no content and fills in no value: no member is put in or taken
out, and a valid content without ``tolerance``, ``source_commit``, ``n_max``,
``candidates_per_round`` or ``op_signature`` is written as it is (decision 2;
the last two of the five members are ADR-0028's and ADR-0031's). It does not
say that a content is right,
complete or enough to start a run. It reads no file, the one under the final
name included, lists no directory, compares nothing and knows no "same
content" (decision 4). It
is no lock and not the means by which a ``run_id`` is unique. It takes no
lock, makes no commit, writes no other file and is not a tool: what writes the
file, when, in which order against ``STATE.json`` and what a caller does with
a taken name are open (OD-23, sub-questions 10, 17 and 23 of OD-8).
"""

import contextlib
import os
import secrets
from pathlib import Path

from hilclaw import instance, layout


class WrittenFormError(ValueError):
    """A valid content is not in the written form of ADR-0018 decision 2; the message names the rule."""


class NameTakenError(Exception):
    """The last step found the final name taken; the content was not written.

    It is no :class:`OSError`, so a caller that catches :class:`OSError` for a
    failure of the file system does not catch it. It says nothing of what is
    under the name: that entry was not opened, read or compared.
    """


def write(data_root, run_id, content):
    """Put ``content`` under ``runs/<run_id>/instance.json`` if that name is free; return ``None``.

    ``content`` is the whole file as ``bytes``. A call that returns has given
    the final name to a file of exactly these bytes: nothing is added,
    removed, defaulted or normalised. The final name is never opened, and
    this call puts nothing under it before the last step.

    Raises, before the file system is touched and in this order:
    :class:`hilclaw.layout.InvalidPathValueError` for an invalid ``run_id``;
    :class:`TypeError`, :class:`hilclaw.instance.InvalidInstanceError` or
    :class:`hilclaw.instance.UnsupportedVersionError` for a content
    :func:`hilclaw.instance.parse` refuses; :class:`WrittenFormError` for a
    valid content that does not end with a line feed or holds a carriage
    return byte. Nothing is created then.

    Raises :class:`FileNotFoundError` or :class:`NotADirectoryError` for a
    ``data_root`` that is no existing directory, and the :class:`OSError` of
    the step that failed (the creation of a directory or of the temporary
    file, the write, the flush, the link). This call has then put nothing
    under the final name, and its temporary file is removed where that is
    possible.

    Raises :class:`NameTakenError` when the link finds the final name taken,
    whatever is there and whatever its content: equal bytes are reported as
    any other. This call leaves the entry under the name as it found it and
    removes its temporary file where that is possible. Nothing is retried.
    """
    layout.check_run_id(run_id)
    instance.parse(content)
    if not content.endswith(b"\n"):
        raise WrittenFormError("content: does not end with a line feed")
    if b"\r" in content:
        raise WrittenFormError("content: holds a carriage return byte")
    path = layout.run_file(data_root, run_id, "instance.json")
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
        try:
            os.link(temporary, path)
        except FileExistsError:
            file = path.relative_to(root).as_posix()
            reason = f"{file}: the name is taken; the content was not written"
            raise NameTakenError(reason) from None
    except BaseException:
        if created:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
        raise
    with contextlib.suppress(OSError):
        os.unlink(temporary)
