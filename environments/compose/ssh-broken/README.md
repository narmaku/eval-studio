# SSH-Broken Scenario Environment

## Feasibility Note

SSH-broken scenarios require systemd to manage the sshd service. Standard
containers do not run systemd by default.

### Implementation Options

1. **Privileged container with systemd as PID 1** -- Complex setup with
   security tradeoffs. Requires `--privileged` flag and mounting cgroups.

2. **Simulate by stopping sshd process directly** -- Simpler but less
   realistic. The agent cannot use `systemctl` commands, only process
   management.

3. **Use BYOE with a real VM** -- Most realistic option. The agent
   interacts with a real RHEL machine with full systemd support.

### Recommendation

Defer to BYOE (Bring Your Own Environment) for realistic SSH scenarios.
Use Docker Compose templates only for simple command-based scenarios where
systemd is not required.

See `environments/scenarios/ssh-diagnosis.yaml` for the scenario definition.
