# Project rules

## No pushes

**Never run `git push` (any form — branch, tag, `--force`, `--set-upstream`, etc.) in this repo.**
Commit locally as needed, on any branch. Never push to `origin` or any remote.
If a task seems to need a push, stop and ask the user instead of running it.

Note: `origin` push is already disabled at the git-remote level (`origin DISABLED (push)`
in `git remote -v`) as a second layer — this file is the instruction-level rule, not a
substitute for checking.
