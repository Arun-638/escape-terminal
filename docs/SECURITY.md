# 🔒 ESCAPE THE TERMINAL — Security Architecture & Hardening Report

**Defense-in-Depth Implementation for Multi-Tenant College LAN Competition**

---

## 1. Threat Model & Mitigation Matrix

| Threat Vector | Risk Level | Mitigation Strategy | Implemented Mechanism |
| :--- | :--- | :--- | :--- |
| **Container Breakout to Host** | Critical | Least privilege, dropped capabilities | Non-root UID 1001, `no-new-privileges: true`, `cap_drop: ALL` |
| **Cross-Team Network Reconnaissance** | High | Network separation | Containers spawned with `network_mode: none` |
| **Host Resource Exhaustion / Fork Bomb** | High | Hard resource quotas | `--pids-limit=100`, `mem_limit=256m`, `cpu_quota=50000` |
| **Privilege Escalation via SUID Binaries** | Medium | SUID/SGID audit & stripping | Build-time removal of SUID bits on all system executables |
| **Automated Flag Brute-Forcing** | Medium | Request throttling | Sliding-window rate limiter (15 req/min per team, HTTP 429) |
| **IDOR / Session Tampering** | High | Server-side identity binding | Strict session cookie validation; client `team_id` override blocked |
| **Answer Sharing Across Teams** | High | Dynamic challenge generation | HMAC-SHA256 team-seeded unique flag and path distribution |

---

## 2. Hardening Controls Detail

### 2.1 Non-Root User & SUID Stripping
- Standard Docker containers default to `root` (UID 0).
- In **Escape The Terminal**, player processes strictly execute under:
  ```dockerfile
  # Dockerfile
  RUN groupadd -g 1001 player && \
      useradd -u 1001 -g player -m -d /home/player -s /bin/bash player
  USER player
  ```
- All unnecessary SUID/SGID bits are stripped during container image creation:
  ```bash
  find / -xdev -perm /6000 -type f -exec chmod a-s {} \;
  ```
- Any attempt to use `sudo`, `su`, or `chroot` immediately fails with permission denied.

### 2.2 Complete Network Isolation
- Sandboxes contain no sensitive network interfaces.
- Provisioned with Docker `network_mode="none"`.
- Sandboxes cannot reach:
  - The host server (`localhost` / `172.17.0.1`)
  - CTFd or the terminal service (`80`, `8000`, `8080`)
  - The PostgreSQL database or Redis cache
  - Other team containers (`escape-team-*`)
  - The campus LAN or the public Internet

### 2.3 Resource Quotas & Fork Bomb Immunity
To prevent malicious or accidental disruption (e.g. `() { :|:& };:` fork bombs):
```python
container = self.client.containers.run(
    image=settings.DOCKER_IMAGE,
    name=container_name,
    detach=True,
    network_mode="none",
    mem_limit="256m",
    cpu_period=100000,
    cpu_quota=50000,       # Max 0.5 CPU Core
    pids_limit=100,        # Max 100 processes per team
    security_opt=["no-new-privileges:true"],
    cap_drop=["ALL"]       # Drop all Linux capabilities
)
```
If a fork bomb is initiated, process allocation is immediately halted at 100 PIDs without affecting host responsiveness.

### 2.4 Server-Side State Validation & Rate Limiting
- The challenge validation endpoint (`/api/terminal/validate`) does not inspect fragile bash history.
- It validates the cryptographic key against the deterministic HMAC-SHA256 team seed in memory in < 1ms.
- An in-memory sliding-window limiter blocks automated dictionary attacks:
  - Teams exceeding 15 validation attempts in 60 seconds receive `HTTP 429 Too Many Requests` with a `Retry-After` header.

### 2.5 Anti-IDOR Enforcement
- In both the CTFd plugin (`/terminal`) and the WebSocket gateway (`/ws/terminal/{id}`):
- The player's identity is resolved solely from the validated CTFd session cookie.
- If a user from Team 1 attempts to pass `team_id=2` or connect to `/ws/terminal/2`, the request is rejected with `HTTP 403 Forbidden` / WebSocket code `4003`.

---

## 3. Security Audit Verification

The test suite in `tests/security/test_security_hardening.py` automatically validates all controls:
```bash
pytest tests/security/test_security_hardening.py -v
```
- Non-root UID 1001 verified.
- Dropped capabilities verified.
- Rate limiting 429 verified.
- Input bounds (door 1-6, payload < 256 bytes) verified.
- Cross-team IDOR rejection verified.
