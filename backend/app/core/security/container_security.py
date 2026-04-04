"""
Container Security - Distroless Images, Non-Root User
Implements container security best practices.
"""
import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ImageType(str, Enum):
    """Types of container images."""
    DISTROLESS = "distroless"
    ALPINE = "alpine"
    SCRATCH = "scratch"
    STANDARD = "standard"


class Severity(str, Enum):
    """Vulnerability severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class SecurityPolicy:
    """Container security policy."""
    run_as_non_root: bool = True
    read_only_root_filesystem: bool = True
    allow_privilege_escalation: bool = False
    drop_all_capabilities: bool = True
    add_capabilities: List[str] = field(default_factory=list)
    seccomp_profile: Optional[str] = None
    apparmor_profile: Optional[str] = None
    run_as_user: int = 1000
    run_as_group: int = 1000
    fs_group: int = 1000


@dataclass
class Vulnerability:
    """Represents a container vulnerability."""
    id: str
    package: str
    installed_version: str
    fixed_version: Optional[str]
    severity: Severity
    description: str
    cve_ids: List[str] = field(default_factory=list)


class ContainerImageBuilder:
    """Builds secure container images."""
    
    # Base images
    DISTROLESS_PYTHON = "gcr.io/distroless/python3-debian12"
    DISTROLESS_NODE = "gcr.io/distroless/nodejs20-debian12"
    ALPINE_PYTHON = "python:3.11-alpine"
    ALPINE_NODE = "node:20-alpine"
    
    def __init__(self, app_name: str, app_version: str):
        self.app_name = app_name
        self.app_version = app_version
    
    def generate_dockerfile_distroless(self, 
                                       language: str = "python",
                                       entry_point: str = "main.py") -> str:
        """Generate Dockerfile using distroless base image."""
        
        if language == "python":
            base_image = self.DISTROLESS_PYTHON
            build_stage = f"""# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application
COPY . .

# Production stage
FROM {base_image}

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/nonroot/.local
COPY --from=builder /app /app

# Set environment
ENV PATH=/home/nonroot/.local/bin:$PATH
ENV PYTHONPATH=/home/nonroot/.local/lib/python3.11/site-packages

# Non-root user (distroless uses nonroot:nonroot)
USER nonroot:nonroot

WORKDIR /app

# Run application
ENTRYPOINT ["python", "{entry_point}"]
"""
        elif language == "node":
            base_image = self.DISTROLESS_NODE
            build_stage = f"""# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application
COPY . .

# Production stage
FROM {base_image}

# Copy application from builder
COPY --from=builder /app /app

# Non-root user
USER nonroot:nonroot

WORKDIR /app

# Run application
ENTRYPOINT ["node", "{entry_point}"]
"""
        else:
            raise ValueError(f"Unsupported language: {language}")
        
        return build_stage
    
    def generate_dockerfile_alpine(self,
                                   language: str = "python",
                                   entry_point: str = "main.py") -> str:
        """Generate Dockerfile using Alpine base image."""
        
        if language == "python":
            dockerfile = f"""FROM {self.ALPINE_PYTHON}

# Create non-root user
RUN addgroup -g 1000 -S appgroup && \\
    adduser -u 1000 -S appuser -G appgroup

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set permissions
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["python", "{entry_point}"]
"""
        elif language == "node":
            dockerfile = f"""FROM {self.ALPINE_NODE}

# Create non-root user
RUN addgroup -g 1000 -S appgroup && \\
    adduser -u 1000 -S appuser -G appgroup

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application
COPY . .

# Set permissions
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD node -e "require('http').get('http://localhost:3000/health', (r) => r.statusCode === 200 ? process.exit(0) : process.exit(1))"

ENTRYPOINT ["node", "{entry_point}"]
"""
        else:
            raise ValueError(f"Unsupported language: {language}")
        
        return dockerfile
    
    def generate_dockerignore(self) -> str:
        """Generate .dockerignore file."""
        return """# Git
.git
.gitignore
.gitattributes

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
.coverage
htmlcov/
.tox/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.eslintcache
*.tsbuildinfo

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Secrets
.env
.env.local
.env.*.local
*.pem
*.key
secrets/

# Tests
tests/
test/
*.test.js
*.test.ts
*.test.py

# Documentation
docs/
*.md
!README.md

# CI/CD
.github/
.gitlab-ci.yml
.travis.yml
azure-pipelines.yml

# Docker
Dockerfile*
docker-compose*
.docker/
"""


class KubernetesSecurity:
    """Kubernetes security configurations."""
    
    @staticmethod
    def generate_security_context(policy: SecurityPolicy) -> Dict[str, Any]:
        """Generate Kubernetes security context."""
        context = {
            'runAsNonRoot': policy.run_as_non_root,
            'runAsUser': policy.run_as_user,
            'runAsGroup': policy.run_as_group,
            'fsGroup': policy.fs_group,
            'readOnlyRootFilesystem': policy.read_only_root_filesystem,
            'allowPrivilegeEscalation': policy.allow_privilege_escalation,
        }
        
        if policy.drop_all_capabilities:
            context['capabilities'] = {
                'drop': ['ALL']
            }
        
        if policy.add_capabilities:
            if 'capabilities' not in context:
                context['capabilities'] = {}
            context['capabilities']['add'] = policy.add_capabilities
        
        if policy.seccomp_profile:
            context['seccompProfile'] = {
                'type': 'Localhost',
                'localhostProfile': policy.seccomp_profile
            }
        
        return context
    
    @staticmethod
    def generate_pod_security_policy() -> Dict[str, Any]:
        """Generate Pod Security Policy (deprecated, use Pod Security Standards)."""
        return {
            'apiVersion': 'policy/v1beta1',
            'kind': 'PodSecurityPolicy',
            'metadata': {
                'name': 'cerebrum-restricted'
            },
            'spec': {
                'privileged': False,
                'allowPrivilegeEscalation': False,
                'requiredDropCapabilities': ['ALL'],
                'volumes': [
                    'configMap', 'emptyDir', 'projected', 'secret',
                    'downwardAPI', 'persistentVolumeClaim'
                ],
                'runAsUser': {
                    'rule': 'MustRunAsNonRoot'
                },
                'seLinux': {
                    'rule': 'RunAsAny'
                },
                'fsGroup': {
                    'rule': 'RunAsAny'
                },
                'readOnlyRootFilesystem': True
            }
        }
    
    @staticmethod
    def generate_pod_security_standard(level: str = "restricted") -> Dict[str, Any]:
        """Generate Pod Security Standard configuration."""
        return {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': 'cerebrum',
                'labels': {
                    'pod-security.kubernetes.io/enforce': level,
                    'pod-security.kubernetes.io/audit': level,
                    'pod-security.kubernetes.io/warn': level
                }
            }
        }


class VulnerabilityScanner:
    """Scans container images for vulnerabilities."""
    
    def __init__(self, scanner_type: str = "trivy"):
        self.scanner_type = scanner_type
    
    def scan_image(self, image_name: str) -> List[Vulnerability]:
        """Scan a container image for vulnerabilities."""
        # Placeholder - integrate with Trivy, Snyk, etc.
        logger.info(f"Scanning image: {image_name}")
        return []
    
    def generate_scan_command(self, image_name: str, 
                             output_format: str = "json") -> str:
        """Generate vulnerability scan command."""
        if self.scanner_type == "trivy":
            return f"trivy image --format {output_format} --output scan-results.json {image_name}"
        elif self.scanner_type == "snyk":
            return f"snyk container test {image_name} --json-file-output=scan-results.json"
        else:
            raise ValueError(f"Unsupported scanner: {self.scanner_type}")
    
    def parse_scan_results(self, results_file: str) -> List[Vulnerability]:
        """Parse vulnerability scan results."""
        try:
            with open(results_file, 'r') as f:
                data = json.load(f)
            
            vulnerabilities = []
            
            if self.scanner_type == "trivy":
                for result in data.get('Results', []):
                    for vuln in result.get('Vulnerabilities', []):
                        vulnerabilities.append(Vulnerability(
                            id=vuln.get('VulnerabilityID', ''),
                            package=vuln.get('PkgName', ''),
                            installed_version=vuln.get('InstalledVersion', ''),
                            fixed_version=vuln.get('FixedVersion'),
                            severity=Severity(vuln.get('Severity', 'UNKNOWN')),
                            description=vuln.get('Description', ''),
                            cve_ids=vuln.get('References', [])
                        ))
            
            return vulnerabilities
        
        except Exception as e:
            logger.error(f"Failed to parse scan results: {e}")
            return []


class ImageSigning:
    """Container image signing with Cosign."""
    
    @staticmethod
    def generate_sign_command(image_name: str, key_path: str) -> str:
        """Generate cosign sign command."""
        return f"cosign sign --key {key_path} {image_name}"
    
    @staticmethod
    def generate_verify_command(image_name: str, key_path: str) -> str:
        """Generate cosign verify command."""
        return f"cosign verify --key {key_path} {image_name}"
    
    @staticmethod
    def generate_key_generation_command() -> str:
        """Generate cosign key generation command."""
        return "cosign generate-key-pair"


class ContainerRuntimeSecurity:
    """Runtime security for containers."""
    
    @staticmethod
    def generate_falco_rule() -> str:
        """Generate Falco rule for container security monitoring."""
        return """# Cerebrum Container Security Rules
- rule: Non-Root User Violation
  desc: Detect processes running as root
  condition: spawned_process and user.name = root
  output: "Root process detected (user=%user.name command=%proc.cmdline)"
  priority: WARNING

- rule: Privilege Escalation
  desc: Detect privilege escalation attempts
  condition: spawned_process and (proc.name in (sudo, su) or proc.suid)
  output: "Privilege escalation detected (command=%proc.cmdline)"
  priority: CRITICAL

- rule: Sensitive File Access
  desc: Detect access to sensitive files
  condition: >
    open_read and
    (fd.name contains "/etc/shadow" or
     fd.name contains "/etc/passwd" or
     fd.name contains "/etc/hosts")
  output: "Sensitive file accessed (file=%fd.name user=%user.name)"
  priority: NOTICE

- rule: Outbound Connection
  desc: Detect unexpected outbound connections
  condition: >
    outbound and
    not (fd.sip in (trusted_cidrs))
  output: "Outbound connection (connection=%fd.name)"
  priority: NOTICE
"""
    
    @staticmethod
    def generate_seccomp_profile() -> Dict[str, Any]:
        """Generate seccomp security profile."""
        return {
            "defaultAction": "SCMP_ACT_ERRNO",
            "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_X86"],
            "syscalls": [
                {
                    "names": [
                        "accept", "accept4", "access", "alarm", "bind",
                        "brk", "capget", "capset", "chdir", "chmod",
                        "chown", "clock_gettime", "clone", "close",
                        "connect", "copy_file_range", "creat", "dup",
                        "dup2", "dup3", "epoll_create", "epoll_create1",
                        "epoll_ctl", "epoll_pwait", "epoll_wait", "eventfd",
                        "eventfd2", "execve", "execveat", "exit", "exit_group",
                        "faccessat", "fadvise64", "fallocate", "fanotify_mark",
                        "fchdir", "fchmod", "fchmodat", "fchown", "fchownat",
                        "fcntl", "fdatasync", "fgetxattr", "flistxattr",
                        "flock", "fork", "fremovexattr", "fsetxattr", "fstat",
                        "fstatfs", "fsync", "ftruncate", "futex", "getcpu",
                        "getcwd", "getdents", "getdents64", "getegid",
                        "geteuid", "getgid", "getgroups", "getitimer",
                        "getpeername", "getpgid", "getpgrp", "getpid",
                        "getppid", "getpriority", "getrandom", "getresgid",
                        "getresuid", "getrlimit", "get_robust_list", "getrusage",
                        "getsid", "getsockname", "getsockopt", "get_thread_area",
                        "gettid", "gettimeofday", "getuid", "getxattr",
                        "inotify_add_watch", "inotify_init", "inotify_init1",
                        "inotify_rm_watch", "io_cancel", "ioctl", "io_destroy",
                        "io_getevents", "io_pgetevents", "ioprio_get",
                        "ioprio_set", "io_setup", "io_submit", "io_uring_enter",
                        "io_uring_register", "io_uring_setup", "ipc", "kill",
                        "lchown", "lgetxattr", "link", "linkat", "listen",
                        "listxattr", "llistxattr", "lremovexattr", "lseek",
                        "lsetxattr", "lstat", "madvise", "membarrier",
                        "memfd_create", "mincore", "mkdir", "mkdirat", "mknod",
                        "mknodat", "mlock", "mlock2", "mlockall", "mmap",
                        "mprotect", "mq_getsetattr", "mq_notify", "mq_open",
                        "mq_timedreceive", "mq_timedsend", "mq_unlink", "mremap",
                        "msgctl", "msgget", "msgrcv", "msgsnd", "msync",
                        "munlock", "munlockall", "munmap", "nanosleep",
                        "newfstatat", "open", "openat", "pause", "pipe",
                        "pipe2", "poll", "ppoll", "prctl", "pread64",
                        "preadv", "preadv2", "prlimit64", "pselect6",
                        "pwrite64", "pwritev", "pwritev2", "read", "readahead",
                        "readdir", "readlink", "readlinkat", "readv",
                        "recv", "recvfrom", "recvmmsg", "recvmsg", "remap_file_pages",
                        "removexattr", "rename", "renameat", "renameat2",
                        "restart_syscall", "rmdir", "rt_sigaction", "rt_sigpending",
                        "rt_sigprocmask", "rt_sigqueueinfo", "rt_sigreturn",
                        "rt_sigsuspend", "rt_sigtimedwait", "rt_tgsigqueueinfo",
                        "sched_getaffinity", "sched_getattr", "sched_getparam",
                        "sched_get_priority_max", "sched_get_priority_min",
                        "sched_getscheduler", "sched_rr_get_interval",
                        "sched_setaffinity", "sched_setattr", "sched_setparam",
                        "sched_setscheduler", "sched_yield", "seccomp",
                        "select", "semctl", "semget", "semop", "semtimedop",
                        "send", "sendfile", "sendmmsg", "sendmsg", "sendto",
                        "setfsgid", "setfsuid", "setgid", "setgroups",
                        "setitimer", "setpgid", "setpriority", "setregid",
                        "setresgid", "setresuid", "setreuid", "setrlimit",
                        "set_robust_list", "setsid", "setsockopt", "set_thread_area",
                        "set_tid_address", "setuid", "setxattr", "shmat",
                        "shmctl", "shmdt", "shmget", "shutdown", "sigaltstack",
                        "signalfd", "signalfd4", "socket", "socketcall",
                        "socketpair", "splice", "stat", "statfs", "statx",
                        "symlink", "symlinkat", "sync", "sync_file_range",
                        "syncfs", "sysinfo", "tee", "tgkill", "time",
                        "timer_create", "timer_delete", "timer_getoverrun",
                        "timer_gettime", "timer_settime", "timerfd_create",
                        "timerfd_gettime", "timerfd_settime", "times", "tkill",
                        "truncate", "ugetrlimit", "umask", "uname", "unlink",
                        "unlinkat", "utime", "utimensat", "utimes", "vfork",
                        "wait4", "waitid", "waitpid", "write", "writev"
                    ],
                    "action": "SCMP_ACT_ALLOW"
                }
            ]
        }
