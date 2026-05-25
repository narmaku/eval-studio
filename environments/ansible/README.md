# Ansible Playbooks for BYOE Environment Setup

Ansible playbooks for BYOE (Bring Your Own Environment) setup and teardown.
These playbooks configure target machines into specific "broken" states for
agent evaluation scenarios.

## Status

Playbook implementation is deferred to post-MVP (v0.4.0). See the product
spec Section 19 for the roadmap.

## Planned Playbooks

| Playbook              | Description                                    |
|-----------------------|------------------------------------------------|
| `break-ssh.yml`       | Stop sshd service and misconfigure SSH settings|
| `restore-ssh.yml`     | Restore SSH to working state                   |
| `break-selinux.yml`   | Create SELinux denials on non-standard ports    |
| `restore-selinux.yml` | Restore correct SELinux port labels             |

## Usage (Future)

```bash
# Break the environment for scenario evaluation
ansible-playbook -i inventory.yml break-ssh.yml

# Restore after evaluation
ansible-playbook -i inventory.yml restore-ssh.yml
```
