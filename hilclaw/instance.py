"""The instance record of one run, ``runs/<run_id>/instance.json`` (ADR-0018, ADR-0020, ADR-0022, ADR-0023, ADR-0024, ADR-0028, ADR-0031, ADR-0032, ADR-0033, ADR-0034, ADR-0046, ADR-0053, ADR-0136).

``ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md`` fixes the
file as a whole (decision 2), the member ``hw_profile`` in which a run states
the hw_profile it was started with (decisions 3 and 5) and how a call of a HW
tool reads it (decision 4).
``ARCHITECTURE/decisions/ADR-0020-od8-instance-record-tolerance.md`` adds the
member ``tolerance``, in which a run states the ``rtol`` and the ``atol`` of
its correctness check in the vocabulary of the first case (decisions 2 to 4),
and says where the tolerance of a run is read from (decision 5).
``ARCHITECTURE/decisions/ADR-0022-od8-instance-record-source-commit.md`` adds
the member ``source_commit``, in which a run states the commit of the source
repository it was started with (decision 3), says that a valid file may lack
it and that a present one must be valid (decision 5), and says where the
source commit a run states is read from (decision 7).
``ARCHITECTURE/decisions/ADR-0023-od8-instance-record-n-max.md`` adds the
member ``n_max``, in which a run states the upper bound of repeats of one
timing measurement (decisions 2 and 3), says that a valid file may lack it,
that a present one must be valid and that no value stands in for an absent
one (decision 4), and says where the bound a run states is read from
(decision 5).
``ARCHITECTURE/decisions/ADR-0024-od8-instance-record-layout-version.md`` adds
no member and no rule of validity: the file states the layout version of its
run through its ``schema_version`` (decision 3), so a file this module
accepts states layout version 1, and the record says when a reader has the
layout version of a run and from where it is read (decisions 4 and 5).
``ARCHITECTURE/decisions/ADR-0028-od8-instance-record-candidates-per-round.md``
adds the member ``candidates_per_round``, in which a run states its number of
candidates per round (decisions 2 and 3), says that a valid file may lack it,
that a present one must be valid and that no value stands in for an absent
one (decision 4), and says where the number a run states is read from
(decision 5).
``ARCHITECTURE/decisions/ADR-0031-od8-instance-record-op-signature.md`` adds
the member ``op_signature``, in which a run states an op_signature record and
the key derived from it (decisions 2 and 3), says that a valid file may lack
it, that a present one must be valid and that nothing stands in for an absent
one (decision 5), and says where the op_signature a run states is read from
(decision 6).
``ARCHITECTURE/decisions/ADR-0032-od8-instance-record-round-budget.md`` adds
the member ``round_budget``, in which a run states the budget of loop
iterations the instance was started with, as a number of rounds (decisions 2
and 3), says that a valid file may lack it, that a present one must be valid
and that no value stands in for an absent one (decision 4), and says where
the round budget a run states is read from (decision 5).
``ARCHITECTURE/decisions/ADR-0033-od8-instance-record-wall-clock-budget.md``
adds the member ``wall_clock_budget_s``, in which a run states the budget of
wall-clock time the instance was started with, as a number of seconds
(decisions 2 and 3), says that a valid file may lack it, that a present one
must be valid and that no value stands in for an absent one (decision 4), and
says where the wall-clock budget a run states is read from (decision 5).
``ARCHITECTURE/decisions/ADR-0034-od8-instance-record-owner-project.md`` adds
the members ``owner`` and ``project``, in which a run states the owner and the
project the instance was started with, each as a name (decisions 2 and 3),
says that a valid file may lack either, that a present one must be valid and
that nothing stands in for an absent one (decision 4), and says where the
owner and the project a run states are read from (decision 5).
``ARCHITECTURE/decisions/ADR-0046-od18-correctness-check-draws.md`` adds the
member ``draws``, in which a run states the number of draws of a check of
``correctness.check`` about one of its attempts, says that a valid file may
lack it, that a present one must be valid and that no value stands in for an
absent one (decision 3), and says from which read of the file a call of that
tool takes the number (decision 4); no such call is made here.
``ARCHITECTURE/decisions/ADR-0053-od8-instance-record-objective.md`` adds the
member ``objective``, in which a run states its objectives and its
constraints in the form of the ``task.objective`` of a version-2 spec
(decision 4), says that a valid file may lack it, that a present one must be
valid and that nothing stands in for an absent one (decision 5), and says how
the member is read (decision 7).
``ARCHITECTURE/decisions/ADR-0136-od8-first-case-coder-model.md`` adds the
member ``coder_model``, in which a run states the full name of the Claude
model its coder calls request (decisions 2 and 3), and says that a valid file
may lack it, that a present one must be valid and that nothing stands in for
an absent one (decision 4). This
module is those rules: :func:`parse` and :func:`validate` are pure functions of
the bytes of a content and of a parsed document, and :func:`read`,
:func:`hw_profile_of`, :func:`tolerance_of`, :func:`source_commit_of`,
:func:`n_max_of`, :func:`candidates_per_round_of`, :func:`op_signature_of`,
:func:`round_budget_of`, :func:`wall_clock_budget_s_of`, :func:`owner_of`,
:func:`project_of`, :func:`draws_of`, :func:`objective_of`,
:func:`coder_model_of` and :func:`layout_version_of` read the file of a run.
:func:`hw_profile_of` has the call form of the parameter ``hw_profile_of`` of
:func:`hilclaw.hw_tool.tool_function`; nothing here binds it,
:func:`tolerance_of`, :func:`source_commit_of`, :func:`n_max_of`,
:func:`candidates_per_round_of`, :func:`op_signature_of`,
:func:`round_budget_of`, :func:`wall_clock_budget_s_of`, :func:`owner_of`,
:func:`project_of`, :func:`draws_of`, :func:`objective_of`,
:func:`coder_model_of` or :func:`layout_version_of` to a tool.

Conventions of this module, which the thirteen records do not fix:

- A content is exactly ``bytes`` (:class:`TypeError` otherwise: the encoding is
  part of validity). Values are as :func:`json.loads` returns them, an integer
  exactly an ``int``: ``true`` and ``1.0`` are none.
- Every other broken rule of a content or of a document raises
  :class:`InvalidInstanceError` naming the place, and another version raises
  :class:`UnsupportedVersionError` of this module.
- The rules for the whole text come first, whatever the version, then
  ``schema_version``, then ``hw_profile``, then ``tolerance`` when the document
  holds it, then ``source_commit`` when the document holds it, then ``n_max``
  when the document holds it, then ``candidates_per_round`` when the document
  holds it, then ``op_signature`` when the document holds it, then
  ``round_budget`` when the document holds it, then ``wall_clock_budget_s``
  when the document holds it, then ``owner`` when the document holds it, then
  ``project`` when the document holds it, then ``draws`` when the document
  holds it, then ``objective`` when the document holds it, then
  ``coder_model`` when the document holds it: the order in which the records
  defined them, and for the two of ADR-0034 the order in which it
  names them. A content this interpreter cannot read (an integer too long for
  it anywhere in the text, nesting too deep) raises :class:`InvalidInstanceError` too,
  though it is a limit of this reader and not damage; the limits stay as the
  interpreter has them. A number beyond the float range in a member not
  defined here is read as an infinity and is no error, as
  :mod:`hilclaw.run_state` has it; in ``tolerance``, as ``n_max``, as
  ``candidates_per_round``, as ``round_budget``, as
  ``wall_clock_budget_s`` and as ``draws`` it makes the content invalid
  (ADR-0020 decision 4, ADR-0023 decision 3, ADR-0028 decision 3, ADR-0032
  decision 3, ADR-0033 decision 3, ADR-0046 decision 3).
- ``schema_version`` is an integer of ADR-0001, from 0 to
  :data:`hilclaw.keys.MAX_INTEGER`: a value outside that range is no integer of
  the records and makes the content invalid, it is not another version. ``-0``
  is read as the integer 0, as :mod:`hilclaw.run_state` reads it, and is then
  the unsupported version 0.
- Inside ``hw_profile`` the order is: an object, no member besides ``key`` and
  ``record``, both present, ``key`` a ``str``, ``record`` an object, the record
  valid, ``key`` the derived name. The first rule found broken is reported. An
  empty ``key`` and one of another form are reported as not the derived name.
- What is a value of ``op_signature`` is ADR-0031 decision 3 and not a
  convention: an object with exactly ``key`` and ``record``, the record one
  that :func:`hilclaw.keys.op_signature_key` accepts and ``key`` the name that
  function derives from it. The conventions are the order inside the member,
  which is that of ``hw_profile`` with the other place name, the first rule
  found broken being reported and an empty ``key`` and one of another form as
  not the derived name; that for a value built in memory the member and
  ``record`` must each be exactly a ``dict`` and ``key`` exactly a ``str``;
  and that a message of :mod:`hilclaw.keys` about the record is given as it
  is, after ``op_signature.record.``. The member is handed out as an
  :class:`OpSignature`: the ``str`` and the ``dict`` of the file, unchanged.
  That a content without the member states no op_signature, and that this is
  no error of the content, is ADR-0031 decision 5 and not a convention; the
  convention is that it has ``None`` in that place.
- Inside ``tolerance`` the order is: an object, no member besides ``rtol`` and
  ``atol``, both present, ``rtol`` a valid value, ``atol`` a valid value. A
  value is exactly an ``int`` or a ``float`` (``true`` is none) whose ``float``
  is finite and not negative, so an ``int`` that no ``float`` holds is invalid.
  The first rule found broken is reported. The rule for a value is written
  here and agrees with ``check_tolerance`` of the verification harness, which
  this module does not import.
- The tolerance is handed out as a :class:`Tolerance` of two ``float``, also
  for an integer literal, and a zero as ``0.0`` whatever its sign in the file.
  A content without the member has ``None`` in that place: it states no
  tolerance, and that is no error of the content.
- What is a value of ``source_commit`` is ADR-0022 decision 3 and not a
  convention: a string of exactly 40 or exactly 64 characters, each one of
  ``0``-``9`` and ``a``-``f``. Either length is a value: the module does not
  know or check which of the two the source repository uses. The conventions
  are that a value built in memory must be exactly a ``str``, that the
  characters themselves are compared with the sixteen ASCII ones, so a digit
  of another script is none, that the one rule is reported as a whole, and
  that a ``str`` that breaks it is shown as every ``str`` is, a long one
  shortened. The source commit is handed out as the ``str`` of the file,
  unchanged. That a content without the member states no source commit, and
  that this is no error of the content, is ADR-0022 decision 5 and not a
  convention; the convention is that it has ``None`` in that place.
- What is a value of ``n_max`` is ADR-0023 decision 3 and not a convention:
  an integer from 5 to :data:`hilclaw.keys.MAX_INTEGER`, both included, so
  ``true``, ``10.0``, ``1e1`` and ``-0`` are none. The conventions are that a
  value built in memory must be exactly an ``int`` (a subclass is none), that
  ``-0`` is refused as the integer 0 it is read as, that the one rule is
  reported as a whole, and that an ``int`` that breaks it is not shown, as
  for ``schema_version``. The bound is handed out as the ``int`` of the file,
  unchanged. A content without the member has ``None`` in that place: it
  states no bound, and that is no error of the content.
- What is a value of ``candidates_per_round`` is ADR-0028 decision 3 and not
  a convention: an integer from 1 to :data:`hilclaw.keys.MAX_INTEGER`, both
  included, so ``true``, ``2.0``, ``2e0``, ``0`` and ``-0`` are none, and a
  value above 5 is one. The conventions are that a value built in memory
  must be exactly an ``int`` (a subclass is none), that ``-0`` is refused as
  the integer 0 it is read as, that the one rule is reported as a whole, and
  that an ``int`` that breaks it is not shown, as for ``schema_version``.
  The number is handed out as the ``int`` of the file, unchanged. A content
  without the member has ``None`` in that place: it states no number of
  candidates per round, and that is no error of the content.
- What is a value of ``round_budget`` is ADR-0032 decision 3 and not a
  convention: an integer from 1 to :data:`hilclaw.keys.MAX_INTEGER`, both
  included, so ``true``, ``8.0``, ``8e0``, ``0`` and ``-0`` are none, and
  ``1``, ``4``, ``11`` and ``20`` are values. The conventions are that a value
  built in memory must be exactly an ``int`` (a subclass is none), that ``-0``
  is refused as the integer 0 it is read as, that the one rule is reported as
  a whole, and that an ``int`` that breaks it is not shown, as for
  ``schema_version``. The round budget is handed out as the ``int`` of the
  file, unchanged. That a content without the member states no round budget,
  and that this is no error of the content, is ADR-0032 decision 4 and not a
  convention; the convention is that it has ``None`` in that place.
- What is a value of ``wall_clock_budget_s`` is ADR-0033 decision 3 and not a
  convention: an integer from 1 to :data:`hilclaw.keys.MAX_INTEGER`, both
  included, that counts seconds, so ``true``, ``5400.0``, ``5.4e3``, ``0``,
  ``-0`` and every string (``"5400"``, ``"8h"`` and ``"PT90M"`` among them)
  are none, and every integer from the one end to the other is a value. The
  conventions are that a value built in memory must be exactly an ``int`` (a
  subclass is none), that ``-0`` is refused as the integer 0 it is read as,
  that the one rule is reported as a whole, and that an ``int`` that breaks
  it is not shown, as for ``schema_version``. The wall-clock budget is handed
  out as the ``int`` of the file, unchanged: a number of seconds, converted
  to no other unit. That a content without the member states no wall-clock
  budget, and that this is no error of the content, is ADR-0033 decision 4
  and not a convention; the convention is that it has ``None`` in that place.
- What is a value of ``owner`` and of ``project`` is ADR-0034 decision 3 with
  ADR-0001 decision 1 and not a convention: the string after JSON decoding,
  of 1 to 255 characters, each one from U+0020 to U+007E, so the empty
  string, a string longer than 255 characters, a string that holds a line
  feed, a tab or a letter of another script and everything that is no string
  are none, and a string of spaces only is a value. That no case is folded
  and no space removed is decision 3 too. The conventions are that a value
  built in memory must be exactly a ``str``, that the one rule is reported as
  a whole, that a ``str`` that breaks it is shown as every ``str`` is, a long
  one shortened, that the rule is written here and agrees with the *string*
  of :mod:`hilclaw.keys`, of which no private name is used, and that each
  member is handed out as the ``str`` of the file, unchanged. That a content
  without one of the two states no owner or no project, and that this is no
  error of the content, is ADR-0034 decision 4 and not a convention; the
  convention is that it has ``None`` in that place.
- What is a value of ``draws`` is ADR-0046 decision 3 and not a convention:
  an integer from 1 to :data:`hilclaw.keys.MAX_INTEGER`, both included, so
  ``true``, ``false``, ``null``, a number with a fraction or an exponent
  (``2.0`` and ``2e0`` among them), every string (``"2"`` among them), an
  array, an object, ``0``, ``-0``, every negative number and an integer
  above that range are none, and every integer from the one end to the
  other is a value. The conventions are that a value built in memory must
  be exactly an ``int`` (a subclass is none), that ``-0`` is refused as the
  integer 0 it is read as, that the one rule is reported as a whole, and
  that an ``int`` that breaks it is not shown, as for ``schema_version``.
  The number is handed out as the ``int`` of the file, unchanged. That a
  content without the member states no number of draws, and that this is no
  error of the content, is ADR-0046 decision 3 and not a convention; the
  convention is that it has ``None`` in that place.
- What is a value of ``objective`` is ADR-0053 decision 4 and not a
  convention: a value ADR-0050 accepts as the ``task.objective`` of a
  version-2 spec by its checks 1 to 3, which today is an object with exactly
  ``objectives`` and ``constraints``, ``objectives`` an array of exactly one
  entry, the entry an object with exactly ``type``, ``type`` the name
  ``latency_minimisation`` and ``constraints`` an empty array, so one value
  is valid today. Check 4 of ADR-0050, the form of a constraint entry, is
  not made: no constraint type is admitted, so every entry is refused
  whatever its form, ``memory_ceiling`` with a ``bound`` among them, and the
  written form of a ``bound`` (ADR-0053 decision 4) binds nothing here. The
  conventions are the order inside the member (an object, no member besides
  the two, both present, ``objectives`` an array of one entry, the entry an
  object, no member besides ``type``, ``type`` present, ``type`` the admitted
  name, ``constraints`` an empty array), the first rule found broken being
  reported with its place below ``objective``; that for a value built in
  memory the member and the entry must each be exactly a ``dict``, the two
  arrays exactly a ``list`` and ``type`` exactly a ``str``; and that the
  member is handed out as the ``dict`` of the file, unchanged. That a
  content without the member states no objective and no set of constraints,
  and that this is no error of the content, is ADR-0053 decision 5 and not a
  convention; the convention is that it has ``None`` in that place, which no
  present member is equal to.
- What is a value of ``coder_model`` is ADR-0136 decision 3 and not a
  convention: a full Claude model name, a string of at most 64 characters
  that begins with ``claude-``, continues with one or more ASCII lowercase
  letters, digits and ``-`` and does not end with ``-``, so an alias
  (``opus``, ``best``), ``default``, ``claude-`` alone, a name with a context
  suffix (``[1m]``), an inference-profile ARN, the empty string and
  everything that is no string are none. The conventions are that a value
  built in memory must be exactly a ``str`` (a subclass is none), that the
  characters are compared with the ASCII ones, so a lowercase letter of
  another script is none, that the one rule is reported as a whole, that a
  ``str`` that breaks it is shown as every ``str`` is, a long one shortened,
  and that the member is handed out as the ``str`` of the file, unchanged.
  That a content without the member states no coder model, and that this is
  no error of the content, is ADR-0136 decision 4 and not a convention; the
  convention is that it has ``None`` in that place.
- Which layout version a schema version states is ADR-0024 decision 3 and not
  a convention: schema version 1 states layout version 1. The conventions are
  that the pairing is a mapping keyed by the schema version with the number
  written in it, that the layout version is handed out as an ``int`` by
  :func:`layout_version_of`, which goes through :func:`read`, and that
  :class:`Instance` has no field for it, as it is no member.
- The file is read as :mod:`hilclaw.run_journal` reads ``STATE.json``:
  ``run_id`` is checked first, then ``data_root``, which is used as given and
  must be an existing directory (:class:`FileNotFoundError` or
  :class:`NotADirectoryError` otherwise). A missing file (no file, no run
  directory, a file in the place of a directory above it) raises
  :class:`MissingInstanceError`. A path that is not a regular file (a symbolic
  link is not followed) raises :class:`InvalidInstanceError`. An error about
  the content names the file by its path relative to the data root, in front
  of the message of the parser. A file that disappears between the check and
  the read is an :class:`OSError`, as every other failure of the file system.

It writes, creates and removes no file and composes no content. It defines no
member besides the fourteen (``schema_version``, ``hw_profile``,
``tolerance``, ``source_commit``, ``n_max``, ``candidates_per_round``,
``op_signature``, ``round_budget``, ``wall_clock_budget_s``, ``owner``,
``project``, ``draws``, ``objective`` and ``coder_model``) and interprets no
other: a file
it accepts is not thereby a complete instance record, and not enough to start a
run (ADR-0018 decisions 1 and 2).
Of the tolerance it gives what the file states and nothing else: it holds no
default and substitutes no value (ADR-0020 decision 3), does not check that a
run is of the first case, and gives the member no meaning for a run of another
case (#5 B-7). A file it accepts need not state a tolerance, and where it is
checked that an instance states one is open (OD-8 sub-question 19). Which tool
or component reads the member, at which moment of a call, and what a call
answers when no tolerance is stated is not said here; "not stated" is no error
of the content, and this module gives it no tool-failure kind.
Of the source commit it gives what the file states for the start of the
instance and nothing else (ADR-0022 decisions 5 and 7): it obtains no commit
and runs no ``git``, and it substitutes no value for a member that is absent,
so no constant, default or fallback of this module is a commit. It checks the
form of the member only: not that a stated commit exists anywhere, and not
that the statement is true (ADR-0022 decisions 4 and 8). It does not identify
or locate the source repository, compares the member with nothing, and says
nothing about the source of a later result of the run (OD-11) or about a
source that is not exactly a commit. A file it accepts need not state a
source commit, and where it is checked that an instance states one is open
(OD-8 sub-question 20). Which tool or component reads the member, at which
moment, and what a call answers when no source commit is stated is not said
here; "not stated" is no error of the content here either, and this module
gives it no tool-failure kind.
Of the bound of repeats it gives what the file states and nothing else
(ADR-0023 decisions 4 and 5): it holds no default and substitutes no value
for a member that is absent, not 10 and not a constant of the harness, which
it does not import. The lower bound is the number 5 of ADR-0023 decision 3,
written here, and not the constant of the measurement policy. It checks the
form of the member only: not that a measurement was or can be taken under a
stated bound. The member bounds the samples of one measurement (ADR-0023
decision 2): this module makes it no bound of measurements, attempts,
candidates or rounds and no budget member. A file it accepts need not state
a bound; whether a measurement of a run that states none may be taken, and
where it is checked that an instance states its bound, is open (OD-8
sub-question 21). Which tool or component reads the member, at which moment,
and what a call answers when no bound is stated is not said here; "not
stated" is no error of the content here either, this module gives it no
tool-failure kind, and :func:`n_max_of` is bound to no tool and to no timing
run.
Of the number of candidates per round it gives what the file states and
nothing else (ADR-0028 decisions 4 and 5): it holds no default and substitutes
no value for a member that is absent, not 1 and not a number taken from
another member, from another run or from a spec. The lower end is the number
1 of ADR-0028 decision 3, written here, and there is no upper end below
:data:`hilclaw.keys.MAX_INTEGER`: the module holds no range of a user
interface, and a value above 5 is a value. It checks the form of the member
only. It does not read, import or compare a spec and concludes nothing about
the ``id.candidates`` of one (ADR-0028 decision 5). It does not say that any
round of the run had, has or will have that many candidates, and it makes the
member no number of coder calls, of specs, of attempts or of promoted
candidates and no budget member (ADR-0028 decision 2). A file it accepts need
not state the number; where it is checked that an instance states one, and
what follows for a round of a run whose valid file states none, is open (OD-8
sub-question 25). Which tool or component reads the member and at which
moment is not said here (ADR-0028 decision 5 and Boundaries); "not stated" is
no error of the content here either, this module gives it no tool-failure
kind, and :func:`candidates_per_round_of` is bound to no tool and to nothing
that issues a spec.
Of the op_signature it gives what the file states and nothing else (ADR-0031
decisions 5 and 6): it substitutes nothing for a member that is absent, no
record, no key and no constant of this module, and nothing taken from
``hw_profile``, from another member, from another run, from a spec or from a
directory below ``db/``. The record is judged by
:func:`hilclaw.keys.op_signature_key` alone: this module holds no list of
kinds, dtypes, layouts or shapes and no value of M, so a record of a kind
that function does not know makes the file invalid here (ADR-0031 decision
7). It reads, imports and compares no spec, reads no file below ``db/``,
compares the member with no other member and does not conclude that a stored
record or a directory exists for the key (decisions 2 and 6). It does not
say that a spec, a measurement or a result of the run concerns the stated
operation, that the run is of the first case, or which kernel contract or
kernel language the run has (decision 2). It does not say that an instance
concerns no more than one op_signature: the member is one object because a
file of version 1 states at most one, and whether one instance may cover
several values of M is open (ADR-0031 decision 4; OD-6 sub-question 3). A
file it accepts need not state an op_signature; where it is checked that an
instance states one, and what follows for a run whose valid file states
none, is open (OD-8 sub-question 28). Which tool or component reads the
member and at which moment is not said here (ADR-0031 decision 6 and
Boundaries); "not stated" is no error of the content here either, this
module gives it no tool-failure kind, and :func:`op_signature_of` is bound to
no tool, to no spec and to nothing below ``db/``.
Of the round budget it gives what the file states and nothing else (ADR-0032
decisions 4 and 5): it holds no default and substitutes no value for a member
that is absent, no number, no infinity or other sign of "unlimited", no
constant of this module and nothing taken from another member, from another
file of the run, from a count of round directories or from another run. It
does not read "not stated" as "unlimited", as a default or as zero, and it
concludes neither that the run may go on without end nor that it may not
begin (ADR-0032 decision 4). The lower end is the number 1 of ADR-0032
decision 3, written here, and there is no upper end below
:data:`hilclaw.keys.MAX_INTEGER`: the module holds no range of the cap of the
initial runs (#5 B-4, a budget of 5 to 10 rounds), which ADR-0032 decision 3
reads as no rule of the file, so 1, 4, 11 and 20 are values as 5 and 10 are.
It checks the form of the member only. It does not read, import or compare
``STATE.json``, the journal or the spend view, and it concludes nothing from
the member and a ``round`` together (ADR-0032 decision 5). It counts nothing,
says nothing of what counts against the budget, stops nothing and ends no run
(ADR-0032 decisions 2 and 5). It does not say that the run had, has or will
have that many rounds. It makes the member no number of candidates per round
and no ``n_max``, no number of coder calls, of specs, of attempts or of
repair calls, no amount of tokens, of time or of hardware quota and no target
metric, and it makes the member no statement of any other budget axis
(ADR-0032 decision 2 and Boundaries). A file it accepts need not state a round
budget; what counts against a stated one, whether an instance may start with
no budget axis and what ends a run whose valid file states none, is open (OD-8
sub-question 29).
Which tool or component reads the member, at which moment, and what follows
when no round budget is stated is not said here (ADR-0032 decision 5 and
Boundaries); "not stated" is no error of the content here either, this module
gives it no tool-failure kind, and :func:`round_budget_of` is bound to no
tool, to no ``STATE.json`` and to nothing that ends a run.
Of the wall-clock budget it gives what the file states and nothing else
(ADR-0033 decisions 4 and 5): it holds no default and substitutes no value for
a member that is absent, no number, no infinity or other sign of "unlimited",
no constant of this module and nothing taken from ``round_budget`` or from
another member, from another file of the run, from the ``time`` values of a
log, from the time part of a ``run_id`` or from another run. It does not read
"not stated" as "unlimited", as a default or as zero, and it concludes neither
that the run may go on without end nor that it may not begin (ADR-0033
decision 4). The lower end is the number 1 of ADR-0033 decision 3, written
here, and there is no upper end below :data:`hilclaw.keys.MAX_INTEGER`: the
"8h" of StandardScenarios S2 is no rule of this module, as ADR-0033 decision
3 reads it as the value of an example and as no cap, no default and no
typical value. It checks the form of the member only. It hands out a number
of seconds and converts nothing: it accepts no other unit or notation and
produces none (ADR-0033 decision 3). It reads no clock and measures no time,
and it does not say from which moment the time runs, what counts against the
budget or against which clock it is read: that is not decided (ADR-0033
decision 2; OD-8 sub-question 30). It does not read, import or compare
``STATE.json``, the journal, the log or the spend view, and it concludes
nothing from the member together with a ``round``, with the ``time`` of a
line of a log or with the time part of a ``run_id`` (ADR-0033 decision 5). It
adds no rule between the member and ``round_budget``: each is valid by
itself, a file may state either, both or neither, and neither bounds the
other (ADR-0033 decision 5). It counts nothing, stops nothing and ends no
run, and it does not say that the run took, takes or will take that long
(ADR-0033 decisions 2 and 5). It makes the member no time of day and no
deadline, no limit of one process, build, measurement, coder call or tool
call (it is no ``timeout_s``), no amount of hardware time, no number of
rounds, no amount of tokens and no target metric (ADR-0033 decision 2). The
name is that of a member of this file and of nothing else: the module names
no axis of the spend view (ADR-0033 decision 3). A file it accepts need not
state a wall-clock budget; whether an instance may start with no budget axis
and what ends a run whose valid file states none is open (OD-8 sub-question
29). Which tool or component reads the member, at which moment, and what
follows when no wall-clock budget is stated is not said here (ADR-0033
decision 5 and Boundaries); "not stated" is no error of the content here
either, this module gives it no tool-failure kind, and
:func:`wall_clock_budget_s_of` is bound to no tool, to no clock, to no
``STATE.json``, to no log and to nothing that ends a run.
Of the owner and of the project it gives what the file states and nothing
else (ADR-0034 decisions 4 and 5): it holds no default and substitutes nothing
for a member that is absent, not the user name of a process, not the author or
the committer of a commit, not a GitHub account, not the name of a directory,
of the data repository or of the source repository, not a part of the
``run_id``, not the value of the other member or of another run and no
constant of this module. It does not conclude that a run without the member
has no owner or belongs to no project, only that the file states none
(ADR-0034 decision 4). It checks the form of the members only. It makes
neither value an identity: not the name of a person, of an account or of a
service account, not a user name of an operating system, not an author or a
committer, not a GitHub account and not the account of a Claude Code session,
and it checks the value against none (ADR-0034 decision 2). It draws no right
from either value: no access control exists (ADR-0010 decision 8), and what
is shared or promoted is OD-25, which this module does not enter. It makes
neither value a path level or a part of a ``run_id``. It folds no case and
removes no space, so two values that differ in any character are two values
(ADR-0034 decision 3). It relates no two runs by equal values and looks up,
groups, counts, orders, refuses and notifies nothing by either value, and it
adds no rule between the two members or between either and another member
(the ``hw_source`` and the ``label`` of the hw_profile record and
``source_commit`` among them), another file or another run (ADR-0034
decisions 2 and 5). The member ``owner`` is not the holder of a lock of a
``STATE.json``, a lock no record defines (OD-17), and not the ``lock.owner``
of the ``PROCESS/STATE.json`` of the development driver
(:mod:`hilclaw.driver_state`, which this module does not import). A file it
accepts need not state an owner or a project; what an owner and a project of
a run are beyond a stated name, where the start of an instance takes the
names from, whether anything checks them and what follows for a run whose
valid file states none is open (OD-8 sub-question 31). Which tool or
component reads the members and at which moment is not said here (ADR-0034
decision 5 and Boundaries); "not stated" is no error of the content here
either, this module gives it no tool-failure kind, and :func:`owner_of` and
:func:`project_of` are bound to no tool, to no hook, to no ``STATE.json``, to
nothing below ``db/`` and to nothing that lists, groups or allows.
Of the number of draws it gives what the file states and nothing else
(ADR-0046 decision 3): it holds no default and substitutes no value for a
member that is absent, not 1, not the 2 that stands in the Example of that
record, no constant of this module or of the harness, which it does not
import, and nothing taken from another member or from another run. The lower
end is the number 1 of ADR-0046 decision 3, written here; there is no lower
end above it and no upper end below :data:`hilclaw.keys.MAX_INTEGER`, which
is the end of the form of an integer of ADR-0001 and no bound chosen for a
number of draws, and a valid value is not thereby one a check can be carried
out with (ADR-0046 decision 3). It checks the form of the member only. It
does not check that the run is one ADR-0046 gives the member a meaning for,
a run of the first case or one whose hw_profile names the mock, and it gives
the member no meaning for any other run (ADR-0046 decisions 1 and 3). It
makes the member no budget member and no bound (ADR-0046 decision 3), no
number of repeats of a timing measurement (it is no ``n_max``) and no number
of candidates, of attempts, of checks or of executions. It does not say
which number an instance should state, whether a promotion-level
re-verification or a gate uses another number or whether the two execution
points use two: none of that is decided (ADR-0046 decision 7). It compares
the member with nothing: not with ``n_max``, with ``candidates_per_round``,
with ``op_signature``, with ``tolerance`` or with a limit of the harness. A
file it accepts need not state a number of draws; whether the start of an
instance checks that one is stated is open (OD-8 sub-question 32). Which
tool reads the member, at which moment, and what a call answers for a valid
file without it is said by ADR-0046 decisions 4 and 5 for
``correctness.check`` and is not done here: "not stated" is no error of the
content here either, this module gives it no tool-failure kind, and
:func:`draws_of` is bound to no tool and to no check.
Of the objective it gives what the file states and nothing else (ADR-0053
decisions 5 and 7): it holds no default and substitutes nothing for a member
that is absent, not ``latency_minimisation``, though that is the only type a
file can state today, not the one valid value, not an empty set of
constraints, no constant of this module and nothing taken from a spec, from
another member or from another run. It does not conclude that a run whose
file lacks the member has no constraint: "no constraint" is stated by a
present member whose ``constraints`` is empty and by nothing else, and a
top-level member of a nearby name (``objectives``, ``target``) is passed
over (ADR-0053 decision 5 and L3). The rule is ADR-0050's, taken by citation
(ADR-0053 decision 4); it is written here and agrees with
:mod:`hilclaw.spec`, of which nothing is imported, and the type name is held
as what makes a member valid and is handed out for no file that does not
state it. It checks the form of the member only. It judges, measures and
stops nothing (ADR-0053 L4): it makes the member no target metric of FR-3,
no budget, no tolerance and no baseline, and it does not say that anything
was measured or that a constraint is met (ADR-0053 decision 3). It reads,
imports and compares no spec and does not say that a spec of the run
carries the same value (ADR-0053 decision 6 and L8), and it adds no rule
between the member and another member, another file or another run. It does
not say that the quantity of the type can be measured where the run
executes (ADR-0053 L9). No memory ceiling and no throughput can be stated
yet (ADR-0053 L5). A file it accepts need not state a target; that an
instance states one is FR-2's, and where that is checked is open (ADR-0053
decision 5; OD-8 sub-question 34 (i)).
Which call reads the member and what it answers when none is stated is not
said: those are the contracts of the run tools (ADR-0053 decision 7; OD-18;
OD-13 sub-question 10); "not stated" is no error of the content here either,
this module gives it no tool-failure kind, and
:func:`objective_of` is bound to no tool, to no spec and to nothing that
judges a candidate.
Of the coder model it gives what the file states and nothing else (ADR-0136
decisions 3 and 4): it holds no default and substitutes nothing for a member
that is absent, no model name, no alias, no constant of this module and
nothing taken from another member or from another run. The default of Opus
is applied by the start of an instance, which records it in the file
(ADR-0136 decision 4, a later code slice), and never by a reader here. It
checks the form of the member only, not whether a model of that name is
offered: it holds no list of models, so a misspelt name of the right form is
a value (ADR-0136 decision 3, "The cost"). The member states the model the
coder calls of the run request, not the one that ran, which may differ
(ADR-0136 decision 3). It folds no case and resolves no name. A top-level
member of a nearby name (``model``, ``coderModel``, ``coder``) is passed
over (ADR-0136 decision 2). "Not stated" is no error of the content here
either, this module gives it no tool-failure kind, and :func:`coder_model_of`
is bound to no tool and starts nothing: the read of the member at a coder
call and its failure kinds are ADR-0136 decision 5 and are not done here.
Of the layout version it gives what the ``schema_version`` of a valid file
states by the pairing of ADR-0024 decision 3 and nothing else (decisions 4
and 5). It defines no member for the layout version and interprets none: a
member named ``layout_version`` is passed over, is handed back among the
members not defined and is no stamp (decision 6). The number is the one the
record pairs with schema version 1, written here; it is not taken from
:data:`hilclaw.layout.LAYOUT_VERSION`, which this module does not read. It
compares the stamp with nothing and refuses no run on that ground. It does
not check that the tree of the run has the stated layout or which of its
files exist, and the stamp says nothing about ``db/``, about ``blobs/`` or
about the content of any other file (decision 2). For a file of another
``schema_version`` it has no layout version and infers none: neither that the
layout differs nor that it is the same. For a call of a tool whose tool
function carries out the lookup of a journaled tool or the selection of a HW
tool about a run, ADR-0030 decision 3 says when the call has the stamp: after
the data root was obtained and before it uses any other path of that run.
:func:`hilclaw.journaled_tool.checked_function`, the part the two builders of
such a tool function share, calls :func:`layout_version_of` for that. Whether
and at which moment another user of a path of a run has the stamp, and
whether a source holds the stamp against the layout it builds, is not said
here (OD-8 sub-question 27), and neither is what states the layout of
``db/``, of ``blobs/`` and of the rest of the top level (part (ii) of
sub-question 22).
It reads no other file, so no stored record below ``db/``, of the hw_profile
key or of the op_signature key, is read or compared (ADR-0018 decision 4,
ADR-0031 decision 6) and no reader here needs one to exist; how an embedded
record and the stored one relate is open (OD-8 sub-question 18 for the
hw_profile, part (iii) of sub-question 28 for the op_signature). None of its
errors is a :class:`hilclaw.tools.ToolFailure`: the kind a call of a tool
answers for them is given by the tool function that calls :func:`hw_profile_of`
or :func:`layout_version_of` (:mod:`hilclaw.hw_tool`,
:mod:`hilclaw.journaled_tool`; ADR-0019, ADR-0030), not here. It reads no other
version (OD-11) and says nothing of what writes the file, of when, or of a run
directory without it (OD-8 sub-questions 10 and 17). Nothing is kept between
calls, so a file changed between two calls is read as changed (ADR-0018
decision 6).
"""

import codecs
import json
import math
import os
import reprlib
import stat
from pathlib import Path
from typing import NamedTuple

from hilclaw import keys, layout

SCHEMA_VERSION = 1

_MAX = keys.MAX_INTEGER
_DEFINED = (
    "schema_version",
    "hw_profile",
    "tolerance",
    "source_commit",
    "n_max",
    "candidates_per_round",
    "op_signature",
    "round_budget",
    "wall_clock_budget_s",
    "owner",
    "project",
    "draws",
    "objective",
    "coder_model",
)
_SECTION = ("key", "record")
_TOLERANCE = ("rtol", "atol")
_COMMIT_LENGTHS = (40, 64)
_COMMIT_CHARACTERS = frozenset("0123456789abcdef")
_STATED_LAYOUT = {SCHEMA_VERSION: 1}
_OBJECTIVE = ("objectives", "constraints")
_OBJECTIVE_ENTRY = ("type",)
_OBJECTIVE_TYPES = ("latency_minimisation",)


class InvalidInstanceError(ValueError):
    """A content, a document or a path breaks a rule; the message names it.

    The rules are those of ADR-0018, ADR-0020, ADR-0022, ADR-0023, ADR-0028,
    ADR-0031, ADR-0032, ADR-0033, ADR-0034, ADR-0046, ADR-0053 and ADR-0136
    and the conventions of this module.
    """


class UnsupportedVersionError(Exception):
    """``schema_version`` is an integer other than 1: not damage, and nothing is interpreted."""


class MissingInstanceError(Exception):
    """No instance record was written for the ``run_id``; the message names the path."""


class Tolerance(NamedTuple):
    """The tolerance a content states (ADR-0020 decision 2): ``rtol`` and ``atol``.

    As :func:`parse` returns it, both are ``float``, finite and not negative.
    They are what the content states, in the vocabulary of the first case; no
    value here is a default.
    """

    rtol: float
    atol: float


class OpSignature(NamedTuple):
    """The op_signature a content states (ADR-0031 decisions 2 and 3).

    ``key`` is ``op_signature.key`` and ``record`` is ``op_signature.record``.
    As :func:`parse` returns it, the record is one that
    :func:`hilclaw.keys.op_signature_key` accepts and the key is the name
    derived from it. Both are what the content states; neither is a default,
    and neither says that a stored record exists for the key.
    """

    key: str
    record: dict


class Instance(NamedTuple):
    """Result of :func:`parse`: what a content states and the members not defined.

    ``tolerance`` is a :class:`Tolerance`, or ``None`` for a content without
    the member ``tolerance``. ``source_commit`` is the ``str`` of the member
    ``source_commit``, or ``None`` for a content without that member.
    ``n_max`` is the ``int`` of the member ``n_max``, or ``None`` for a content
    without that member. ``candidates_per_round`` is the ``int`` of the member
    ``candidates_per_round``, or ``None`` for a content without that member.
    ``op_signature`` is an :class:`OpSignature`, or ``None`` for a content
    without the member ``op_signature``. ``round_budget`` is the ``int`` of
    the member ``round_budget``, or ``None`` for a content without that
    member. ``wall_clock_budget_s`` is the ``int`` of the member
    ``wall_clock_budget_s``, a number of seconds, or ``None`` for a content
    without that member. ``owner`` and ``project`` are each the ``str`` of the
    member of that name, unchanged, or ``None`` for a content without that
    member: ``None`` says that the content states none. ``draws`` is the
    ``int`` of the member ``draws``, a number of draws, or ``None`` for a
    content without that member. ``objective`` is the ``dict`` of the member
    ``objective``, the objectives and the constraints the content states
    (ADR-0053 decision 4), or ``None`` for a content without that member:
    ``None`` says that the content states no objective and no set of
    constraints, and is not an empty set of constraints (ADR-0053 decision 5).
    ``coder_model`` is the ``str`` of the member ``coder_model``, the full
    name of the Claude model the run's coder calls request, unchanged, or
    ``None`` for a content without that member: ``None`` says that the
    content states no coder model, and no model stands in (ADR-0136 decision
    4). No field has a default. ``others`` is the last field.
    """

    hw_profile_key: str
    hw_profile: dict
    tolerance: Tolerance | None
    source_commit: str | None
    n_max: int | None
    candidates_per_round: int | None
    op_signature: OpSignature | None
    round_budget: int | None
    wall_clock_budget_s: int | None
    owner: str | None
    project: str | None
    draws: int | None
    objective: dict | None
    coder_model: str | None
    others: dict


def parse(content):
    """Return the :class:`Instance` of ``content``, the bytes of an ``instance.json``.

    ``hw_profile_key`` is ``hw_profile.key`` and ``hw_profile`` is
    ``hw_profile.record``, the ``dict`` parsed from this content;
    ``tolerance`` is the :class:`Tolerance` of the member ``tolerance``, each
    value the ``float`` of its literal (``2`` gives ``2.0``; ``-0``, ``-0.0``,
    ``-1e-999`` and ``1e-999`` give ``0.0``), or ``None`` when the content has
    no such member, and no value is substituted then; ``source_commit`` is
    the string of the member ``source_commit`` as the content states it
    (ADR-0022 decision 3), not normalised, shortened or resolved, or ``None``
    when the content has no such member, and no value is substituted then
    either; ``n_max`` is the ``int`` of the member ``n_max`` as the content
    states it (ADR-0023 decision 3), not clamped, rounded or replaced, or
    ``None`` when the content has no such member, and no value is substituted
    then either; ``candidates_per_round`` is the ``int`` of the member
    ``candidates_per_round`` as the content states it (ADR-0028 decision 3),
    not clamped to a range, rounded or replaced, or ``None`` when the content
    has no such member, and no value is substituted then either, 1 included;
    ``op_signature`` is the :class:`OpSignature` of the member
    ``op_signature`` (ADR-0031 decision 3), its ``key`` the ``str`` and its
    ``record`` the ``dict`` parsed from this content, or ``None`` when the
    content has no such member, and nothing is substituted then either, no
    record and no key; ``round_budget`` is the ``int`` of the member
    ``round_budget`` as the content states it (ADR-0032 decision 3), not
    clamped to a range, rounded or replaced, or ``None`` when the content has
    no such member, and no value is substituted then either: ``None`` is not
    "unlimited", not a default and not zero (ADR-0032 decision 4);
    ``wall_clock_budget_s`` is the ``int`` of the member
    ``wall_clock_budget_s`` as the content states it (ADR-0033 decision 3), a
    number of seconds, not converted to another unit, clamped to a range,
    rounded or replaced, or ``None`` when the content has no such member, and
    no value is substituted then either: ``None`` is not "unlimited", not a
    default and not zero (ADR-0033 decision 4); ``owner`` and ``project``
    are each the string of the member of that name as the content states it
    after JSON decoding (ADR-0034 decision 3), with no case folded, no space
    removed and nothing normalised, shortened or split, or ``None`` when the
    content has no such member, and nothing is substituted then either:
    ``None`` is no default and no anonymous or shared value (ADR-0034
    decision 4); ``draws`` is the ``int`` of the member ``draws`` as the
    content states it (ADR-0046 decision 3), not clamped to a range, rounded
    or replaced, or ``None`` when the content has no such member, and no
    value is substituted then either, 1 included; ``objective`` is the
    ``dict`` of the member ``objective`` as parsed from this content
    (ADR-0053 decision 4), with its ``objectives`` and its ``constraints``,
    not completed, reordered or replaced, or ``None`` when the content has no
    such member, and nothing is substituted then either: ``None`` is no
    default, not ``latency_minimisation`` and not an empty set of
    constraints (ADR-0053 decision 5); ``coder_model`` is the string of the
    member ``coder_model`` as the content states it (ADR-0136 decision 3),
    not lower-cased, stripped, resolved or replaced, or ``None`` when the
    content has no such member, and nothing is substituted then either:
    ``None`` is no default, no alias and no model name (ADR-0136 decision 4);
    ``others`` holds every top-level member that is none of
    ``schema_version``, ``hw_profile``, ``tolerance``, ``source_commit``,
    ``n_max``, ``candidates_per_round``, ``op_signature``, ``round_budget``,
    ``wall_clock_budget_s``, ``owner``, ``project``, ``draws``,
    ``objective`` and ``coder_model``, as parsed and not interpreted,
    whatever its name and value (``tolerence``, a top-level ``rtol``,
    ``source-commit``, ``nmax``, ``candidates``, ``op``, ``task``,
    ``rounds``, ``budget``, ``wall_clock_budget``, ``time_budget``,
    ``Owner``, ``user``, ``username``, ``projectname``, ``n_draws``,
    ``Draws``, ``check_draws``, ``objectives``, a top-level ``constraints``,
    ``target``, ``Objective``, ``goal``, ``model``, ``coderModel``,
    ``coder_models`` or ``coder`` among them).
    Any order of members and any white space of JSON are accepted.

    Raises :class:`InvalidInstanceError` when ``content`` is not UTF-8 without
    a byte order mark, is not exactly one JSON text (the tokens ``NaN``,
    ``Infinity`` and ``-Infinity`` are no JSON; an empty content is none),
    holds a member name twice in any object or is a document :func:`validate`
    refuses, and :class:`UnsupportedVersionError` as that function does.
    Nothing is returned then, and nothing is repaired.
    """
    if type(content) is not bytes:
        raise TypeError(f"content must be bytes, got {type(content).__name__}")
    if content.startswith(codecs.BOM_UTF8):
        raise InvalidInstanceError("content: starts with a byte order mark")
    try:
        text = content.decode("utf-8")
        document = json.loads(text, object_pairs_hook=_object, parse_constant=_nan)
    except RecursionError:
        raise InvalidInstanceError("content: is nested too deeply to parse") from None
    except ValueError as error:
        reason = f"content: cannot be read as one JSON text: {error}"
        raise InvalidInstanceError(reason) from None
    return _checked(document)


def validate(document):
    """Check ``document``, a parsed ``instance.json``, against the twelve records.

    ``document`` must be a ``dict`` with ``schema_version`` (an ``int`` from 0
    to :data:`hilclaw.keys.MAX_INTEGER`) and, at version 1, ``hw_profile``: a
    ``dict`` with exactly ``key`` and ``record``, the record a ``dict`` that
    :func:`hilclaw.keys.hw_profile_key` accepts and the key the name derived
    from it (ADR-0018 decisions 2 and 3). It may hold ``tolerance``, which is
    then a ``dict`` with exactly ``rtol`` and ``atol``, each exactly an ``int``
    or a ``float`` whose ``float`` is finite and not negative (ADR-0020
    decisions 2 to 4): for a value built in memory, an infinity, a NaN and an
    ``int`` that no ``float`` holds are invalid, and a ``bool`` is no number.
    It may hold ``source_commit``, which is then exactly a ``str`` of 40 or of
    64 characters, each one of ``0``-``9`` and ``a``-``f`` (ADR-0022 decisions
    3 and 5): for a value built in memory, a subclass of ``str`` and a
    ``bytes`` are none. Only that form is checked, not that such a commit
    exists. It may hold ``n_max``, which is then exactly an ``int`` from 5 to
    :data:`hilclaw.keys.MAX_INTEGER`, both included (ADR-0023 decisions 3 and
    4): for a value built in memory, a ``bool``, a ``float`` such as ``10.0``
    and a subclass of ``int`` are none. Only that form is checked, not that a
    measurement was or can be taken under the bound. It may hold
    ``candidates_per_round``, which is then exactly an ``int`` from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`, both included (ADR-0028 decisions 3 and
    4): for a value built in memory, a ``bool``, a ``float`` such as ``2.0``
    and a subclass of ``int`` are none. Only that form is checked: the member
    is compared with no spec and with no range of a user interface. It may
    hold ``op_signature``, which is then a ``dict`` with exactly ``key`` and
    ``record``, the record a ``dict`` that
    :func:`hilclaw.keys.op_signature_key` accepts and the key exactly a
    ``str``, the name derived from it (ADR-0031 decisions 3 and 5): for a
    value built in memory, a subclass of ``dict`` and one of ``str`` are
    none. Only that is checked: the member is compared with no spec, with no
    file below ``db/`` and with no other member. It may hold
    ``round_budget``, which is then exactly an ``int`` from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`, both included (ADR-0032 decisions 3 and
    4): for a value built in memory, a ``bool``, a ``float`` such as ``8.0``
    and a subclass of ``int`` are none. Only that form is checked: the member
    is compared with no other member, with no other file and with no range a
    run is started in. It may hold ``wall_clock_budget_s``, which is then
    exactly an ``int`` from 1 to :data:`hilclaw.keys.MAX_INTEGER`, both
    included, a number of seconds (ADR-0033 decisions 3 and 4): for a value
    built in memory, a ``bool``, a ``float`` such as ``5400.0`` and a
    subclass of ``int`` are none. Only that form is checked: the member is
    compared with no other member, with no other file and with no clock. It
    may hold ``owner`` and it may hold ``project``, each of which is then
    exactly a ``str`` of 1 to 255 characters, each one from U+0020 to U+007E
    (ADR-0034 decisions 3 and 4): for a value built in memory, a subclass of
    ``str`` and a ``bytes`` are none. Only that form is checked: neither is
    compared with the other, with another member, with another file or with
    an identity. It may hold ``draws``, which is then exactly an ``int``
    from 1 to :data:`hilclaw.keys.MAX_INTEGER`, both included (ADR-0046
    decision 3): for a value built in memory, a ``bool``, a ``float`` such
    as ``2.0`` and a subclass of ``int`` are none. Only that form is
    checked: the member is compared with no other member and with no limit
    of the harness, and that a check can be carried out with the number is
    not checked. It may hold ``objective``, which is then a ``dict`` with
    exactly ``objectives`` and ``constraints``, ``objectives`` a ``list`` of
    exactly one entry, the entry a ``dict`` with exactly ``type``, ``type``
    the ``str`` ``latency_minimisation`` and ``constraints`` an empty
    ``list`` (ADR-0053 decisions 4 and 5, with the checks 1 to 3 of
    ADR-0050): for a value built in memory, a subclass of ``dict``, of
    ``list`` or of ``str`` and a ``tuple`` are none. Only that form is
    checked: the member is compared with no spec, with no other member and
    with no other file, and that the quantity of the type can be measured is
    not checked. It may hold ``coder_model``, which is then exactly a ``str``
    of at most 64 characters, ``claude-`` followed by one or more ASCII
    lowercase letters, digits and ``-``, not ending with ``-`` (ADR-0136
    decisions 3 and 4): for a value built in memory, a subclass of ``str``
    and a ``bytes`` are none. Only that form is checked: the name is
    compared with no list of offered models. Its other members are not
    looked at. The rules for the text (the encoding, a member name twice)
    cannot be checked on a parsed value. The twelve records are ADR-0018,
    ADR-0020, ADR-0022, ADR-0023, ADR-0028, ADR-0031, ADR-0032, ADR-0033,
    ADR-0034, ADR-0046, ADR-0053 and ADR-0136; ADR-0024 adds no rule of
    validity.

    Raises :class:`InvalidInstanceError` for the first rule found broken,
    naming the place (for example ``hw_profile.record.accelerator``,
    ``tolerance.rtol``, ``source_commit``, ``n_max``,
    ``candidates_per_round``, ``op_signature.key``, ``round_budget``,
    ``wall_clock_budget_s``, ``owner``, ``project``, ``draws``,
    ``objective.objectives[0].type`` or ``coder_model``). The
    version comes first: an integer other than :data:`SCHEMA_VERSION` raises
    :class:`UnsupportedVersionError` before any other member is looked at.
    """
    _checked(document)


def read(data_root, run_id):
    """Return the :class:`Instance` of the run ``run_id``, read from its ``instance.json``.

    The bytes of ``runs/<run_id>/instance.json`` below ``data_root`` are given
    to :func:`parse`; no other file is read and nothing is written. The whole
    file is read at each call and nothing is kept, so each call returns new
    objects.

    Raises :class:`hilclaw.layout.InvalidPathValueError` for a ``run_id`` that
    is none, before the file system is touched; :class:`FileNotFoundError` or
    :class:`NotADirectoryError` when ``data_root`` is no existing directory;
    then one error for each situation of ADR-0018 decision 4:
    :class:`MissingInstanceError` when there is no file, an :class:`OSError`
    of the file system, unchanged, when it cannot be read,
    :class:`InvalidInstanceError` for an invalid content, an empty file
    included, and :class:`UnsupportedVersionError` for another version. A path
    that is not a regular file is none of the four: by the convention of this
    module it raises :class:`InvalidInstanceError`.
    """
    path = layout.run_file(data_root, run_id, "instance.json")
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    file = path.relative_to(root).as_posix()
    try:
        status = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        reason = f"{file}: is missing: no instance record was written for this run_id"
        raise MissingInstanceError(reason) from None
    if not stat.S_ISREG(status.st_mode):
        raise InvalidInstanceError(f"{file}: is not a regular file")
    try:
        return parse(path.read_bytes())
    except (InvalidInstanceError, UnsupportedVersionError) as error:
        raise type(error)(f"{file}: {error}") from None


def hw_profile_of(data_root, run_id):
    """Return the hw_profile record the run ``run_id`` states (ADR-0018 decision 4).

    It is the ``hw_profile`` of what :func:`read` returns: the
    ``hw_profile.record`` of ``runs/<run_id>/instance.json``, a ``dict`` valid
    by ADR-0001 and new at each call, which the caller may hand to
    :func:`hilclaw.backends.select`. Raises what :func:`read` raises, so
    :class:`InvalidInstanceError` also for a file whose ``tolerance``,
    ``source_commit``, ``n_max``, ``candidates_per_round``,
    ``op_signature``, ``round_budget``, ``wall_clock_budget_s``, ``owner``,
    ``project``, ``draws``, ``objective`` or ``coder_model`` is invalid: no
    member of an invalid file is used (ADR-0020 decision 3, ADR-0022
    decision 5, ADR-0023 decision 4, ADR-0028 decision 4, ADR-0031 decision
    5, ADR-0032 decision 4, ADR-0033 decision 4, ADR-0034 decision 4,
    ADR-0046 decision 3, ADR-0053 decision 5, ADR-0136 decision 3).
    """
    return read(data_root, run_id).hw_profile


def tolerance_of(data_root, run_id):
    """Return the tolerance the run ``run_id`` states, or ``None`` when it states none.

    It is the ``tolerance`` of what :func:`read` returns (ADR-0020 decision
    5): a :class:`Tolerance` with the ``rtol`` and the ``atol`` of the member
    ``tolerance`` of ``runs/<run_id>/instance.json``, new at each call, or
    ``None`` for a valid file without that member. ``None`` says that no
    tolerance is stated; no value stands in for it, here or in a default of
    this module. Raises what :func:`read` raises, so no tolerance is returned
    for a missing, unreadable or invalid file or one of another version.
    """
    return read(data_root, run_id).tolerance


def source_commit_of(data_root, run_id):
    """Return the source commit the run ``run_id`` states, or ``None`` when it states none.

    It is the ``source_commit`` of what :func:`read` returns (ADR-0022
    decision 7): the string of the member ``source_commit`` of
    ``runs/<run_id>/instance.json``, 40 or 64 characters of ``0``-``9`` and
    ``a``-``f``, as the file states it at this call, or ``None`` for a valid
    file without that member. ``None`` says that no source commit is stated;
    no value stands in for it (ADR-0022 decision 5): not the commit of the
    source this function runs from, which it does not look for. The string is
    what the file states for the start of the instance; that the commit
    exists or that the statement is true is not checked. Raises what
    :func:`read` raises, so no source commit is returned for a missing,
    unreadable or invalid file or one of another version.
    """
    return read(data_root, run_id).source_commit


def n_max_of(data_root, run_id):
    """Return the bound of repeats the run ``run_id`` states, or ``None`` when it states none.

    It is the ``n_max`` of what :func:`read` returns (ADR-0023 decision 5):
    the ``int`` of the member ``n_max`` of ``runs/<run_id>/instance.json``,
    from 5 to :data:`hilclaw.keys.MAX_INTEGER`, as the file states it at this
    call, or ``None`` for a valid file without that member. The member
    states the largest number of samples one timing measurement may hold
    (ADR-0023 decision 2). ``None`` says that no bound is stated; no value
    stands in for it (ADR-0023 decision 4): not 10, not a constant of the
    harness and not the bound of another run. That a measurement was or can
    be taken under the bound is not checked, and nothing here hands the
    bound to a measurement. Raises what :func:`read` raises, so no bound is
    returned for a missing, unreadable or invalid file or one of another
    version.
    """
    return read(data_root, run_id).n_max


def candidates_per_round_of(data_root, run_id):
    """Return the candidates per round the run ``run_id`` states, or ``None`` when it states none.

    It is the ``candidates_per_round`` of what :func:`read` returns (ADR-0028
    decision 5): the ``int`` of the member ``candidates_per_round`` of
    ``runs/<run_id>/instance.json``, from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`, as the file states it at this call, or
    ``None`` for a valid file without that member. The member states the
    number of candidates per round the instance was started with (ADR-0028
    decision 2). ``None`` says that no number is stated; no value stands in
    for it (ADR-0028 decision 4): not 1, not a number of a range a user is
    offered, not a constant of this module, not a number taken from a spec
    and not the number of another run. The number is compared with nothing:
    not with a spec, and that a round had or will have that many candidates
    is not checked. Raises what :func:`read` raises, so no number is
    returned, and none is inferred, for a missing, unreadable or invalid
    file or one of another version.
    """
    return read(data_root, run_id).candidates_per_round


def op_signature_of(data_root, run_id):
    """Return the op_signature the run ``run_id`` states, or ``None`` when it states none.

    It is the ``op_signature`` of what :func:`read` returns (ADR-0031
    decision 6): an :class:`OpSignature` with the ``key`` and the ``record``
    of the member ``op_signature`` of ``runs/<run_id>/instance.json`` as the
    file states them at this call, the record a ``dict`` valid by ADR-0001
    and new at each call and the key the name derived from it, or ``None``
    for a valid file without that member. ``None`` says that no op_signature
    is stated; nothing stands in for it (ADR-0031 decision 5): not the
    ``task.op_signature`` of a spec, not the name of a directory below
    ``db/``, not the op_signature of another run, not a constant of this
    module and nothing inferred from another member. No spec and no file
    below ``db/`` is read, and the result is compared with nothing: that a
    stored record exists for the key, or that a spec, a measurement or a
    result of the run concerns the stated operation, is not checked. Raises
    what :func:`read` raises, so no op_signature is returned, and none is
    inferred, for a missing, unreadable or invalid file or one of another
    version.
    """
    return read(data_root, run_id).op_signature


def round_budget_of(data_root, run_id):
    """Return the round budget the run ``run_id`` states, or ``None`` when it states none.

    It is the ``round_budget`` of what :func:`read` returns (ADR-0032
    decision 5): the ``int`` of the member ``round_budget`` of
    ``runs/<run_id>/instance.json``, from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`, as the file states it at this call, or
    ``None`` for a valid file without that member. The member states the
    budget of loop iterations the instance was started with, as a number of
    rounds (ADR-0032 decision 2). ``None`` says that no round budget is
    stated: it is not "unlimited", not a default and not zero, and no value
    stands in for it (ADR-0032 decision 4), no number, no infinity, no
    constant of this module, nothing taken from another member or from
    another file of the run and not the round budget of another run. Only
    the instance file is read, and the number is compared with nothing: not
    with the ``round`` of a ``STATE.json`` beside it, with the spend view or
    with another member, so nothing is reported or refused because a run is
    at or beyond the number, and what counts against the budget is not said
    here. Raises what :func:`read` raises, so no round budget is returned,
    and none is inferred, for a missing, unreadable or invalid file or one
    of another version.
    """
    return read(data_root, run_id).round_budget


def wall_clock_budget_s_of(data_root, run_id):
    """Return the wall-clock budget the run ``run_id`` states, in seconds, or ``None``.

    It is the ``wall_clock_budget_s`` of what :func:`read` returns (ADR-0033
    decision 5): the ``int`` of the member ``wall_clock_budget_s`` of
    ``runs/<run_id>/instance.json``, from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`, as the file states it at this call, or
    ``None`` for a valid file without that member. The member states the
    budget of wall-clock time the instance was started with, as a number of
    seconds (ADR-0033 decisions 2 and 3), and the number is returned as it
    is, converted to no other unit. ``None`` says that no wall-clock budget
    is stated: it is not "unlimited", not a default and not zero, and no
    value stands in for it (ADR-0033 decision 4), no number, no infinity, no
    constant of this module, nothing taken from ``round_budget``, from
    another member or from another file of the run and not the wall-clock
    budget of another run. Only the instance file is read and no clock is:
    the number is compared with nothing, not with a time that has passed,
    with the ``time`` of a line of a log beside it, with the ``round`` of a
    ``STATE.json`` beside it, with the spend view or with another member, so
    nothing is reported or refused because of any such time, and from which
    moment the time runs and what counts against the budget is not said
    here. Raises what :func:`read` raises, so no wall-clock budget is
    returned, and none is inferred, for a missing, unreadable or invalid
    file or one of another version.
    """
    return read(data_root, run_id).wall_clock_budget_s


def owner_of(data_root, run_id):
    """Return the owner the run ``run_id`` states, a name, or ``None`` when it states none.

    It is the ``owner`` of what :func:`read` returns (ADR-0034 decision 5):
    the string of the member ``owner`` of ``runs/<run_id>/instance.json``, 1
    to 255 printable ASCII characters, as the file states it at this call,
    unchanged, or ``None`` for a valid file without that member. The member
    states the owner the instance was started with, as a name, and no more
    (ADR-0034 decision 2): the name is no identity, nothing checks it against
    one, and no right follows from it. ``None`` says that the file states no
    owner, not that the run has none: it is no default and no anonymous or
    shared value, and nothing stands in for it (ADR-0034 decision 4), not the
    user name of a process, not an author or a committer, not a GitHub
    account, not the name of a directory or of a repository, not a part of
    the ``run_id``, not the member ``project``, not the owner of another run
    and no constant of this module. Only the instance file is read, and the
    name is compared with nothing: no run is looked up, grouped, allowed or
    refused by it. Raises what :func:`read` raises, so no owner is returned,
    and none is inferred, for a missing, unreadable or invalid file or one of
    another version.
    """
    return read(data_root, run_id).owner


def project_of(data_root, run_id):
    """Return the project the run ``run_id`` states, a name, or ``None`` when it states none.

    It is the ``project`` of what :func:`read` returns (ADR-0034 decision 5):
    the string of the member ``project`` of ``runs/<run_id>/instance.json``,
    1 to 255 printable ASCII characters, as the file states it at this call,
    unchanged, or ``None`` for a valid file without that member. The member
    states the project the instance was started with, as a name, and no more
    (ADR-0034 decision 2): the name says nothing about the run itself, and no
    right follows from it. ``None`` says that the file states no project, not
    that the run belongs to none: it is no default and no shared value, and
    nothing stands in for it (ADR-0034 decision 4), not the name of a
    directory or of a repository, not a part of the ``run_id``, not the
    member ``owner``, not the project of another run and no constant of this
    module. Only the instance file is read, and the name is compared with
    nothing: no run is looked up, grouped, allowed or refused by it, and two
    runs that state equal names are not thereby related. Raises what
    :func:`read` raises, so no project is returned, and none is inferred, for
    a missing, unreadable or invalid file or one of another version.
    """
    return read(data_root, run_id).project


def draws_of(data_root, run_id):
    """Return the number of draws the run ``run_id`` states, or ``None`` when it states none.

    It is the ``draws`` of what :func:`read` returns: the ``int`` of the
    member ``draws`` of ``runs/<run_id>/instance.json``, from 1 to
    :data:`hilclaw.keys.MAX_INTEGER`, as the file states it at this call,
    unchanged, or ``None`` for a valid file without that member (ADR-0046
    decision 3). The member states the number of draws of a check of
    ``correctness.check`` about an attempt of the run, for a run of the
    first case and for one whose hw_profile names the mock; that the run is
    one of them is not checked here, and the record gives the member no
    meaning for any other run (ADR-0046 decisions 1 and 3). ``None`` says
    that no number is stated: there is no default, and no value stands in
    for it (ADR-0046 decision 3), not 1, no constant of this module or of
    the harness, nothing taken from another member and not the number of
    another run. Only the instance file is read, and the number is compared
    with nothing: a returned number is not thereby one a check can be
    carried out with, and nothing here hands it to a check. What a call of
    the tool answers for a valid file without the member is ADR-0046
    decision 5 and is not done here: this function raises no tool failure.
    Raises what :func:`read` raises, so no number is returned, and none is
    inferred, for a missing, unreadable or invalid file or one of another
    version.
    """
    return read(data_root, run_id).draws


def objective_of(data_root, run_id):
    """Return the objectives and the constraints the run ``run_id`` states, or ``None``.

    It is the ``objective`` of what :func:`read` returns (ADR-0053 decision
    7): the ``dict`` of the member ``objective`` of
    ``runs/<run_id>/instance.json`` as the file states it at this call, new
    at each call, with ``objectives`` and ``constraints`` - today a ``list``
    of the one entry ``{"type": "latency_minimisation"}`` and an empty
    ``list``, the one value ADR-0053 decision 4 gives -, or ``None`` for a
    valid file without that member. The member states the target the
    instance was started with and no more (ADR-0053 decision 3): nothing
    here says that anything was measured, compared or judged. ``None`` says
    that the file states no objective and no set of constraints: it is no
    default and not "no constraint", which a present member with an empty
    ``constraints`` states and nothing else does, and nothing stands in for
    it (ADR-0053 decision 5), not ``latency_minimisation``, no constant of
    this module, not the ``task.objective`` of a spec of the run, nothing
    taken from another member and not the objective of another run. Only the
    instance file is read, no spec is, and the result is compared with
    nothing. Raises what :func:`read` raises, so no objective and no
    constraint is returned, and none is inferred, for a missing, unreadable
    or invalid file or one of another version (ADR-0053 decision 5). It
    raises no tool failure: for the run tools, what a call answers when no
    objective is stated or the stated one is not covered is ADR-0061
    decision 4; for any other tool it is not said (ADR-0053 decision 7).
    """
    return read(data_root, run_id).objective


def coder_model_of(data_root, run_id):
    """Return the coder model the run ``run_id`` states, a full name, or ``None``.

    It is the ``coder_model`` of what :func:`read` returns: the string of the
    member ``coder_model`` of ``runs/<run_id>/instance.json``, a full Claude
    model name of at most 64 characters (ADR-0136 decision 3), as the file
    states it at this call, unchanged, or ``None`` for a valid file without
    that member. The member states the model the coder calls of the run
    request, not the one that ran (ADR-0136 decisions 3 and 7). ``None`` says
    that the file states no coder model: no value stands in for it (ADR-0136
    decision 4), not the default the start applies, not an alias, no
    constant of this module, nothing taken from another member and not the
    model of another run. Only the instance file is read; that a model of
    that name is offered is not checked, and the name is resolved, compared
    and handed to nothing. Raises what :func:`read` raises, so no model is
    returned, and none is inferred, for a missing, unreadable or invalid
    file or one of another version. It raises no tool failure and gives
    "not stated" no kind: the read of the member at a coder call is ADR-0136
    decision 5 and is not done here.
    """
    return read(data_root, run_id).coder_model


def layout_version_of(data_root, run_id):
    """Return the layout version the run ``run_id`` states (ADR-0024 decisions 3 to 5).

    ``runs/<run_id>/instance.json`` is read through :func:`read`, as a whole
    and at each call, and must be valid. No member holds the layout version:
    a valid file of schema version 1 states layout version 1 through its
    ``schema_version`` (decision 3), and that number, the ``int`` 1, is
    returned, from the pairing this module holds per schema version. Nothing
    stands in (decision 4): the result does not depend on
    :data:`hilclaw.layout.LAYOUT_VERSION`, the layout that module builds,
    which is not read here, nor on another run, nor on a member such as
    ``layout_version``, which is passed over and is no stamp. The result is
    compared with nothing and no run is refused for it; that the tree of the
    run has that layout is not checked. Raises what :func:`read` raises, so
    no layout version is returned, and none is inferred, for a missing or
    unreadable file, for an invalid file, though it may hold
    ``"schema_version": 1``, or for one of another version.
    """
    read(data_root, run_id)
    return _STATED_LAYOUT[SCHEMA_VERSION]


def _fail(place, rule, value):
    got = type(value).__name__
    if type(value) is str:
        got = f"{got} {reprlib.repr(value)}"
    raise InvalidInstanceError(f"{place}: must be {rule}, got {got}")


def _checked(document):
    if type(document) is not dict:
        _fail("document", "an object", document)
    if "schema_version" not in document:
        raise InvalidInstanceError("document: lacks the member schema_version")
    version = document["schema_version"]
    if type(version) is not int or not 0 <= version <= _MAX:
        _fail("schema_version", f"an int from 0 to {_MAX}", version)
    if version != SCHEMA_VERSION:
        raise UnsupportedVersionError(f"schema_version: {version} is not supported")
    if "hw_profile" not in document:
        raise InvalidInstanceError("document: lacks the member hw_profile")
    key, record = _keyed("hw_profile", document["hw_profile"], keys.hw_profile_key)
    tolerance = _tolerance(document["tolerance"]) if "tolerance" in document else None
    commit = None
    if "source_commit" in document:
        commit = _source_commit(document["source_commit"])
    n_max = _n_max(document["n_max"]) if "n_max" in document else None
    candidates = None
    if "candidates_per_round" in document:
        candidates = _candidates_per_round(document["candidates_per_round"])
    op = None
    if "op_signature" in document:
        section = document["op_signature"]
        op = OpSignature(*_keyed("op_signature", section, keys.op_signature_key))
    budget = None
    if "round_budget" in document:
        budget = _round_budget(document["round_budget"])
    seconds = None
    if "wall_clock_budget_s" in document:
        seconds = _wall_clock_budget_s(document["wall_clock_budget_s"])
    owner = project = None
    if "owner" in document:
        owner = _string("owner", document["owner"])
    if "project" in document:
        project = _string("project", document["project"])
    draws = _draws(document["draws"]) if "draws" in document else None
    objective = None
    if "objective" in document:
        objective = _objective(document["objective"])
    model = None
    if "coder_model" in document:
        model = _coder_model(document["coder_model"])
    others = {name: value for name, value in document.items() if name not in _DEFINED}
    return Instance(
        key,
        record,
        tolerance,
        commit,
        n_max,
        candidates,
        op,
        budget,
        seconds,
        owner,
        project,
        draws,
        objective,
        model,
        others,
    )


def _keyed(place, section, derive):
    if type(section) is not dict:
        _fail(place, "an object", section)
    for name in section:
        if name not in _SECTION:
            _fail(place, "an object without the member", name)
    for name in _SECTION:
        if name not in section:
            raise InvalidInstanceError(f"{place}: lacks the member {name}")
    key, record = section["key"], section["record"]
    if type(key) is not str:
        _fail(f"{place}.key", "a str", key)
    if type(record) is not dict:
        _fail(f"{place}.record", "an object", record)
    try:
        name = derive(record).name
    except keys.InvalidRecordError as error:
        raise InvalidInstanceError(f"{place}.record.{error}") from None
    if key != name:
        _fail(f"{place}.key", f"{name}, the name derived from {place}.record", key)
    return key, record


def _tolerance(section):
    if type(section) is not dict:
        _fail("tolerance", "an object", section)
    for name in section:
        if name not in _TOLERANCE:
            _fail("tolerance", "an object without the member", name)
    for name in _TOLERANCE:
        if name not in section:
            raise InvalidInstanceError(f"tolerance: lacks the member {name}")
    return Tolerance(*(_number(name, section[name]) for name in _TOLERANCE))


def _number(name, value):
    try:
        number = float(value) if type(value) in (int, float) else math.nan
    except OverflowError:
        number = math.inf
    if not 0 <= number < math.inf:
        _fail(f"tolerance.{name}", "a finite number that is not negative", value)
    return abs(number)


def _source_commit(value):
    if (
        type(value) is not str
        or len(value) not in _COMMIT_LENGTHS
        or not _COMMIT_CHARACTERS.issuperset(value)
    ):
        rule = "a str of 40 or of 64 characters, each one of 0-9 and a-f"
        _fail("source_commit", rule, value)
    return value


def _n_max(value):
    if type(value) is not int or not 5 <= value <= _MAX:
        _fail("n_max", f"an int from 5 to {_MAX}", value)
    return value


def _candidates_per_round(value):
    if type(value) is not int or not 1 <= value <= _MAX:
        _fail("candidates_per_round", f"an int from 1 to {_MAX}", value)
    return value


def _round_budget(value):
    if type(value) is not int or not 1 <= value <= _MAX:
        _fail("round_budget", f"an int from 1 to {_MAX}", value)
    return value


def _wall_clock_budget_s(value):
    if type(value) is not int or not 1 <= value <= _MAX:
        _fail("wall_clock_budget_s", f"an int from 1 to {_MAX}", value)
    return value


def _draws(value):
    if type(value) is not int or not 1 <= value <= _MAX:
        _fail("draws", f"an int from 1 to {_MAX}", value)
    return value


def _objective(section):
    _closed("objective", section, _OBJECTIVE)
    objectives, constraints = section["objectives"], section["constraints"]
    if type(objectives) is not list or len(objectives) != 1:
        _fail("objective.objectives", "an array of exactly one entry", objectives)
    entry = objectives[0]
    _closed("objective.objectives[0]", entry, _OBJECTIVE_ENTRY)
    kind = entry["type"]
    if type(kind) is not str or kind not in _OBJECTIVE_TYPES:
        _fail("objective.objectives[0].type", " or ".join(_OBJECTIVE_TYPES), kind)
    if type(constraints) is not list or constraints:
        rule = "an empty array, as no constraint type is admitted"
        _fail("objective.constraints", rule, constraints)
    return section


def _closed(place, section, names):
    if type(section) is not dict:
        _fail(place, "an object", section)
    for name in section:
        if name not in names:
            _fail(place, "an object without the member", name)
    for name in names:
        if name not in section:
            raise InvalidInstanceError(f"{place}: lacks the member {name}")


def _string(place, value):
    if (
        type(value) is not str
        or not 1 <= len(value) <= 255
        or not all(" " <= character <= "~" for character in value)
    ):
        _fail(place, "a str of 1 to 255 printable ASCII characters", value)
    return value


def _coder_model(value):
    if (
        type(value) is not str
        or not 8 <= len(value) <= 64
        or not value.startswith("claude-")
        or value.endswith("-")
        or not all("a" <= c <= "z" or "0" <= c <= "9" or c == "-" for c in value)
    ):
        rule = (
            'a str of at most 64 characters, "claude-" followed by lowercase ASCII'
            ' letters, digits and "-", not ending with "-"'
        )
        _fail("coder_model", rule, value)
    return value


def _object(pairs):
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("a JSON object repeats a member name")
    return members


def _nan(name):
    raise ValueError(f"{name} is not a JSON value")
