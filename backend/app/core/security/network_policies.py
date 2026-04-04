"""
Kubernetes NetworkPolicies and Security Groups
Implements network segmentation and access controls.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import yaml
import json
import logging

logger = logging.getLogger(__name__)


class PolicyType(str, Enum):
    """Network policy types."""
    INGRESS = "Ingress"
    EGRESS = "Egress"


class Protocol(str, Enum):
    """Network protocols."""
    TCP = "TCP"
    UDP = "UDP"
    SCTP = "SCTP"


@dataclass
class PortRule:
    """Port rule for network policies."""
    protocol: Protocol = Protocol.TCP
    port: Optional[int] = None
    port_name: Optional[str] = None  # For named ports
    end_port: Optional[int] = None  # For port ranges
    
    def to_k8s(self) -> Dict[str, Any]:
        rule = {'protocol': self.protocol.value}
        if self.port:
            rule['port'] = self.port
        if self.port_name:
            rule['port'] = self.port_name
        if self.end_port:
            rule['endPort'] = self.end_port
        return rule


@dataclass
class PodSelector:
    """Pod selector for network policies."""
    match_labels: Dict[str, str] = field(default_factory=dict)
    match_expressions: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_k8s(self) -> Dict[str, Any]:
        selector = {}
        if self.match_labels:
            selector['matchLabels'] = self.match_labels
        if self.match_expressions:
            selector['matchExpressions'] = self.match_expressions
        return selector


@dataclass
class NamespaceSelector:
    """Namespace selector for network policies."""
    match_labels: Dict[str, str] = field(default_factory=dict)
    
    def to_k8s(self) -> Dict[str, Any]:
        return {'matchLabels': self.match_labels}


@dataclass
class IPBlock:
    """IP block for network policies."""
    cidr: str
    except_cidrs: List[str] = field(default_factory=list)
    
    def to_k8s(self) -> Dict[str, Any]:
        block = {'cidr': self.cidr}
        if self.except_cidrs:
            block['except'] = self.except_cidrs
        return block


@dataclass
class NetworkPolicyPeer:
    """Network policy peer (source/destination)."""
    pod_selector: Optional[PodSelector] = None
    namespace_selector: Optional[NamespaceSelector] = None
    ip_block: Optional[IPBlock] = None
    
    def to_k8s(self) -> Dict[str, Any]:
        peer = {}
        if self.pod_selector:
            peer['podSelector'] = self.pod_selector.to_k8s()
        if self.namespace_selector:
            peer['namespaceSelector'] = self.namespace_selector.to_k8s()
        if self.ip_block:
            peer['ipBlock'] = self.ip_block.to_k8s()
        return peer


@dataclass
class NetworkPolicyRule:
    """Network policy rule (ingress/egress)."""
    from_peers: List[NetworkPolicyPeer] = field(default_factory=list)
    to_peers: List[NetworkPolicyPeer] = field(default_factory=list)
    ports: List[PortRule] = field(default_factory=list)
    
    def to_k8s_ingress(self) -> Dict[str, Any]:
        rule = {}
        if self.from_peers:
            rule['from'] = [p.to_k8s() for p in self.from_peers]
        if self.ports:
            rule['ports'] = [p.to_k8s() for p in self.ports]
        return rule
    
    def to_k8s_egress(self) -> Dict[str, Any]:
        rule = {}
        if self.to_peers:
            rule['to'] = [p.to_k8s() for p in self.to_peers]
        if self.ports:
            rule['ports'] = [p.to_k8s() for p in self.ports]
        return rule


@dataclass
class NetworkPolicy:
    """Kubernetes NetworkPolicy definition."""
    name: str
    namespace: str
    pod_selector: PodSelector
    policy_types: List[PolicyType]
    ingress_rules: List[NetworkPolicyRule] = field(default_factory=list)
    egress_rules: List[NetworkPolicyRule] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    def to_k8s_yaml(self) -> str:
        """Convert to Kubernetes NetworkPolicy YAML."""
        policy = {
            'apiVersion': 'networking.k8s.io/v1',
            'kind': 'NetworkPolicy',
            'metadata': {
                'name': self.name,
                'namespace': self.namespace,
                'labels': self.labels,
                'annotations': self.annotations
            },
            'spec': {
                'podSelector': self.pod_selector.to_k8s(),
                'policyTypes': [pt.value for pt in self.policy_types]
            }
        }
        
        if self.ingress_rules:
            policy['spec']['ingress'] = [
                r.to_k8s_ingress() for r in self.ingress_rules
            ]
        
        if self.egress_rules:
            policy['spec']['egress'] = [
                r.to_k8s_egress() for r in self.egress_rules
            ]
        
        return yaml.dump(policy, default_flow_style=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return yaml.safe_load(self.to_k8s_yaml())


class NetworkPolicyManager:
    """Manages network policies for microservices."""
    
    # Standard ports
    HTTP_PORT = PortRule(Protocol.TCP, 80)
    HTTPS_PORT = PortRule(Protocol.TCP, 443)
    API_PORT = PortRule(Protocol.TCP, 8000)
    DB_PORT = PortRule(Protocol.TCP, 5432)
    REDIS_PORT = PortRule(Protocol.TCP, 6379)
    KUBE_DNS_PORT = PortRule(Protocol.UDP, 53)
    
    def __init__(self, k8s_client=None):
        self.k8s_client = k8s_client
    
    def create_default_deny_policy(self, namespace: str) -> NetworkPolicy:
        """Create default deny-all policy."""
        return NetworkPolicy(
            name="default-deny-all",
            namespace=namespace,
            pod_selector=PodSelector(),  # Empty selector matches all pods
            policy_types=[PolicyType.INGRESS, PolicyType.EGRESS],
            labels={'policy-type': 'default-deny'}
        )
    
    def create_api_policy(self, namespace: str, 
                         allowed_namespaces: List[str] = None) -> NetworkPolicy:
        """Create policy for API services."""
        ingress_rules = [
            NetworkPolicyRule(
                from_peers=[
                    NetworkPolicyPeer(
                        namespace_selector=NamespaceSelector(
                            match_labels={'name': 'ingress-nginx'}
                        )
                    ),
                    NetworkPolicyPeer(
                        namespace_selector=NamespaceSelector(
                            match_labels={'name': 'istio-system'}
                        )
                    )
                ],
                ports=[self.HTTPS_PORT, self.API_PORT]
            )
        ]
        
        egress_rules = [
            # Allow database access
            NetworkPolicyRule(
                to_peers=[
                    NetworkPolicyPeer(
                        pod_selector=PodSelector(match_labels={'app': 'postgresql'})
                    )
                ],
                ports=[self.DB_PORT]
            ),
            # Allow Redis access
            NetworkPolicyRule(
                to_peers=[
                    NetworkPolicyPeer(
                        pod_selector=PodSelector(match_labels={'app': 'redis'})
                    )
                ],
                ports=[self.REDIS_PORT]
            ),
            # Allow external HTTPS
            NetworkPolicyRule(
                to_peers=[NetworkPolicyPeer(ip_block=IPBlock('0.0.0.0/0'))],
                ports=[self.HTTPS_PORT]
            ),
            # Allow DNS
            NetworkPolicyRule(
                to_peers=[
                    NetworkPolicyPeer(
                        namespace_selector=NamespaceSelector(
                            match_labels={'name': 'kube-system'}
                        ),
                        pod_selector=PodSelector(match_labels={'k8s-app': 'kube-dns'})
                    )
                ],
                ports=[self.KUBE_DNS_PORT]
            )
        ]
        
        return NetworkPolicy(
            name="api-service-policy",
            namespace=namespace,
            pod_selector=PodSelector(match_labels={'app': 'cerebrum-api'}),
            policy_types=[PolicyType.INGRESS, PolicyType.EGRESS],
            ingress_rules=ingress_rules,
            egress_rules=egress_rules,
            labels={'app': 'cerebrum-api', 'tier': 'api'}
        )
    
    def create_database_policy(self, namespace: str) -> NetworkPolicy:
        """Create policy for database pods."""
        ingress_rules = [
            NetworkPolicyRule(
                from_peers=[
                    NetworkPolicyPeer(
                        pod_selector=PodSelector(match_labels={'app': 'cerebrum-api'})
                    ),
                    NetworkPolicyPeer(
                        pod_selector=PodSelector(match_labels={'app': 'cerebrum-worker'})
                    )
                ],
                ports=[self.DB_PORT]
            )
        ]
        
        egress_rules = [
            # Allow DNS
            NetworkPolicyRule(
                to_peers=[
                    NetworkPolicyPeer(
                        namespace_selector=NamespaceSelector(
                            match_labels={'name': 'kube-system'}
                        )
                    )
                ],
                ports=[self.KUBE_DNS_PORT]
            )
        ]
        
        return NetworkPolicy(
            name="database-policy",
            namespace=namespace,
            pod_selector=PodSelector(match_labels={'app': 'postgresql'}),
            policy_types=[PolicyType.INGRESS, PolicyType.EGRESS],
            ingress_rules=ingress_rules,
            egress_rules=egress_rules,
            labels={'app': 'postgresql', 'tier': 'database'}
        )
    
    def create_worker_policy(self, namespace: str) -> NetworkPolicy:
        """Create policy for worker pods."""
        ingress_rules = [
            # Workers typically don't accept external connections
        ]
        
        egress_rules = [
            # Allow database access
            NetworkPolicyRule(
                to_peers=[
                    NetworkPolicyPeer(
                        pod_selector=PodSelector(match_labels={'app': 'postgresql'})
                    )
                ],
                ports=[self.DB_PORT]
            ),
            # Allow Redis access
            NetworkPolicyRule(
                to_peers=[
                    NetworkPolicyPeer(
                        pod_selector=PodSelector(match_labels={'app': 'redis'})
                    )
                ],
                ports=[self.REDIS_PORT]
            ),
            # Allow external HTTPS for webhooks
            NetworkPolicyRule(
                to_peers=[NetworkPolicyPeer(ip_block=IPBlock('0.0.0.0/0'))],
                ports=[self.HTTPS_PORT]
            ),
            # Allow DNS
            NetworkPolicyRule(
                to_peers=[
                    NetworkPolicyPeer(
                        namespace_selector=NamespaceSelector(
                            match_labels={'name': 'kube-system'}
                        )
                    )
                ],
                ports=[self.KUBE_DNS_PORT]
            )
        ]
        
        return NetworkPolicy(
            name="worker-policy",
            namespace=namespace,
            pod_selector=PodSelector(match_labels={'app': 'cerebrum-worker'}),
            policy_types=[PolicyType.INGRESS, PolicyType.EGRESS],
            ingress_rules=ingress_rules,
            egress_rules=egress_rules,
            labels={'app': 'cerebrum-worker', 'tier': 'worker'}
        )
    
    def create_vdc_policy(self, namespace: str) -> NetworkPolicy:
        """Create policy for VDC processing pods."""
        ingress_rules = [
            NetworkPolicyRule(
                from_peers=[
                    NetworkPolicyPeer(
                        pod_selector=PodSelector(match_labels={'app': 'cerebrum-api'})
                    )
                ],
                ports=[PortRule(Protocol.TCP, 8080)]
            )
        ]
        
        egress_rules = [
            # Allow database access
            NetworkPolicyRule(
                to_peers=[
                    NetworkPolicyPeer(
                        pod_selector=PodSelector(match_labels={'app': 'postgresql'})
                    )
                ],
                ports=[self.DB_PORT]
            ),
            # Allow Redis access
            NetworkPolicyRule(
                to_peers=[
                    NetworkPolicyPeer(
                        pod_selector=PodSelector(match_labels={'app': 'redis'})
                    )
                ],
                ports=[self.REDIS_PORT]
            ),
            # Allow object storage (S3, etc.)
            NetworkPolicyRule(
                to_peers=[NetworkPolicyPeer(ip_block=IPBlock('0.0.0.0/0'))],
                ports=[self.HTTPS_PORT]
            ),
            # Allow DNS
            NetworkPolicyRule(
                to_peers=[
                    NetworkPolicyPeer(
                        namespace_selector=NamespaceSelector(
                            match_labels={'name': 'kube-system'}
                        )
                    )
                ],
                ports=[self.KUBE_DNS_PORT]
            )
        ]
        
        return NetworkPolicy(
            name="vdc-policy",
            namespace=namespace,
            pod_selector=PodSelector(match_labels={'app': 'cerebrum-vdc'}),
            policy_types=[PolicyType.INGRESS, PolicyType.EGRESS],
            ingress_rules=ingress_rules,
            egress_rules=egress_rules,
            labels={'app': 'cerebrum-vdc', 'tier': 'processing'}
        )
    
    def apply_policy(self, policy: NetworkPolicy) -> bool:
        """Apply network policy to cluster."""
        if not self.k8s_client:
            logger.warning("No Kubernetes client configured")
            return False
        
        try:
            # Apply using Kubernetes API
            self.k8s_client.apply_network_policy(policy.to_dict())
            logger.info(f"Applied network policy: {policy.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply policy {policy.name}: {e}")
            return False
    
    def generate_all_policies(self, namespace: str) -> List[NetworkPolicy]:
        """Generate all standard policies for a namespace."""
        return [
            self.create_default_deny_policy(namespace),
            self.create_api_policy(namespace),
            self.create_database_policy(namespace),
            self.create_worker_policy(namespace),
            self.create_vdc_policy(namespace)
        ]


class AWSSecurityGroupManager:
    """AWS Security Group management for non-Kubernetes resources."""
    
    def __init__(self, ec2_client=None):
        self.ec2_client = ec2_client
    
    def create_security_group_rules(self, group_id: str, 
                                    rules: List[Dict[str, Any]]) -> bool:
        """Create security group rules."""
        try:
            if self.ec2_client:
                self.ec2_client.authorize_security_group_ingress(
                    GroupId=group_id,
                    IpPermissions=rules
                )
            return True
        except Exception as e:
            logger.error(f"Failed to create security group rules: {e}")
            return False
    
    def create_database_security_group(self, vpc_id: str, 
                                       allowed_security_groups: List[str]) -> str:
        """Create security group for RDS database."""
        # Implementation would create SG using AWS API
        return "sg-placeholder"
