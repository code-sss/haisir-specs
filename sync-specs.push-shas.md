## Last Push SHAs

Record the spec-side HEAD SHA when `./sync-specs.sh push {source}` was last run.
Used by the `sync-spec` skill as the merge base when pulling changes back.

| Container | SHA | Pushed |
|---|---|---|
| backend  | — | — |
| frontend | — | — |

> Update this file immediately after every `./sync-specs.sh push` run.
> To update: replace the SHA and date for the relevant container row.
> The `sync-spec` skill reads this file to distinguish spec-ahead content from
> container-completed content during a pull merge.
