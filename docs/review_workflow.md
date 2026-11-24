# Review integrity

Review state binds to input SHA256s, complete mapping configuration, policy and run ID.
Each action has a revision, reviewer, timezone-aware timestamp, endpoints and optional
reason; reassignment requires explicit confirmation and a reason. Replaying validated
active events overlays immutable automatic associations. One physical extractor cannot
be owned twice. Cross-paper transactions, invalid/suppressed items and fingerprint
mismatches are rejected. Rejected edges remain in the candidate inventory.

Undo appends history and targets a specified active earlier action. Later dependent
transactions must remain valid; otherwise undo is rejected. Undo dependent actions
first. An undo event cannot itself be an undo target; corrections can be re-entered as
new events. Confirming the same selected link can explicitly adjudicate a prior automatic
identity conflict. Marking an accepted gold missing requires confirmation of its removal.

Local autosave uses an exclusive lock, expected revision, a previous-state backup,
write/fsync/temp + atomic replace. Download/import carries a checksum for corruption
protection. It is not a cryptographic identity signature or permission system. This is
a local single-user baseline; shared authenticated concurrency needs a separate design.
