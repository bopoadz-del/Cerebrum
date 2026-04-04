"""
Dependency Resolver

Handles version constraints and dependency graph resolution for capabilities.
"""
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from packaging import version as pkg_version
from packaging.requirements import Requirement
import logging

logger = logging.getLogger(__name__)


@dataclass
class VersionConstraint:
    """Represents a version constraint for a dependency."""
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    exact_version: Optional[str] = None
    exclude_versions: List[str] = field(default_factory=list)
    
    def is_satisfied_by(self, version: str) -> bool:
        """Check if a version satisfies this constraint."""
        try:
            v = pkg_version.parse(version)
            
            if self.exact_version and v != pkg_version.parse(self.exact_version):
                return False
            if self.min_version and v < pkg_version.parse(self.min_version):
                return False
            if self.max_version and v > pkg_version.parse(self.max_version):
                return False
            for excl in self.exclude_versions:
                if v == pkg_version.parse(excl):
                    return False
            return True
        except Exception as e:
            logger.error(f"Version parsing error: {e}")
            return False
    
    @classmethod
    def from_string(cls, constraint_str: str) -> "VersionConstraint":
        """Parse constraint string like '>=1.0.0,<2.0.0'."""
        constraint = cls()
        
        # Handle exact version
        if re.match(r"^\d+\.\d+\.\d+$", constraint_str):
            constraint.exact_version = constraint_str
            return constraint
        
        # Parse complex constraints
        parts = constraint_str.split(",")
        for part in parts:
            part = part.strip()
            if part.startswith(">="):
                constraint.min_version = part[2:]
            elif part.startswith(">"):
                # Strictly greater - use next patch version
                v = part[1:]
                constraint.min_version = v
            elif part.startswith("<="):
                constraint.max_version = part[2:]
            elif part.startswith("<"):
                v = part[1:]
                constraint.max_version = v
            elif part.startswith("!="):
                constraint.exclude_versions.append(part[2:])
            elif part.startswith("=="):
                constraint.exact_version = part[2:]
        
        return constraint


class DependencyNode:
    """Node in the dependency graph."""
    def __init__(self, capability_id: str, version: str):
        self.capability_id = capability_id
        self.version = version
        self.dependencies: Dict[str, VersionConstraint] = {}
        self.dependents: Set[str] = set()
        self.resolved = False
    
    def add_dependency(self, dep_id: str, constraint: VersionConstraint):
        self.dependencies[dep_id] = constraint


class DependencyResolver:
    """
    Resolves capability dependencies with version constraints.
    
    Supports:
    - Version constraint parsing (semver)
    - Circular dependency detection
    - Transitive dependency resolution
    - Topological sort for install order
    """
    
    def __init__(self):
        self._nodes: Dict[str, DependencyNode] = {}
        self._versions: Dict[str, List[str]] = defaultdict(list)  # capability_id -> versions
    
    def register_capability(self, capability_id: str, version: str, 
                           dependencies: Dict[str, str] = None):
        """Register a capability with its dependencies."""
        node = DependencyNode(capability_id, version)
        
        if dependencies:
            for dep_id, constraint_str in dependencies.items():
                constraint = VersionConstraint.from_string(constraint_str)
                node.add_dependency(dep_id, constraint)
        
        self._nodes[capability_id] = node
        if version not in self._versions[capability_id]:
            self._versions[capability_id].append(version)
    
    def resolve(self, root_capability_id: str) -> Tuple[List[str], List[str], List[List[str]]]:
        """
        Resolve dependencies for a capability.
        
        Returns:
            Tuple of (resolved_order, unresolved, circular_deps)
        """
        if root_capability_id not in self._nodes:
            return [], [root_capability_id], []
        
        # Detect circular dependencies
        circular = self._detect_cycles(root_capability_id)
        if circular:
            return [], [], circular
        
        # Topological sort for install order
        resolved, unresolved = self._topological_sort(root_capability_id)
        
        return resolved, unresolved, []
    
    def _detect_cycles(self, start_id: str) -> List[List[str]]:
        """Detect circular dependencies using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            node = self._nodes.get(node_id)
            if node:
                for dep_id in node.dependencies:
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        # Found cycle
                        cycle_start = path.index(dep_id)
                        cycles.append(path[cycle_start:] + [dep_id])
            
            path.pop()
            rec_stack.remove(node_id)
            return False
        
        dfs(start_id)
        return cycles
    
    def _topological_sort(self, start_id: str) -> Tuple[List[str], List[str]]:
        """Perform topological sort for install order."""
        in_degree = defaultdict(int)
        graph = defaultdict(list)
        unresolved = []
        
        # Build graph
        visited = set()
        queue = deque([start_id])
        
        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            
            node = self._nodes.get(node_id)
            if not node:
                unresolved.append(node_id)
                continue
            
            for dep_id in node.dependencies:
                graph[dep_id].append(node_id)
                in_degree[node_id] += 1
                if dep_id not in visited:
                    queue.append(dep_id)
        
        # Kahn's algorithm
        resolved = []
        queue = deque([cap_id for cap_id in visited if in_degree[cap_id] == 0])
        
        while queue:
            node_id = queue.popleft()
            resolved.append(node_id)
            
            for dependent in graph[node_id]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Check for unresolved
        if len(resolved) != len(visited) - len(unresolved):
            for cap_id in visited:
                if cap_id not in resolved and cap_id not in unresolved:
                    unresolved.append(cap_id)
        
        return resolved, unresolved
    
    def check_compatibility(self, capability_id: str, 
                           target_version: str) -> Tuple[bool, List[str]]:
        """Check if a version upgrade is compatible with dependents."""
        node = self._nodes.get(capability_id)
        if not node:
            return False, ["Capability not found"]
        
        issues = []
        
        for dependent_id in node.dependents:
            dep_node = self._nodes.get(dependent_id)
            if dep_node and capability_id in dep_node.dependencies:
                constraint = dep_node.dependencies[capability_id]
                if not constraint.is_satisfied_by(target_version):
                    issues.append(
                        f"{dependent_id} requires {capability_id}{constraint}"
                    )
        
        return len(issues) == 0, issues
    
    def get_dependency_tree(self, capability_id: str, 
                           max_depth: int = 10) -> Dict:
        """Get hierarchical dependency tree."""
        def build_tree(cid: str, depth: int) -> Optional[Dict]:
            if depth > max_depth:
                return {"id": cid, "truncated": True}
            
            node = self._nodes.get(cid)
            if not node:
                return {"id": cid, "error": "Not found"}
            
            deps = []
            for dep_id, constraint in node.dependencies.items():
                dep_tree = build_tree(dep_id, depth + 1)
                if dep_tree:
                    dep_tree["constraint"] = str(constraint)
                    deps.append(dep_tree)
            
            return {
                "id": cid,
                "version": node.version,
                "dependencies": deps
            }
        
        return build_tree(capability_id, 0)


class PipDependencyResolver:
    """Resolves Python package dependencies."""
    
    @staticmethod
    def parse_requirements(requirements: List[str]) -> List[Requirement]:
        """Parse pip requirements."""
        parsed = []
        for req in requirements:
            try:
                parsed.append(Requirement(req))
            except Exception as e:
                logger.error(f"Failed to parse requirement {req}: {e}")
        return parsed
    
    @staticmethod
    def check_conflicts(requirements: List[str]) -> List[str]:
        """Check for version conflicts in requirements."""
        conflicts = []
        by_package: Dict[str, List[Requirement]] = defaultdict(list)
        
        for req_str in requirements:
            try:
                req = Requirement(req_str)
                by_package[req.name.lower()].append(req)
            except Exception:
                continue
        
        for pkg_name, reqs in by_package.items():
            if len(reqs) > 1:
                # Check if constraints are compatible
                for i, req1 in enumerate(reqs):
                    for req2 in reqs[i+1:]:
                        # Simplified conflict detection
                        if str(req1.specifier) != str(req2.specifier):
                            conflicts.append(
                                f"Potential conflict: {req1} vs {req2}"
                            )
        
        return conflicts
