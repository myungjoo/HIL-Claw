"""The once-only write: the steps by which a whole content is given a final name that is free.

Three records fix the same steps for three kinds of file:
``ARCHITECTURE/decisions/ADR-0014-od8-whole-file-writes.md`` decision 3 for the
key record files, ``ARCHITECTURE/decisions/ADR-0025-od8-instance-file-write.md``
decisions 3 and 6 for ``instance.json`` and
``ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md`` for ``spec.json``. This
module is those steps, once, for :mod:`hilclaw.key_records`,
:mod:`hilclaw.instance_file` and :mod:`hilclaw.spec_file`:

- a new temporary file ``<final name>.<token>.tmp`` beside the final name,
  created exclusively, where ``<token>`` is the process id, a hyphen and 16
  random hexadecimal characters;
- the whole content written into it, flushed and brought to stable storage;
- a hard link from the temporary name to the final name, a step that fails
  when the final name exists and replaces nothing;
- the removal of the temporary name.

There is no fallback to a replacing rename: where the link is not possible the
write fails and has put nothing under the final name. The temporary file is
removed after any exception raised before the final name is given, an
interrupt included, and only when this call created it: a file of the name
form that another write left is never read, removed or given the final name.
A removal that fails is not reported, neither in the place of the failure it
follows nor after the final name is given, where the temporary name then stays
as a second name of the file.

Limits, as the three records state them: the steps hold on the POSIX systems
of C-7 whose file system gives the hard link; nothing is stated for a network
file system, for a Windows drive seen from WSL or for native Windows. The
directory entry is not flushed.

What this module does not do: it creates no directory, reads and lists
nothing, never opens the final name, validates no content, takes no lock and
retries nothing. What a taken final name means, which directories are created
and what happens to them when the write fails stay with each caller. It is no
tool.
"""

import contextlib
import os
import secrets


def write_once(path, content):
    """Give the final name ``path`` to a new file of ``content`` if that name is free.

    ``path`` is a :class:`pathlib.Path` whose directory exists; ``content`` is
    the whole file as ``bytes``.

    Returns ``None`` when the final name was given to the file. Returns the
    :class:`FileExistsError` of the link, not raised, when the link found the
    final name taken: the entry under the name is left as it was found and
    the temporary file is removed where that is possible.

    Raises the :class:`OSError` of any other step that failed (the creation of
    the temporary file, the write, the flush, the link), a
    :class:`FileExistsError` for a temporary name in use among them, and
    :class:`TypeError` for a ``content`` that is not bytes. Nothing is under
    the final name by this call then, and its temporary file is removed where
    that is possible.
    """
    token = f"{os.getpid()}-{secrets.token_hex(8)}"
    temporary = path.with_name(f"{path.name}.{token}.tmp")
    created = False
    taken = None
    try:
        with open(temporary, "xb") as f:
            created = True
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            taken = error
    except BaseException:
        if created:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
        raise
    with contextlib.suppress(OSError):
        os.unlink(temporary)
    return taken
