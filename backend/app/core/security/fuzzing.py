"""
Automated Fuzz Testing Framework
Enterprise security fuzzing for API and input validation
"""
import random
import string
import asyncio
import logging
from typing import Optional, Dict, List, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import hashlib

logger = logging.getLogger(__name__)


class FuzzStrategy(Enum):
    """Fuzzing strategies"""
    RANDOM = "random"
    MUTATION = "mutation"
    GENERATION = "generation"
    GRAMMATICAL = "grammatical"
    PROTOCOL = "protocol"
    INTELLIGENT = "intelligent"


class FuzzTargetType(Enum):
    """Types of fuzzing targets"""
    API_ENDPOINT = "api_endpoint"
    FUNCTION = "function"
    PROTOCOL = "protocol"
    FILE_FORMAT = "file_format"
    DATABASE = "database"
    MESSAGE_QUEUE = "message_queue"


@dataclass
class FuzzInput:
    """Fuzz test input"""
    data: Any
    strategy: FuzzStrategy
    mutation_point: Optional[int] = None
    parent_input: Optional[str] = None
    generation_seed: Optional[int] = None


@dataclass
class FuzzResult:
    """Fuzz test result"""
    input_data: Any
    output_data: Any
    execution_time_ms: float
    exception: Optional[Exception] = None
    crash_type: Optional[str] = None
    is_crash: bool = False
    is_interesting: bool = False
    coverage_increase: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    response_code: Optional[int] = None


@dataclass
class CrashInfo:
    """Crash information"""
    crash_id: str
    input_hash: str
    exception_type: str
    exception_message: str
    stack_trace: str
    input_data: Any
    reproducible: bool = False
    severity: str = "medium"
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    occurrence_count: int = 1


class InputGenerator:
    """Generates fuzzing inputs"""
    
    def __init__(self):
        self._seed_corpus: List[Any] = []
        self._mutation_history: List[FuzzInput] = []
    
    def add_seed(self, seed: Any):
        """Add seed input to corpus"""
        self._seed_corpus.append(seed)
    
    def generate_random_string(self, min_len: int = 0, 
                               max_len: int = 1000,
                               charset: str = None) -> str:
        """Generate random string"""
        charset = charset or string.printable
        length = random.randint(min_len, max_len)
        return ''.join(random.choices(charset, k=length))
    
    def generate_random_bytes(self, min_len: int = 0,
                              max_len: int = 1000) -> bytes:
        """Generate random bytes"""
        length = random.randint(min_len, max_len)
        return bytes(random.randint(0, 255) for _ in range(length))
    
    def generate_random_json(self, depth: int = 3) -> Dict:
        """Generate random JSON object"""
        if depth <= 0:
            return random.choice([
                random.randint(-10000, 10000),
                self.generate_random_string(0, 50),
                random.random() > 0.5,
                None
            ])
        
        obj_type = random.choice(['dict', 'list', 'primitive'])
        
        if obj_type == 'dict':
            return {
                self.generate_random_string(1, 20): self.generate_random_json(depth - 1)
                for _ in range(random.randint(0, 10))
            }
        elif obj_type == 'list':
            return [
                self.generate_random_json(depth - 1)
                for _ in range(random.randint(0, 10))
            ]
        else:
            return self.generate_random_json(0)
    
    def mutate_string(self, original: str, 
                      mutation_count: int = 1) -> str:
        """Mutate string input"""
        result = list(original)
        
        for _ in range(mutation_count):
            mutation_type = random.choice([
                'bit_flip', 'byte_insert', 'byte_delete', 
                'byte_replace', 'boundary'
            ])
            
            if not result:
                break
            
            if mutation_type == 'bit_flip':
                idx = random.randint(0, len(result) - 1)
                char_val = ord(result[idx])
                bit_to_flip = random.randint(0, 7)
                result[idx] = chr(char_val ^ (1 << bit_to_flip))
            
            elif mutation_type == 'byte_insert':
                idx = random.randint(0, len(result))
                result.insert(idx, random.choice(string.printable))
            
            elif mutation_type == 'byte_delete':
                idx = random.randint(0, len(result) - 1)
                del result[idx]
            
            elif mutation_type == 'byte_replace':
                idx = random.randint(0, len(result) - 1)
                result[idx] = random.choice(string.printable)
            
            elif mutation_type == 'boundary':
                # Insert boundary values
                boundary = random.choice(['\x00', '\xff', '\x7f', '\x80'])
                idx = random.randint(0, len(result))
                result.insert(idx, boundary)
        
        return ''.join(result)
    
    def mutate_json(self, original: Dict) -> Dict:
        """Mutate JSON object"""
        result = json.loads(json.dumps(original))  # Deep copy
        
        # Randomly modify values
        def mutate_value(obj):
            if isinstance(obj, dict):
                key = random.choice(list(obj.keys())) if obj else None
                if key:
                    if random.random() > 0.5:
                        obj[key] = mutate_value(obj[key])
                    else:
                        # Add new key
                        obj[self.generate_random_string(5)] = self.generate_random_json(2)
            elif isinstance(obj, list):
                if obj and random.random() > 0.5:
                    idx = random.randint(0, len(obj) - 1)
                    obj[idx] = mutate_value(obj[idx])
                else:
                    obj.append(self.generate_random_json(2))
            elif isinstance(obj, str):
                return self.mutate_string(obj)
            elif isinstance(obj, (int, float)):
                return obj + random.randint(-100, 100)
            return obj
        
        return mutate_value(result)
    
    def generate_input(self, strategy: FuzzStrategy = None,
                       input_type: str = 'string') -> FuzzInput:
        """Generate fuzz input using specified strategy"""
        strategy = strategy or FuzzStrategy.RANDOM
        
        if strategy == FuzzStrategy.RANDOM:
            if input_type == 'string':
                data = self.generate_random_string()
            elif input_type == 'bytes':
                data = self.generate_random_bytes()
            elif input_type == 'json':
                data = self.generate_random_json()
            else:
                data = self.generate_random_string()
        
        elif strategy == FuzzStrategy.MUTATION:
            if self._seed_corpus:
                seed = random.choice(self._seed_corpus)
                if isinstance(seed, str):
                    data = self.mutate_string(seed)
                elif isinstance(seed, dict):
                    data = self.mutate_json(seed)
                else:
                    data = seed
            else:
                data = self.generate_random_string()
        
        else:
            data = self.generate_random_string()
        
        return FuzzInput(
            data=data,
            strategy=strategy
        )


class FuzzTarget:
    """Fuzzing target wrapper"""
    
    def __init__(self, 
                 target_func: Callable,
                 target_type: FuzzTargetType,
                 name: str = None):
        self.target_func = target_func
        self.target_type = target_type
        self.name = name or target_func.__name__
        self._execution_count = 0
        self._crash_count = 0
    
    async def execute(self, input_data: Any) -> FuzzResult:
        """Execute target with input"""
        import time
        
        start_time = time.time()
        self._execution_count += 1
        
        try:
            if asyncio.iscoroutinefunction(self.target_func):
                output = await self.target_func(input_data)
            else:
                output = self.target_func(input_data)
            
            execution_time = (time.time() - start_time) * 1000
            
            return FuzzResult(
                input_data=input_data,
                output_data=output,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self._crash_count += 1
            
            return FuzzResult(
                input_data=input_data,
                output_data=None,
                execution_time_ms=execution_time,
                exception=e,
                is_crash=True,
                crash_type=type(e).__name__
            )


class APITarget(FuzzTarget):
    """API endpoint fuzzing target"""
    
    def __init__(self, client, method: str, endpoint: str,
                 base_url: str = ""):
        self.client = client
        self.method = method
        self.endpoint = endpoint
        self.base_url = base_url
        
        async def target_func(data):
            url = f"{base_url}{endpoint}"
            if method.upper() == 'GET':
                return await client.get(url, params=data)
            elif method.upper() == 'POST':
                return await client.post(url, json=data)
            elif method.upper() == 'PUT':
                return await client.put(url, json=data)
            elif method.upper() == 'DELETE':
                return await client.delete(url, params=data)
        
        super().__init__(target_func, FuzzTargetType.API_ENDPOINT, 
                        f"{method}_{endpoint}")


class FuzzingEngine:
    """Main fuzzing engine"""
    
    def __init__(self):
        self._targets: Dict[str, FuzzTarget] = {}
        self._generator = InputGenerator()
        self._crashes: Dict[str, CrashInfo] = {}
        self._interesting_inputs: List[FuzzResult] = []
        self._coverage_data: Dict[str, set] = {}
        self._running = False
    
    def register_target(self, target: FuzzTarget):
        """Register fuzzing target"""
        self._targets[target.name] = target
        logger.info(f"Registered fuzz target: {target.name}")
    
    def add_seed_corpus(self, seeds: List[Any]):
        """Add seed corpus for mutation"""
        for seed in seeds:
            self._generator.add_seed(seed)
    
    async def fuzz_target(self, target_name: str,
                          iterations: int = 1000,
                          strategy: FuzzStrategy = FuzzStrategy.MUTATION,
                          input_type: str = 'json') -> Dict:
        """Run fuzzing campaign on target"""
        target = self._targets.get(target_name)
        if not target:
            raise ValueError(f"Target not found: {target_name}")
        
        self._running = True
        results = {
            'target': target_name,
            'iterations': iterations,
            'crashes': [],
            'interesting': [],
            'stats': {
                'executions': 0,
                'crashes': 0,
                'unique_crashes': 0
            }
        }
        
        for i in range(iterations):
            if not self._running:
                break
            
            # Generate input
            fuzz_input = self._generator.generate_input(strategy, input_type)
            
            # Execute target
            result = await target.execute(fuzz_input.data)
            results['stats']['executions'] += 1
            
            # Process result
            if result.is_crash:
                crash_info = self._process_crash(result)
                if crash_info:
                    results['crashes'].append(crash_info)
                    results['stats']['crashes'] += 1
                    
                    if crash_info.crash_id not in self._crashes:
                        results['stats']['unique_crashes'] += 1
            
            elif result.is_interesting:
                self._interesting_inputs.append(result)
                results['interesting'].append({
                    'input': fuzz_input.data,
                    'output': result.output_data
                })
            
            # Progress logging
            if (i + 1) % 100 == 0:
                logger.info(f"Fuzzing progress: {i + 1}/{iterations} iterations")
        
        self._running = False
        return results
    
    def _process_crash(self, result: FuzzResult) -> Optional[CrashInfo]:
        """Process crash and create crash info"""
        if not result.exception:
            return None
        
        # Create crash hash
        input_str = str(result.input_data)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
        
        crash_id = f"{result.crash_type}_{input_hash}"
        
        # Check if crash already known
        if crash_id in self._crashes:
            self._crashes[crash_id].occurrence_count += 1
            self._crashes[crash_id].last_seen = datetime.utcnow()
            return None
        
        # Create new crash info
        import traceback
        crash_info = CrashInfo(
            crash_id=crash_id,
            input_hash=input_hash,
            exception_type=type(result.exception).__name__,
            exception_message=str(result.exception),
            stack_trace=traceback.format_exc(),
            input_data=result.input_data,
            severity=self._classify_severity(result.exception)
        )
        
        self._crashes[crash_id] = crash_info
        
        logger.error(f"New crash found: {crash_id}")
        
        return crash_info
    
    def _classify_severity(self, exception: Exception) -> str:
        """Classify crash severity"""
        exception_type = type(exception).__name__
        
        critical_types = ['SQLInjection', 'CommandInjection', 'RCE', 'AuthenticationBypass']
        high_types = ['ValidationError', 'AuthorizationError', 'DataIntegrityError']
        
        if exception_type in critical_types:
            return 'critical'
        elif exception_type in high_types:
            return 'high'
        elif exception_type in ['ValueError', 'TypeError', 'KeyError']:
            return 'low'
        
        return 'medium'
    
    def stop(self):
        """Stop fuzzing"""
        self._running = False
    
    def get_crash_report(self) -> Dict:
        """Get crash report"""
        return {
            'total_crashes': sum(c.occurrence_count for c in self._crashes.values()),
            'unique_crashes': len(self._crashes),
            'crashes': [
                {
                    'id': c.crash_id,
                    'type': c.exception_type,
                    'severity': c.severity,
                    'occurrences': c.occurrence_count,
                    'first_seen': c.first_seen.isoformat(),
                    'last_seen': c.last_seen.isoformat()
                }
                for c in self._crashes.values()
            ]
        }


class CoverageTracker:
    """Tracks code coverage during fuzzing"""
    
    def __init__(self):
        self._coverage: Dict[str, set] = {}
        self._total_branches: Dict[str, int] = {}
    
    def record_coverage(self, function_name: str, branch_id: str):
        """Record coverage of a branch"""
        if function_name not in self._coverage:
            self._coverage[function_name] = set()
        
        self._coverage[function_name].add(branch_id)
    
    def get_coverage_stats(self) -> Dict:
        """Get coverage statistics"""
        stats = {
            'functions': {},
            'overall': {
                'total_functions': len(self._coverage),
                'total_branches_covered': 0,
                'average_coverage': 0.0
            }
        }
        
        total_coverage = 0
        for func, branches in self._coverage.items():
            total_branches = self._total_branches.get(func, len(branches))
            coverage_pct = (len(branches) / total_branches * 100) if total_branches > 0 else 0
            
            stats['functions'][func] = {
                'branches_covered': len(branches),
                'total_branches': total_branches,
                'coverage_percent': coverage_pct
            }
            
            total_coverage += coverage_pct
            stats['overall']['total_branches_covered'] += len(branches)
        
        if self._coverage:
            stats['overall']['average_coverage'] = total_coverage / len(self._coverage)
        
        return stats


# Global fuzzing engine
fuzzing_engine = FuzzingEngine()
coverage_tracker = CoverageTracker()