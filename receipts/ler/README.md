# Post-merge LER replication receipts

One file per entry with a measured rate, written by
`verify/ler_replicate.py` from the weekly `ler-weekly` workflow (issue #1278).
Each records, per basis and physical rate, whether the point replicated
(verified), disagreed (failed), or could not be checked within the budget
(unverifiable), bound to the claim through a digest of the ler block, the
round count, and the committed circuits; a claim edited after its receipt
reads as pending until the next run. The site reads these files; the
verifier never does, and nothing here changes whether an entry passes.
