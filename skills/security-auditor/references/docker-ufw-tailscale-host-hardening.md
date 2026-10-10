# Docker, UFW, Tailscale, and cloud-host hardening

Use this for a read-only review of a cloud VM running Docker plus a private overlay such as Tailscale.

## Core rule

Never infer reachability from either `0.0.0.0` or `ufw deny incoming` alone. Docker-published IPv4 traffic is commonly DNATed in `nat/PREROUTING` and accepted through `FORWARD`/Docker chains before UFW's ordinary routed policy. Trace the actual rule order and check any upstream cloud firewall.

## Read-only evidence pass

1. Inventory interfaces and classify loopback, public, private, Docker, and overlay addresses. A Tailscale `100.64.0.0/10` address is CGNAT overlay space, not the provider public IP.
2. Capture listeners and owners with `ss -lntup`; map each published port with `docker ps` and `docker inspect`.
3. Inspect UFW, `iptables-save`, nftables, `DOCKER-USER`, Docker DNAT/ACCEPT rules, IPv6 separately, and Docker daemon iptables settings.
4. For each port, state: bind scope, DNAT target, chain path, explicit drop/accept, upstream-firewall unknown, and confidence. Use “probably reachable” until a benign external TCP connect from an independent vantage confirms it.
5. Inspect container user, privilege flag, capabilities, security options, mounts, rootfs writability, restart policy, health check, image digest/tag, and network.
6. Identify the service's exact config/Compose source and all consumers before recommending rebinding or disabling it. Environment variable names may be listed; values must not be printed.
7. Audit effective SSH settings with `sshd -T`, firewall scope, keys/permissions, recent auth events, Tailscale SSH state, and console recovery. Do not install fail2ban by reflex; first verify whether it already exists and whether SSH is public.
8. Check patch backlog, reboot marker, installed versus running kernel, automatic updates, sensitive file modes, Docker socket access, root-run services, agent/API listeners, and approval boundaries.

## Preferred remediation hierarchy

1. Preserve availability: verify cloud console, a second private-overlay SSH session, backups, exact configs, image digests, named volumes, and rollback.
2. Bind host-only services to `127.0.0.1`. If containers consume them, use a private user-defined Docker network without host publication.
3. Use a Tailscale-IP bind only for a verified remote workflow and reviewed ACLs. It adds startup/address dependency.
4. Treat all-address publication plus `DOCKER-USER` rules as a brittle fallback. Rule order and persistence must be explicitly managed and retested after Docker/firewall updates.
5. Change one layer per maintenance window: public port closure, then app rebinding, then permission/approval policy, then patch/reboot, then SSH/container defense-in-depth.

For Compose-managed services, edit only the port mapping and use `docker compose config --quiet` plus `docker compose up -d`; do not manually stop/remove a live stateful service. Preserve project names, env files, named volumes, and database publishing. Validate health, real consumers, local access, external denial, and rollback before continuing.

For standalone containers, first capture inspect/image metadata, pin the current digest, create durable Compose, add a health check/restart policy where appropriate, then migrate the bind. Never prune the original image or volumes before rollback verification.

## Agent and automation blast radius

A root-run agent gateway or automation runner with approvals disabled turns compromise of any authorised chat or session into full-host compromise. Do not blindly enable manual approval for scheduled jobs, because it may break unattended work. Inventory jobs, separate interactive and scheduled policy, keep platform allowlists and secret redaction on, and evaluate a dedicated non-root service account with narrowly scoped privilege as a separate project.

## Fail-closed staged execution

For approved live changes, treat the verification harness as part of the safety boundary:

1. Create the rollback artifact before mutation and validate its syntax plus immutable image/config references without executing it.
2. Preflight the change script and every verifier (`bash -n`, Compose parser, structured assertions) before the first firewall/container mutation. Prefer Python/JSON assertions over long shell `[` expressions; a malformed assertion can trigger a fail-closed rollback even when the service itself is healthy.
3. Separate preflight, mutation, and post-change verification. After mutation, verify bind scope, runtime UID, health/HTTP baseline, logs, restart policy, image identity, and unrelated container/volume IDs.
4. If any required check returns nonzero, including a verifier defect, run the prepared rollback immediately, verify the restored service, and stop later mutation stages. Do not reinterpret a harness failure as success after the fact.
5. After rollback, remove only orphaned artifacts created by the failed attempt (for example, an unattached Compose network). Retain temporary firewall protection whenever rollback restores broad publication.
6. Use a fresh, OS-safe temporary verifier (`tempfile`/`mktemp`, a `verify-` prefix), run it, and clean it with a guaranteed exit handler. Describe this as **ad-hoc changed-file verification**, not “suite green,” when no canonical test suite applies.

Backup scripts must also fail safely. Set `umask 077` first, create the timestamp directory as `0700`, write or immediately chmod each sensitive artifact to `0600`, and install an EXIT/ERR guard that secures partial artifacts if a later capture command fails. A failed first capture is not the canonical rollback source; label it incomplete rather than silently treating it as valid.

Status commands can themselves leak masked credential fragments, messaging/account IDs, destinations, or full live command lines. Prefer narrow structured queries such as `systemctl show` over `systemctl status`; sanitize agent, platform and cron output before persistence; and scan both the final report and stored status artifacts for credential/account patterns. Root-only permissions are necessary but do not substitute for sanitization.

## Non-breaking permission hardening

For secret-bearing config, local state databases, auth exports, and historical environment backups under root-owned trees, mode `0600` is usually safe defense-in-depth. Apply it only to existing regular files with explicit path or `-type f` guards. Record owner, group, size, and SHA-256 immediately before and after `chmod` to prove the operation changed metadata rather than content. Never chmod sockets or directories accidentally, and recheck every dependent service afterward.

## Availability and reporting

- No network, SSH, Docker, package, or service mutation during the audit phase.
- Rank confirmed exposure, probable rule-path exposure, defense-in-depth, false positive, and unknown separately.
- Do not combine firewall, bind, SSH, approval, and reboot changes.
- Report exact rollback and lockout avoidance for every proposed stage.
- Distinguish active controls, staged-but-inactive configuration, restored original state, skipped stages, and externally unverified reachability. Never call a service closed merely because a host bind or one interface-specific rule changed.
