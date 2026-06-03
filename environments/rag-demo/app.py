"""Sample RAG (Retrieval-Augmented Generation) service for eval-studio demo testing.

This is a self-contained FastAPI service that:
- Loads sample RHEL sysadmin documents on startup
- Computes embeddings using sentence-transformers/all-MiniLM-L6-v2
- Builds a FAISS index for vector similarity search
- Serves a /query endpoint that retrieves relevant chunks and generates answers via LiteLLM
- Provides a /health endpoint for readiness checks

The service is designed to work with eval-studio's RAG evaluation adapter,
which expects POST /query with {"query": "..."} and a response containing
{"answer": "...", "source_documents": [{"content": "...", "source": "..."}]}.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger("rag-demo")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Sample RHEL sysadmin document corpus (20 documents)
# ---------------------------------------------------------------------------

SAMPLE_DOCUMENTS: list[dict[str, str]] = [
    {
        "content": (
            "To check the status of a systemd service, use the command "
            "'systemctl status <service-name>'. This shows whether the service is active, "
            "inactive, or failed, along with recent log entries. For example, "
            "'systemctl status sshd' shows the status of the SSH daemon. The output "
            "includes the loaded unit file path, active state, main PID, and memory usage."
        ),
        "source": "systemd-services.md",
    },
    {
        "content": (
            "SELinux (Security-Enhanced Linux) provides mandatory access control (MAC) "
            "in RHEL. It operates in three modes: Enforcing (policies are enforced), "
            "Permissive (policies are not enforced but violations are logged), and "
            "Disabled. Check the current mode with 'getenforce' or 'sestatus'. To "
            "temporarily change to permissive mode: 'setenforce 0'. To permanently "
            "change, edit /etc/selinux/config and set SELINUX=permissive, then reboot."
        ),
        "source": "selinux-guide.md",
    },
    {
        "content": (
            "Firewalld is the default firewall management tool in RHEL. It uses zones "
            "to define the trust level of network connections. Common commands: "
            "'firewall-cmd --state' (check status), 'firewall-cmd --list-all' (show "
            "current rules), 'firewall-cmd --add-service=http --permanent' (allow HTTP "
            "permanently), 'firewall-cmd --reload' (apply changes). The default zone "
            "is usually 'public'."
        ),
        "source": "firewalld-guide.md",
    },
    {
        "content": (
            "DNF (Dandified YUM) is the package manager for RHEL 8 and later. Key "
            "commands: 'dnf install <package>' (install), 'dnf update' (update all "
            "packages), 'dnf remove <package>' (uninstall), 'dnf search <keyword>' "
            "(search), 'dnf info <package>' (package details), 'dnf list installed' "
            "(list installed). Use 'dnf module' for modular content management."
        ),
        "source": "dnf-package-management.md",
    },
    {
        "content": (
            "To manage users in RHEL, use these commands: 'useradd <username>' (create "
            "user), 'usermod -aG <group> <username>' (add to group), 'passwd <username>' "
            "(set password), 'userdel -r <username>' (delete user and home dir), "
            "'id <username>' (show user info). User information is stored in /etc/passwd, "
            "passwords in /etc/shadow, and groups in /etc/group."
        ),
        "source": "user-management.md",
    },
    {
        "content": (
            "Podman is the container management tool in RHEL, designed as a drop-in "
            "replacement for Docker. It runs containers without a daemon (daemonless). "
            "Key commands: 'podman run' (run container), 'podman ps' (list running), "
            "'podman images' (list images), 'podman build' (build image), 'podman pull' "
            "(pull image). Podman supports rootless containers for improved security."
        ),
        "source": "podman-containers.md",
    },
    {
        "content": (
            "NetworkManager is the primary network configuration tool in RHEL. Use "
            "'nmcli' for command-line management: 'nmcli device status' (show devices), "
            "'nmcli connection show' (list connections), 'nmcli connection add type "
            "ethernet con-name eth0 ifname eth0' (add connection), 'nmcli connection "
            "modify eth0 ipv4.addresses 192.168.1.100/24' (set static IP). Configuration "
            "files are in /etc/NetworkManager/."
        ),
        "source": "networking-guide.md",
    },
    {
        "content": (
            "LVM (Logical Volume Manager) provides flexible disk management in RHEL. "
            "The hierarchy is: Physical Volumes (PV) -> Volume Groups (VG) -> Logical "
            "Volumes (LV). Create PV: 'pvcreate /dev/sdb'. Create VG: 'vgcreate myvg "
            "/dev/sdb'. Create LV: 'lvcreate -L 10G -n mylv myvg'. Extend LV: "
            "'lvextend -L +5G /dev/myvg/mylv'. Resize filesystem: 'resize2fs "
            "/dev/myvg/mylv'."
        ),
        "source": "lvm-storage.md",
    },
    {
        "content": (
            "Journald is the logging system in RHEL managed by systemd. View logs with "
            "'journalctl'. Common filters: 'journalctl -u sshd' (by service), "
            "'journalctl --since today' (by time), 'journalctl -p err' (by priority), "
            "'journalctl -f' (follow/tail), 'journalctl -b' (current boot). Persistent "
            "logging requires creating /var/log/journal/ directory. Configure in "
            "/etc/systemd/journald.conf."
        ),
        "source": "journald-logging.md",
    },
    {
        "content": (
            "Chrony is the default NTP implementation in RHEL for time synchronization. "
            "The main configuration file is /etc/chrony.conf. Key commands: 'chronyc "
            "tracking' (show sync status), 'chronyc sources' (show time sources), "
            "'timedatectl' (show/set time), 'timedatectl set-timezone America/New_York' "
            "(set timezone). Chrony is preferred over ntpd for its better accuracy and "
            "faster synchronization."
        ),
        "source": "time-synchronization.md",
    },
    {
        "content": (
            "SSH (Secure Shell) configuration in RHEL is managed via /etc/ssh/sshd_config. "
            "Important settings: PermitRootLogin (disable for security), "
            "PasswordAuthentication (disable to force key-based auth), Port (change "
            "default 22 for security). Generate SSH keys: 'ssh-keygen -t ed25519'. Copy "
            "public key: 'ssh-copy-id user@host'. Restart after changes: 'systemctl "
            "restart sshd'. Use 'ssh-agent' for key management."
        ),
        "source": "ssh-configuration.md",
    },
    {
        "content": (
            "RHEL subscription management uses 'subscription-manager' to register systems "
            "and attach subscriptions. Key commands: 'subscription-manager register' "
            "(register with Red Hat), 'subscription-manager attach --auto' (auto-attach "
            "subscription), 'subscription-manager list --available' (show available "
            "subscriptions), 'subscription-manager repos --enable <repo>' (enable "
            "repository). Simple Content Access (SCA) simplifies entitlement management."
        ),
        "source": "subscription-management.md",
    },
    {
        "content": (
            "Cockpit is the web-based administration interface for RHEL. Install with "
            "'dnf install cockpit'. Enable and start: 'systemctl enable --now "
            "cockpit.socket'. Access at https://hostname:9090. Cockpit provides GUI "
            "management for storage, networking, users, services, containers, virtual "
            "machines, and more. Modules can be installed separately: cockpit-machines, "
            "cockpit-podman, cockpit-storaged."
        ),
        "source": "cockpit-admin.md",
    },
    {
        "content": (
            "Tuned is the dynamic adaptive system tuning daemon in RHEL. It optimizes "
            "system performance based on selected profiles. Key commands: 'tuned-adm "
            "list' (show profiles), 'tuned-adm active' (show current), 'tuned-adm "
            "profile throughput-performance' (set profile). Common profiles: balanced "
            "(default), throughput-performance (high throughput), latency-performance "
            "(low latency), virtual-guest (optimized for VMs)."
        ),
        "source": "tuned-performance.md",
    },
    {
        "content": (
            "Ansible is Red Hat's automation platform used extensively with RHEL. "
            "Install with 'dnf install ansible-core'. Key concepts: inventory (target "
            "hosts), playbooks (YAML automation), modules (task units), roles (reusable "
            "content). Run ad-hoc: 'ansible all -m ping'. Run playbook: "
            "'ansible-playbook site.yml'. Ansible Automation Platform provides enterprise "
            "features including a web UI, RBAC, and credential management."
        ),
        "source": "ansible-automation.md",
    },
    {
        "content": (
            "RHEL Identity Management (IdM/FreeIPA) provides centralized authentication, "
            "authorization, and account information. It integrates Kerberos, LDAP, DNS, "
            "and certificate management. Install server: 'dnf install ipa-server'. "
            "Initialize: 'ipa-server-install'. Join client: 'ipa-client-install'. Key "
            "features: single sign-on, host-based access control (HBAC), sudo rules, "
            "password policies, and certificate authority."
        ),
        "source": "identity-management.md",
    },
    {
        "content": (
            "System boot process in RHEL follows: BIOS/UEFI -> GRUB2 bootloader -> "
            "kernel + initramfs -> systemd (PID 1) -> target units. GRUB2 config: "
            "/etc/default/grub (edit, then 'grub2-mkconfig -o /boot/grub2/grub.cfg'). "
            "Default target: 'systemctl get-default'. Change: 'systemctl set-default "
            "multi-user.target'. Emergency mode: add 'systemd.unit=emergency.target' to "
            "kernel command line."
        ),
        "source": "boot-process.md",
    },
    {
        "content": (
            "Stratis is a modern local storage management solution in RHEL that combines "
            "thin provisioning, snapshots, and monitoring. Create pool: 'stratis pool "
            "create mypool /dev/sdb'. Create filesystem: 'stratis filesystem create "
            "mypool myfs'. Mount: 'mount /dev/stratis/mypool/myfs /mnt'. Create "
            "snapshot: 'stratis filesystem snapshot mypool myfs myfs-snap'. Stratis uses "
            "XFS and device-mapper."
        ),
        "source": "stratis-storage.md",
    },
    {
        "content": (
            "Process management in RHEL uses systemd for service processes and "
            "traditional tools for user processes. Key commands: 'ps aux' (list all), "
            "'top'/'htop' (interactive monitor), 'kill <PID>' (terminate), 'nice -n 10 "
            "command' (set priority), 'renice +5 -p <PID>' (change priority). Cgroups v2 "
            "provides resource control: 'systemd-cgls' (show hierarchy), 'systemctl "
            "set-property <service> MemoryMax=512M' (limit memory)."
        ),
        "source": "process-management.md",
    },
    {
        "content": (
            "RHEL system security hardening includes: running 'oscap' for OpenSCAP "
            "compliance scanning, enabling FIPS mode ('fips-mode-setup --enable'), "
            "configuring audit rules in /etc/audit/audit.rules, using 'aide' for file "
            "integrity monitoring, implementing crypto-policies ('update-crypto-policies "
            "--set FUTURE'), and applying security profiles from the SCAP Security "
            "Guide. The 'security' DNF group provides essential security tools."
        ),
        "source": "security-hardening.md",
    },
]

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    """Request body for the /query endpoint."""

    query: str


class SourceDocument(BaseModel):
    """A retrieved document chunk with its source reference."""

    content: str
    source: str


class QueryResponse(BaseModel):
    """Response body for the /query endpoint."""

    answer: str
    source_documents: list[SourceDocument]


class HealthResponse(BaseModel):
    """Response body for the /health endpoint."""

    status: str
    documents_loaded: int
    index_ready: bool
    llm_configured: bool


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------


class RAGState:
    """Holds the in-memory RAG pipeline state."""

    def __init__(self) -> None:
        self.documents: list[dict[str, str]] = []
        self.index: Any = None  # faiss.IndexFlatIP
        self.embedder: Any = None  # SentenceTransformer
        self.ready: bool = False


state = RAGState()

# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


def _build_index() -> None:
    """Load documents, compute embeddings, and build the FAISS index."""
    import faiss
    from sentence_transformers import SentenceTransformer

    logger.info("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
    t0 = time.time()
    state.embedder = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("Model loaded in %.2fs", time.time() - t0)

    state.documents = SAMPLE_DOCUMENTS
    texts = [doc["content"] for doc in state.documents]

    logger.info("Computing embeddings for %d documents...", len(texts))
    t0 = time.time()
    embeddings = state.embedder.encode(texts, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype=np.float32)
    logger.info("Embeddings computed in %.2fs", time.time() - t0)

    # Build FAISS inner-product index (embeddings are L2-normalized, so IP == cosine)
    dim = embeddings.shape[1]
    state.index = faiss.IndexFlatIP(dim)
    state.index.add(embeddings)
    logger.info("FAISS index built with %d vectors of dimension %d", state.index.ntotal, dim)

    state.ready = True


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Build the RAG index on startup."""
    _build_index()
    yield


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sample RAG Service",
    description="A demo RAG service for eval-studio RAG evaluation testing.",
    version="0.1.0",
    lifespan=lifespan,
)


def _retrieve(query: str, top_k: int = 5) -> list[SourceDocument]:
    """Embed the query and retrieve the top-k most similar documents."""
    query_embedding = state.embedder.encode([query], normalize_embeddings=True)
    query_embedding = np.array(query_embedding, dtype=np.float32)

    scores, indices = state.index.search(query_embedding, top_k)

    results: list[SourceDocument] = []
    for i, idx in enumerate(indices[0]):
        if idx < 0:
            # FAISS returns -1 for unfilled slots
            continue
        doc = state.documents[idx]
        results.append(SourceDocument(content=doc["content"], source=doc["source"]))
        logger.debug("  [%d] score=%.4f source=%s", i, scores[0][i], doc["source"])

    return results


def _generate_answer(query: str, context_docs: list[SourceDocument]) -> str:
    """Generate an answer using LiteLLM, or fall back to a context-only response."""
    model = os.environ.get("LITELLM_MODEL", "")
    if not model:
        return (
            f"[LLM not configured -- returning retrieved context only] "
            f"Found {len(context_docs)} relevant document(s) for: '{query}'. "
            f"Set LITELLM_MODEL and the appropriate API key environment variable "
            f"to enable answer generation."
        )

    try:
        import litellm

        context_text = "\n\n---\n\n".join(
            f"Source: {doc.source}\n{doc.content}" for doc in context_docs
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful RHEL system administration assistant. "
                    "Answer the user's question based on the provided context documents. "
                    "Be concise and accurate. If the context doesn't contain enough "
                    "information, say so."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Context documents:\n\n{context_text}\n\n---\n\n"
                    f"Question: {query}\n\nAnswer:"
                ),
            },
        ]

        response = litellm.completion(model=model, messages=messages, max_tokens=512)
        return response.choices[0].message.content.strip()

    except Exception as exc:
        logger.warning("LLM generation failed: %s", exc)
        return (
            f"[LLM generation failed: {exc}] "
            f"Returning retrieved context from {len(context_docs)} document(s)."
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Retrieve relevant documents and generate an answer for the given query."""
    logger.info("Query: %s", request.query)

    source_documents = _retrieve(request.query, top_k=5)
    answer = _generate_answer(request.query, source_documents)

    return QueryResponse(answer=answer, source_documents=source_documents)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(
        status="ok" if state.ready else "initializing",
        documents_loaded=len(state.documents),
        index_ready=state.ready,
        llm_configured=bool(os.environ.get("LITELLM_MODEL", "")),
    )
