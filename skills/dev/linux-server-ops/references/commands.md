# Commands

Copy-paste commands for each step in `SKILL.md`. Tested on Ubuntu 22.04/24.04 and Debian 12. Run as root or with `sudo`. Commands marked **MUTATES** change the system: only run them in the fix or prevent step, after measuring.

## Inventory (read-only)

```bash
date -Is
hostnamectl 2>/dev/null | grep -E 'Operating System|Kernel'
uptime

# Disks: bytes, human, inodes
df -B1 -x tmpfs -x devtmpfs
df -hT -x tmpfs -x devtmpfs
df -i -x tmpfs -x devtmpfs
lsblk -o NAME,FSTYPE,SIZE,FSAVAIL,FSUSE%,MOUNTPOINTS

# Memory and swap
free -h
swapon --show
vmstat 1 5

# Top processes
ps -eo pid,ppid,user,%mem,rss,%cpu,etime,cmd --sort=-rss | head -15
ps -eo pid,ppid,user,%cpu,%mem,etime,cmd --sort=-%cpu | head -15

# Services
systemctl --failed --no-pager

# Journald and Docker (if present)
journalctl --disk-usage
command -v docker >/dev/null && docker system df && docker ps -a --size --format 'table {{.Names}}\t{{.Status}}\t{{.Size}}'
```

## Diagnose: disk

```bash
# Biggest directories, one filesystem only, largest last
du -x -h -d1 / 2>/dev/null | sort -h | tail -20
du -x -h -d1 /var 2>/dev/null | sort -h | tail -20

# Regular files directly under / (swap files hide here)
find / -maxdepth 1 -xdev -type f -printf '%s\t%p\n' | sort -n | tail

# Largest files over 100 MB on the root filesystem, with modified time
find / -xdev -type f -size +100M -printf '%s\t%TY-%Tm-%Td\t%p\n' 2>/dev/null | sort -n | tail -30

# Deleted files still held open (df vs du gap)
lsof -nP +L1 2>/dev/null | awk 'NR==1 || $7 > 10485760'

# ext4 reserved blocks (explains "full" at 95%)
tune2fs -l "$(findmnt -no SOURCE /)" 2>/dev/null | grep -E 'Block count|Reserved block count|Block size'
```

Growth rate of a suspect file:

```bash
f=/var/log/example.log
a=$(stat -c %s "$f"); sleep 30; b=$(stat -c %s "$f")
echo "growth: $(( (b - a) / 30 )) bytes/sec"
```

Inode exhaustion, find the directory with the most files:

```bash
for d in /var /tmp /home /srv /opt; do printf '%s\t%s\n' "$(find "$d" -xdev 2>/dev/null | wc -l)" "$d"; done | sort -n
# then drill down
find /var -xdev -type f 2>/dev/null | cut -d/ -f2-4 | sort | uniq -c | sort -n | tail
```

Specific suspects:

```bash
du -sh /var/log/* 2>/dev/null | sort -h | tail
du -sh /var/cache/apt /var/crash /var/lib/systemd/coredump /tmp /var/tmp 2>/dev/null
dpkg -l 'linux-image-*' | awk '/^ii/{print $2}'; uname -r
coredumpctl list --no-pager 2>/dev/null | tail
grep -rIl 'No space left on device' /var/log 2>/dev/null | head
journalctl --since '-24h' --no-pager | grep -i 'no space left' | tail
```

## Diagnose: Docker

```bash
docker system df -v
# Container log sizes (json-file driver)
for c in $(docker ps -aq); do
  p=$(docker inspect -f '{{.LogPath}}' "$c"); n=$(docker inspect -f '{{.Name}}' "$c")
  [ -f "$p" ] && printf '%s\t%s\n' "$(du -h "$p" | cut -f1)" "$n"
done | sort -h
# Log driver and limits per container
docker inspect -f '{{.Name}} {{.HostConfig.LogConfig.Type}} {{json .HostConfig.LogConfig.Config}}' $(docker ps -q)
docker volume ls -f dangling=true
```

A dangling volume is not proof of garbage. It may be a database whose container was removed. Inspect it (`docker volume inspect`, look at the mountpoint) before suggesting anything.

## Diagnose: memory and processes

```bash
dmesg -T | grep -iE 'out of memory|oom-kill|killed process' | tail
journalctl -k --since '-24h' --no-pager | grep -i oom | tail
# Is a process growing? Sample RSS a minute apart
pid=1234; ps -o rss= -p $pid; sleep 60; ps -o rss= -p $pid
# Which service owns a PID
systemctl status 1234 --no-pager | head -5
cat /proc/1234/cgroup
```

## Fix (MUTATES, measure before and after each)

```bash
df -B1 / > /root/df-before.txt     # or anywhere off the full disk

truncate -s 0 /var/log/example.log            # runaway log, keep the inode
systemctl restart SERVICE                      # release deleted-open files (ask first on prod)
apt-get clean
journalctl --vacuum-size=500M
find /var/log -type f \( -name '*.gz' -o -name '*.[0-9]' \) -mtime +14 -print   # review, then add -delete
apt-get autoremove --purge                     # old kernels; check uname -r is kept
coredumpctl list && rm -f /var/lib/systemd/coredump/*   # after noting the crash

# Docker, safest first
truncate -s 0 "$(docker inspect -f '{{.LogPath}}' CONTAINER)"
docker image prune -f                 # dangling images only
docker builder prune -f               # build cache
docker container prune -f             # stopped containers, review the list first
# ASK FIRST: docker image prune -a    (removes every image not used by a container)
# NEVER without named approval: docker volume rm / docker system prune --volumes

# /tmp older than 7 days, not open: review first
find /tmp /var/tmp -xdev -type f -mtime +7 -print | head -50

df -B1 /
```

Add swap when there is none (MUTATES):

```bash
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Cap a leaking service (MUTATES):

```bash
systemctl edit SERVICE
# [Service]
# MemoryMax=1G
# Restart=on-failure
systemctl daemon-reload && systemctl restart SERVICE
```

## Prevent

logrotate, `/etc/logrotate.d/myapp`:

```
/var/log/myapp/*.log {
    daily
    size 100M
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

Test: `logrotate -d /etc/logrotate.d/myapp`

journald, `/etc/systemd/journald.conf.d/size.conf`:

```ini
[Journal]
SystemMaxUse=500M
SystemKeepFree=2G
MaxRetentionSec=14day
```

Apply: `systemctl restart systemd-journald && journalctl --disk-usage`

Docker defaults, `/etc/docker/daemon.json` (merge with any existing keys, back up first):

```json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "50m", "max-file": "3" }
}
```

Validate: `dockerd --validate --config-file=/etc/docker/daemon.json`. Restarting Docker restarts containers unless `live-restore` is on, so schedule it. New limits apply only to containers created afterwards. In Compose, set it per service:

```yaml
logging:
  driver: json-file
  options: { max-size: "50m", max-file: "3" }
```

Weekly bounded Docker cleanup, `/etc/cron.weekly/docker-builder-prune` (chmod +x):

```bash
#!/bin/sh
docker builder prune -f --filter until=168h >/dev/null 2>&1
docker image prune -f >/dev/null 2>&1
```

Core dump cap, `/etc/systemd/coredump.conf.d/size.conf`:

```ini
[Coredump]
MaxUse=1G
```

Disk alert, silent when healthy, `/usr/local/bin/disk-alert` (chmod +x), run from cron every 15 minutes. Prints only when a threshold is crossed, so cron mail or a wrapper that forwards non-empty output becomes the alert. Cooldown prevents spam.

```bash
#!/bin/sh
PCT_MAX=85; INODE_MAX=85; FREE_MIN_MB=2048; COOLDOWN=21600
STATE=/var/tmp/disk-alert.last
now=$(date +%s); last=$(cat "$STATE" 2>/dev/null || echo 0)
msg=""
df -P -x tmpfs -x devtmpfs | awk 'NR>1{print $6, $4, $5}' | while read m avail pct; do
  p=${pct%\%}; ip=$(df -Pi "$m" | awk 'NR==2{print $5}' | tr -d %)
  [ "$p" -ge $PCT_MAX ] || [ $((avail/1024)) -lt $FREE_MIN_MB ] || [ "${ip:-0}" -ge $INODE_MAX ] && \
    echo "DISK $m: ${p}% used, $((avail/1024)) MB free, inodes ${ip}%"
done > /var/tmp/disk-alert.out
if [ -s /var/tmp/disk-alert.out ] && [ $((now - last)) -ge $COOLDOWN ]; then
  cat /var/tmp/disk-alert.out; echo "$now" > "$STATE"
fi
```

Cron entry: `*/15 * * * * root /usr/local/bin/disk-alert`. Test the quiet path by running it (no output expected), and the alert path by temporarily setting `PCT_MAX=1`.

## Lock-out safety (before any SSH or firewall change)

```bash
sshd -t                                   # config test, must print nothing
ufw show added; ufw --dry-run enable      # preview UFW
nft -c -f /etc/nftables.conf              # check nftables syntax
# Keep this session open. Test from a NEW terminal before closing it.
# Have the provider console or a second SSH route ready first.
```

## Other distros

| Task | Ubuntu/Debian | RHEL/Rocky/Alma/Fedora | Alpine | Arch |
|---|---|---|---|---|
| Package cache | `apt-get clean` | `dnf clean packages` | `apk cache clean` | `paccache -rk2` |
| Old kernels | `apt-get autoremove --purge` | `dnf remove --oldinstallonly` (keeps `installonly_limit`) | n/a | `pacman` keeps one |
| Installed kernels | `dpkg -l 'linux-image-*'` | `rpm -q kernel` | `apk info linux-*` | `pacman -Q linux` |
| Firewall | `ufw` | `firewalld` (`firewall-cmd`) | `iptables`/`nft` | `nft` |
| Journald | yes | yes | usually not (OpenRC, syslog) | yes |
| Crash files | `/var/crash` (apport) | `/var/spool/abrt` | n/a | systemd-coredump |

On Alpine without systemd, use `rc-service` instead of `systemctl` and check `/var/log/messages`.
