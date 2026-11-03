"""The read-only report of installers and images of ADR-0195 decision 10 (PLAN P3-14).

Command line: ``python -m hilclaw.storage_report [--file-dir <path> ...]
[--image <ref> ...]``. Each ``--file-dir`` names a directory of installers or
archives, each ``--image`` the reference of an image already on the machine;
both may be repeated and at least one of them is given. A value that begins
with ``-``, an empty value, a missing value, an unknown argument, an image
reference that :func:`hilclaw.standin_container.check_image` refuses and an
empty command line are a bad usage, and nothing is read. Nothing is read
beyond what is named: the machine's images are not listed.

**Files.** Each named directory is walked recursively. A regular file gets
its path relative to the named directory (joined by ``/``), its size and its
SHA-256, hashed in chunks as :mod:`hilclaw.cas` hashes. A symbolic link (a
Windows junction included) is not followed and is listed under ``skipped``
with ``symbolic link``; any other entry that is neither a directory nor a
regular file is listed there with ``not a regular file``. The named path
itself is opened as given. A named directory that cannot be listed is
``unreadable``; a file or a directory below it that cannot be read is listed
under its ``unreadable`` and the walk goes on. **File duplicates** are groups
of entries, across all named directories, that hold one SHA-256 and are at
least two distinct files (two names of one file, a hard link or one
directory named twice, are one file).

**Images.** For each named reference the client is asked once, under
:data:`INSPECT_TIME_LIMIT_S`, through :func:`hilclaw.local_run.run` with no
shell: ``<client> image inspect --format {{json .}} <ref>``. Its ``Id``,
``RepoTags`` and ``Size`` give the image id, the tags and the size.
References that resolve to one image id are one image, and its components are
read once, through the first of them, by
:func:`hilclaw.toolchain_check.image_entry` (the adapters' own probes; this
module holds no command of a tool). A reference the client cannot read, an
answer that cannot be read, or an image no container of can be used, is
``unreadable``. **Image duplicates** are two or more image ids holding one
component at one ``present`` version (DRIVER D29: one version of a tool is
held in one image).

**Retirement candidates.** A tag reads as a *tool tag* when its tag part (after
the last ``:`` that follows the last ``/``) is a *version*: one or more
decimal numbers joined by ``.``; the part before it is the tool's name. A
later version is the greater one compared number by number, a version that is
a prefix of another coming first. An image is a candidate when one of its tool
tags has a later version of the same tool on another named image that is
``read`` and holds ``present`` every component the first holds ``present``;
the newest such image is named as what replaces it. Never a candidate: an
image that is not ``read``, has an ``unreadable`` component or holds no
component ``present`` (it holds no tool the table reads, such as a base
image of an operating system); an image one of
whose tool tags holds the newest version of its tool among the named images;
an image named now by ``HILCLAW_STANDIN_IMAGE`` or ``HILCLAW_CODER_IMAGE``.
The two variables are read from the process environment (an unset, empty or
refused value names nothing); a value is matched against each image's named
references, tags and id, with ``:latest`` added when it holds no tag, and
against the image id the client gives for it.

**The report.** Standard output gets one ASCII JSON document and one LF,
with ``files`` (``directories`` and ``duplicates``) and ``images``
(``images``, ``duplicates`` and ``retirement_candidates``). It holds no
environment value, token or command line, and no ``schema_version``: it is
no data-plane file. It proposes; it never deletes.

**Exit statuses**, as in :mod:`hilclaw.toolchain_check` and ADR-0195
decision 2: :data:`EXIT_READ` (0) the report was written and everything
named was read (duplicates, candidates and skipped links are its content);
:data:`EXIT_UNREADABLE` (10) the report was written and a directory, file,
image or image component was ``unreadable``; :data:`EXIT_USAGE` (20) an
argument was refused and nothing was read; :data:`EXIT_FAULT` (21) the
command's own error, or a standard output it does not have or cannot write.
Standard error gets one fixed line only when no report was written.

**Read only.** It removes, installs, pulls and changes nothing and writes
nothing but its report, except the empty temporary directory each container
call of :mod:`hilclaw.toolchain_check` makes and removes.
"""

import contextlib
import hashlib
import json
import os
import re
import stat
import sys

from hilclaw import (
    cas,
    coder_runtime,
    local_run,
    standin_container,
    standin_image,
    toolchain_check,
    vendor_adapter,
)

INSPECT_TIME_LIMIT_S = 30
CLIENT = toolchain_check.CLIENT

EXIT_READ = 0
EXIT_UNREADABLE = 10
EXIT_USAGE = 20
EXIT_FAULT = 21

READ = "read"
UNREADABLE = vendor_adapter.UNREADABLE

USAGE = "usage: python -m hilclaw.storage_report [--file-dir <path> ...] [--image <ref> ...]"

_LINK = "symbolic link"
_NOT_REGULAR = "not a regular file"
_NOT_LISTED = "the directory could not be listed"
_NOT_READ = "the file could not be read"
_CLIENT_FAILED = "the client could not read the image"
_ANSWER_BAD = "the client's answer could not be read"
_PROBE_FAILED = "the components of the image could not be read"
_VERSION = re.compile(r"[0-9]+(?:\.[0-9]+)*")


def _sha256_and_identity(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        status = os.fstat(f.fileno())
        if not stat.S_ISREG(status.st_mode):
            raise OSError("not a regular file")
        for chunk in iter(lambda: f.read(cas.CHUNK_SIZE), b""):
            sha.update(chunk)
    return sha.hexdigest(), status.st_size, (status.st_dev, status.st_ino)


def _is_link(entry):
    return entry.is_symlink() or getattr(entry, "is_junction", lambda: False)()


def _walk(top, relative, result, identities):
    try:
        with os.scandir(top) as listing:
            entries = sorted(listing, key=lambda entry: entry.name)
    except OSError:
        if not relative:
            raise
        result["unreadable"].append({"path": relative, "message": _NOT_LISTED})
        return
    for entry in entries:
        path = f"{relative}/{entry.name}" if relative else entry.name
        try:
            if _is_link(entry):
                result["skipped"].append({"path": path, "reason": _LINK})
            elif entry.is_dir(follow_symlinks=False):
                _walk(entry.path, path, result, identities)
            elif entry.is_file(follow_symlinks=False):
                digest, size, identity = _sha256_and_identity(entry.path)
                result["files"].append({"path": path, "size": size, "sha256": digest})
                identities[path] = identity
            else:
                result["skipped"].append({"path": path, "reason": _NOT_REGULAR})
        except OSError:
            result["unreadable"].append({"path": path, "message": _NOT_READ})


def read_directory(directory):
    """Walk one named directory and return its entry of the report's ``directories``.

    ``directory`` is a ``str`` path. The entry has ``directory`` (as given),
    ``state`` (``read`` or ``unreadable``), ``message`` (``None`` when
    ``read``), ``files``, ``skipped`` and ``unreadable`` (lists, in path
    order). No :class:`OSError` leaves the call; a :class:`TypeError` is
    raised for a ``directory`` that is not ``str``.
    """
    if not isinstance(directory, str):
        raise TypeError(f"directory must be str, not {type(directory).__name__}")
    entry, _ = _read_directory(directory)
    return entry


def _read_directory(directory):
    entry = {"directory": directory, "state": READ, "message": None}
    result = {"files": [], "skipped": [], "unreadable": []}
    identities = {}
    try:
        _walk(directory, "", result, identities)
    except OSError:
        entry.update(state=UNREADABLE, message=_NOT_LISTED)
    entry.update(result)
    return entry, identities


def file_duplicates(directories, identities=None):
    """Return the duplicate groups of the ``directories`` entries of :func:`read_directory`.

    A group is ``{"sha256", "size", "files": [{"directory", "path"}, ...]}``
    for one SHA-256 held by at least two distinct files, in the order of
    ``directories`` and paths; the groups are ordered by SHA-256.
    ``identities``, when given, maps ``(directory, path)`` to a file's
    ``(st_dev, st_ino)``, so that two names of one file count once; without
    it every entry counts as a file of its own.
    """
    groups = {}
    for directory in directories:
        for found in directory["files"]:
            groups.setdefault(found["sha256"], []).append(
                (directory["directory"], found)
            )
    duplicates = []
    for digest in sorted(groups):
        members = groups[digest]
        if identities is None:
            distinct = len(members)
        else:
            distinct = len(
                {identities.get((d, f["path"]), (d, f["path"])) for d, f in members}
            )
        if distinct < 2:
            continue
        duplicates.append(
            {
                "sha256": digest,
                "size": members[0][1]["size"],
                "files": [{"directory": d, "path": f["path"]} for d, f in members],
            }
        )
    return duplicates


def _valid_inspect(document):
    if not isinstance(document, dict):
        return None
    image_id, tags, size = (
        document.get("Id"),
        document.get("RepoTags"),
        document.get("Size"),
    )
    tags = [] if tags is None else tags
    try:
        standin_container.check_image(image_id)
    except (TypeError, ValueError):
        return None
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        return None
    if type(size) is not int or size < 0:
        return None
    return {"id": image_id, "size": size, "tags": list(tags)}


def inspect_image(reference, *, client=CLIENT):
    """Ask the client for one image's id, size and tags and return them, or a refusal text.

    Returns ``({"id", "size", "tags"}, None)`` when the client answered with
    status 0 and one JSON object holding a valid ``Id``, a ``RepoTags`` list
    of ``str`` (or ``null``) and an ``int`` ``Size``; otherwise ``(None,
    message)`` with a fixed text. ``reference`` is checked by
    :func:`hilclaw.standin_container.check_image` first and its
    :class:`TypeError` or :class:`ValueError` is passed on. No other
    exception leaves the call.
    """
    standin_container.check_image(reference)
    command = [client, "image", "inspect", "--format", "{{json .}}", reference]
    try:
        ran = local_run.run(command, timeout_s=INSPECT_TIME_LIMIT_S, env=None)
    except Exception:  # noqa: BLE001
        return None, _CLIENT_FAILED
    if ran.timed_out or ran.returncode != 0:
        return None, _CLIENT_FAILED
    try:
        document = json.loads(ran.stdout.decode("utf-8"))
    except ValueError:
        return None, _ANSWER_BAD
    found = _valid_inspect(document)
    if found is None:
        return None, _ANSWER_BAD
    return found, None


def read_tool_tag(tag):
    """Return ``(tool, version)`` for a tag of the form ``<tool>:<version>``, else ``None``.

    The version is one or more decimal numbers joined by ``.``, returned as a
    ``tuple`` of ``int``; the tool is everything before the last ``:`` that
    follows the last ``/``. A tag that is not ``str`` gives ``None``.
    """
    if not isinstance(tag, str):
        return None
    tool, colon, version = tag.rpartition(":")
    if not colon or not tool or "/" in version or not _VERSION.fullmatch(version):
        return None
    return tool, tuple(int(number) for number in version.split("."))


def _present(image):
    return {
        name: entry["version"]
        for name, entry in image["components"].items()
        if entry["state"] == vendor_adapter.PRESENT
    }


def image_duplicates(images):
    """Return groups of image ids holding one component at one ``present`` version.

    ``images`` is the report's list of image entries. A group is
    ``{"component", "version", "images": [<id>, ...]}``, ordered by component
    and version; an image id appears once in a group however many tags it
    has.
    """
    holders = {}
    for image in images:
        if image["id"] is None:
            continue
        for name, version in _present(image).items():
            ids = holders.setdefault((name, version), [])
            if image["id"] not in ids:
                ids.append(image["id"])
    return [
        {"component": name, "version": version, "images": ids}
        for (name, version), ids in sorted(holders.items())
        if len(ids) > 1
    ]


def _usable(image):
    return image["state"] == READ and all(
        entry["state"] != UNREADABLE for entry in image["components"].values()
    )


def retirement_candidates(images, named_now=frozenset()):
    """Return the retirement candidates among the report's image entries.

    ``named_now`` is a set of image ids that a runtime variable names now;
    those images are never candidates. A candidate is
    ``{"id", "tag", "size", "replaced_by": {"id", "tag"}}``, in the order of
    ``images``; the rule is the module's.
    """
    readings = []
    newest = {}
    for image in images:
        for tag in image["tags"]:
            reading = read_tool_tag(tag)
            if reading is None:
                continue
            readings.append((image, tag) + reading)
            tool, version = reading
            newest[tool] = max(newest.get(tool, version), version)
    holding_newest = {
        image["id"] for image, _, tool, version in readings if version == newest[tool]
    }
    candidates = []
    for image in images:
        if image["id"] in holding_newest or image["id"] in named_now:
            continue
        if image["id"] is None or not _usable(image):
            continue
        held = set(_present(image))
        if not held:
            continue
        for own, tag, tool, version in readings:
            if own is not image:
                continue
            later = [
                (other_version, other_tag, other)
                for other, other_tag, other_tool, other_version in readings
                if other_tool == tool
                and other_version > version
                and other["id"] != image["id"]
                and _usable(other)
                and held <= set(_present(other))
            ]
            if later:
                _, by_tag, by = max(later, key=lambda item: item[0])
                candidates.append(
                    {
                        "id": image["id"],
                        "tag": tag,
                        "size": image["size"],
                        "replaced_by": {"id": by["id"], "tag": by_tag},
                    }
                )
                break
    return candidates


def _named_by_runtime(environ):
    named = []
    with contextlib.suppress(TypeError, ValueError):
        value = standin_image.read_image(environ)
        if value is not None:
            named.append(value)
    value = environ.get(coder_runtime.ENV_IMAGE)
    with contextlib.suppress(TypeError, ValueError):
        standin_container.check_image(value)
        named.append(value)
    return named


def _matches(value, image):
    forms = {value}
    if "@" not in value and ":" not in value.rpartition("/")[2]:
        forms.add(value + ":latest")
    known = set(image["references"]) | set(image["tags"]) | {image["id"]}
    return bool(forms & known)


def _read_images(references, components, client):
    by_id = {}
    images = []
    inspected = {}
    for reference in references:
        found, message = inspect_image(reference, client=client)
        inspected[reference] = found
        if found is None:
            images.append(
                {
                    "references": [reference],
                    "id": None,
                    "size": None,
                    "tags": [],
                    "state": UNREADABLE,
                    "message": message,
                    "components": {},
                }
            )
            continue
        if found["id"] in by_id:
            by_id[found["id"]]["references"].append(reference)
            continue
        image = {"references": [reference], **found}
        try:
            entry = toolchain_check.image_entry(
                reference, components=components, client=client
            )
        except Exception:  # noqa: BLE001
            entry = {"state": UNREADABLE, "message": _PROBE_FAILED, "components": {}}
        image.update(entry)
        by_id[found["id"]] = image
        images.append(image)
    return images, inspected


def report(directories=(), images=(), *, environ=None, components=None, client=CLIENT):
    """Read the named directories and images and return the report as a ``dict``.

    ``directories`` and ``images`` are sequences of ``str`` (one ``str`` is
    refused with :class:`TypeError`); a name given twice is read once. Each
    image reference is checked by
    :func:`hilclaw.standin_container.check_image` before anything is read.
    ``environ`` (a mapping, default ``os.environ``) is where the runtime
    variables are read; ``components`` and ``client`` are as in
    :func:`hilclaw.toolchain_check.check`.
    """
    for name, given in (("directories", directories), ("images", images)):
        if isinstance(given, (str, bytes)):
            raise TypeError(
                f"{name} must be a sequence of str, not one {type(given).__name__}"
            )
    directories = list(dict.fromkeys(directories))
    images = list(dict.fromkeys(images))
    for directory in directories:
        if not isinstance(directory, str):
            raise TypeError(f"directory must be str, not {type(directory).__name__}")
    for reference in images:
        standin_container.check_image(reference)
    environ = os.environ if environ is None else environ
    read, identities = [], {}
    for directory in directories:
        entry, found = _read_directory(directory)
        read.append(entry)
        identities.update({(directory, path): ident for path, ident in found.items()})
    entries, inspected = _read_images(images, components, client)
    named_now = set()
    for value in _named_by_runtime(environ):
        found = inspected.get(value)
        if found is None and value not in inspected:
            found, _ = inspect_image(value, client=client)
        if found is not None:
            named_now.add(found["id"])
        named_now.update(e["id"] for e in entries if e["id"] and _matches(value, e))
    return {
        "files": {
            "directories": read,
            "duplicates": file_duplicates(read, identities),
        },
        "images": {
            "images": entries,
            "duplicates": image_duplicates(entries),
            "retirement_candidates": retirement_candidates(entries, named_now),
        },
    }


def exit_status(document):
    """Return :data:`EXIT_UNREADABLE` when anything of ``document`` is ``unreadable``, else :data:`EXIT_READ`."""
    for directory in document["files"]["directories"]:
        if directory["state"] == UNREADABLE or directory["unreadable"]:
            return EXIT_UNREADABLE
    for image in document["images"]["images"]:
        if not _usable(image):
            return EXIT_UNREADABLE
    return EXIT_READ


def _arguments(args):
    directories, images = [], []
    position = 0
    while position < len(args):
        name = args[position]
        if name not in ("--file-dir", "--image") or position + 1 >= len(args):
            raise ValueError("usage")
        value = args[position + 1]
        if not value or value.startswith("-"):
            raise ValueError("usage")
        if name == "--image":
            standin_container.check_image(value)
            images.append(value)
        else:
            directories.append(value)
        position += 2
    if not directories and not images:
        raise ValueError("usage")
    return directories, images


def _standard(name):
    return getattr(getattr(sys, name), "buffer", None)


def _say(stderr, text):
    with contextlib.suppress(OSError, ValueError):
        if stderr is not None:
            line = f"hilclaw.storage_report: {text}\n"
            stderr.write(line.encode("ascii", "backslashreplace"))
            stderr.flush()


def main(
    argv=None, *, stdout=None, stderr=None, environ=None, components=None, client=CLIENT
):
    """Run the command line, write the report and return the exit status.

    ``argv`` defaults to ``sys.argv[1:]``; ``stdout`` and ``stderr`` are
    binary streams and default to the standard ones; ``environ``,
    ``components`` and ``client`` are as in :func:`report`. Returns one of
    the four exit statuses; no :class:`Exception` leaves the call.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    try:
        directories, images = _arguments(args)
    except (TypeError, ValueError):
        _say(stderr, USAGE)
        return EXIT_USAGE
    try:
        if stdout is None:
            raise OSError("standard output is closed")
        document = report(
            directories, images, environ=environ, components=components, client=client
        )
        status = exit_status(document)
        text = (json.dumps(document, ensure_ascii=True) + "\n").encode("ascii")
        if stdout.write(text) != len(text):
            raise OSError("standard output took a part of the report")
        stdout.flush()
    except Exception as fault:  # noqa: BLE001
        _say(stderr, f"fault: {type(fault).__name__}")
        return EXIT_FAULT
    return status


if __name__ == "__main__":
    raise SystemExit(main())
