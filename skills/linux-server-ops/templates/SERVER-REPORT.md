# Server report: <server label>

Date: <YYYY-MM-DD HH:MM timezone>
OS / kernel: <e.g. Ubuntu 24.04, 6.8.0-xx>
Requested by: <role, not a name if this will be shared>
Mode: <read-only audit | audit + approved fixes>

## Summary

- **Problem:** <one line, e.g. root disk 100% full, Docker JSON log for one container grew 18 GB with no rotation>
- **Done:** <one line, e.g. truncated the log, cleared apt cache and build cache, added Docker log limits>
- **Now:** <one line, e.g. 41% used, 22 GB free, inodes 9%, all services healthy>

## Before and after

| Measure | Before (<time>) | After (<time>) | Change |
|---|---|---|---|
| / used (bytes) | | | |
| / available (bytes) | | | |
| / Use% | | | |
| / inodes used % | | | |
| Other mounts | | | |
| Memory available | | | |
| Swap used | | | |
| Load (1/5/15) | | | |
| Failed units | | | |

Used-space reduction and available-space gain can differ on ext4 (reserved blocks). Per-step sizes below may not add up to the net change because other processes kept writing.

## Root cause

<What was growing, how fast (measured), since when, and why it was not bounded. Note whether it was the cause or a symptom of something else.>

Evidence:
- <command and key output line>
- <command and key output line>

## Actions taken

| # | Action | Command | Freed (measured) | Reversible? | Approved by owner? |
|---|---|---|---|---|---|
| 1 | | | | | n/a (safe) / yes |

## Kept on purpose

| Path or item | Size | Why kept |
|---|---|---|
| | | database / volume / backup / unknown owner / in use |

## Prevention added

| Change | File | Validated with | Result |
|---|---|---|---|
| | | `logrotate -d` / `dockerd --validate` / `sshd -t` | pass |

## Waiting on the owner

- [ ] <decision, with measured size and what is lost, e.g. "Remove 6 unused images (9.2 GB). Lost: fast rollback to older app versions.">
- [ ] <capacity decision if still tight: bigger disk, move data, retire a workload>

## Verification

- [ ] `df`, `df -i`, `free -h` rerun after the last change
- [ ] `systemctl --failed` empty or unchanged
- [ ] Containers healthy, IDs unchanged unless recreated on purpose
- [ ] No "No space left on device" since <time>
- [ ] Growth source measured again and stable
- [ ] Alert silent when healthy, fires on forced test

## Notes

<Anything odd, anything not checked, anything that was point-in-time.>
