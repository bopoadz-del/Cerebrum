"""
AutoML interface using Optuna and Ray Tune.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
from enum import Enum
import asyncio
import uuid


class AutoMLBackend(Enum):
    """Supported AutoML backends."""
    OPTUNA = "optuna"
    RAY_TUNE = "ray_tune"
    FLAML = "flaml"


class SearchAlgorithm(Enum):
    """Hyperparameter search algorithms."""
    RANDOM = "random"
    BAYESIAN = "bayesian"
    HYPERBAND = "hyperband"
    ASHA = "asha"
    POPULATION_BASED = "pbt"


@dataclass
class HyperparameterSpace:
    """Definition of hyperparameter search space."""
    name: str
    type: str  # float, int, categorical, loguniform
    low: Optional[float] = None
    high: Optional[float] = None
    choices: Optional[List[Any]] = None
    log_scale: bool = False
    
    def to_optuna(self) -> Dict[str, Any]:
        """Convert to Optuna format."""
        if self.type == "float":
            return {
                "type": "float",
                "low": self.low,
                "high": self.high,
                "log": self.log_scale
            }
        elif self.type == "int":
            return {
                "type": "int",
                "low": int(self.low) if self.low else None,
                "high": int(self.high) if self.high else None
            }
        elif self.type == "categorical":
            return {
                "type": "categorical",
                "choices": self.choices
            }
        return {}


@dataclass
class AutoMLConfig:
    """Configuration for AutoML run."""
    experiment_name: str
    backend: AutoMLBackend
    search_algorithm: SearchAlgorithm
    max_iterations: int = 100
    max_time_seconds: Optional[int] = None
    max_concurrent_trials: int = 4
    early_stopping_patience: int = 10
    metric: str = "val_loss"
    mode: str = "min"
    hyperparameter_space: Dict[str, HyperparameterSpace] = field(default_factory=dict)
    resource_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrialResult:
    """Result of a single trial."""
    trial_id: str
    config: Dict[str, Any]
    metrics: Dict[str, float]
    training_time_seconds: float
    resource_usage: Dict[str, Any]
    status: str = "completed"
    error_message: Optional[str] = None


@dataclass
class AutoMLRun:
    """Complete AutoML run results."""
    run_id: str
    config: AutoMLConfig
    start_time: datetime
    end_time: Optional[datetime] = None
    trials: List[TrialResult] = field(default_factory=list)
    best_trial: Optional[TrialResult] = None
    best_config: Optional[Dict[str, Any]] = None
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "running"


class AutoMLRunner:
    """Run automated machine learning experiments."""
    
    def __init__(self):
        self.active_runs: Dict[str, AutoMLRun] = {}
        self._backend_instances: Dict[AutoMLBackend, Any] = {}
    
    async def create_study(
        self,
        config: AutoMLConfig
    ) -> str:
        """Create a new AutoML study/run."""
        
        run_id = str(uuid.uuid4())
        
        run = AutoMLRun(
            run_id=run_id,
            config=config,
            start_time=datetime.utcnow()
        )
        
        self.active_runs[run_id] = run
        
        # Initialize backend
        await self._initialize_backend(config.backend)
        
        return run_id
    
    async def _initialize_backend(self, backend: AutoMLBackend):
        """Initialize AutoML backend."""
        
        if backend in self._backend_instances:
            return
        
        if backend == AutoMLBackend.OPTUNA:
            try:
                import optuna
                self._backend_instances[backend] = optuna
            except ImportError:
                raise RuntimeError("Optuna not installed")
        
        elif backend == AutoMLBackend.RAY_TUNE:
            try:
                from ray import tune
                self._backend_instances[backend] = tune
            except ImportError:
                raise RuntimeError("Ray Tune not installed")
    
    async def run_optimization(
        self,
        run_id: str,
        train_function: Callable[[Dict[str, Any]], Dict[str, float]],
        validation_data: Optional[Any] = None
    ) -> AutoMLRun:
        """Run hyperparameter optimization."""
        
        run = self.active_runs.get(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        if run.config.backend == AutoMLBackend.OPTUNA:
            return await self._run_optuna_optimization(run, train_function)
        elif run.config.backend == AutoMLBackend.RAY_TUNE:
            return await self._run_ray_tune_optimization(run, train_function)
        else:
            raise ValueError(f"Unsupported backend: {run.config.backend}")
    
    async def _run_optuna_optimization(
        self,
        run: AutoMLRun,
        train_function: Callable[[Dict[str, Any]], Dict[str, float]]
    ) -> AutoMLRun:
        """Run optimization using Optuna."""
        
        import optuna
        
        def objective(trial):
            # Sample hyperparameters
            params = {}
            for name, space in run.config.hyperparameter_space.items():
                if space.type == "float":
                    if space.log_scale:
                        params[name] = trial.suggest_float(
                            name, space.low, space.high, log=True
                        )
                    else:
                        params[name] = trial.suggest_float(
                            name, space.low, space.high
                        )
                elif space.type == "int":
                    params[name] = trial.suggest_int(
                        name, int(space.low), int(space.high)
                    )
                elif space.type == "categorical":
                    params[name] = trial.suggest_categorical(name, space.choices)
            
            # Train model
            start_time = datetime.utcnow()
            metrics = train_function(params)
            training_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Record trial
            trial_result = TrialResult(
                trial_id=str(trial.number),
                config=params,
                metrics=metrics,
                training_time_seconds=training_time,
                resource_usage={}
            )
            run.trials.append(trial_result)
            
            # Update optimization history
            run.optimization_history.append({
                "trial": trial.number,
                "metric": metrics.get(run.config.metric, 0),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return metrics.get(run.config.metric, 0)
        
        # Create study
        direction = "minimize" if run.config.mode == "min" else "maximize"
        study = optuna.create_study(direction=direction)
        
        # Run optimization
        study.optimize(
            objective,
            n_trials=run.config.max_iterations,
            timeout=run.config.max_time_seconds,
            n_jobs=run.config.max_concurrent_trials
        )
        
        # Update run with results
        run.best_config = study.best_params
        run.best_trial = next(
            (t for t in run.trials if t.config == study.best_params),
            None
        )
        run.status = "completed"
        run.end_time = datetime.utcnow()
        
        return run
    
    async def _run_ray_tune_optimization(
        self,
        run: AutoMLRun,
        train_function: Callable[[Dict[str, Any]], Dict[str, float]]
    ) -> AutoMLRun:
        """Run optimization using Ray Tune."""
        
        from ray import tune
        from ray.tune.schedulers import ASHAScheduler
        
        # Convert hyperparameter space
        search_space = {}
        for name, space in run.config.hyperparameter_space.items():
            if space.type == "float":
                if space.log_scale:
                    search_space[name] = tune.loguniform(space.low, space.high)
                else:
                    search_space[name] = tune.uniform(space.low, space.high)
            elif space.type == "int":
                search_space[name] = tune.randint(int(space.low), int(space.high))
            elif space.type == "categorical":
                search_space[name] = tune.choice(space.choices)
        
        # Define training function wrapper
        def train_wrapper(config):
            metrics = train_function(config)
            tune.report(**metrics)
        
        # Setup scheduler for early stopping
        scheduler = ASHAScheduler(
            metric=run.config.metric,
            mode=run.config.mode,
            max_t=run.config.max_iterations,
            grace_period=run.config.early_stopping_patience
        )
        
        # Run tuning
        analysis = tune.run(
            train_wrapper,
            config=search_space,
            num_samples=run.config.max_iterations,
            scheduler=scheduler,
            time_budget_s=run.config.max_time_seconds,
            verbose=1
        )
        
        # Update run with results
        run.best_config = analysis.best_config
        run.status = "completed"
        run.end_time = datetime.utcnow()
        
        return run
    
    async def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """Get current status of AutoML run."""
        
        run = self.active_runs.get(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        return {
            "run_id": run_id,
            "status": run.status,
            "experiment_name": run.config.experiment_name,
            "backend": run.config.backend.value,
            "trials_completed": len(run.trials),
            "max_iterations": run.config.max_iterations,
            "best_metric": run.best_trial.metrics.get(run.config.metric) if run.best_trial else None,
            "start_time": run.start_time.isoformat(),
            "end_time": run.end_time.isoformat() if run.end_time else None,
            "elapsed_seconds": (
                datetime.utcnow() - run.start_time
            ).total_seconds() if run.status == "running" else None
        }
    
    async def stop_run(self, run_id: str) -> bool:
        """Stop an active AutoML run."""
        
        run = self.active_runs.get(run_id)
        if not run:
            return False
        
        run.status = "stopped"
        run.end_time = datetime.utcnow()
        
        return True
    
    async def get_best_config(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get best configuration from completed run."""
        
        run = self.active_runs.get(run_id)
        if not run:
            return None
        
        return run.best_config
    
    async def export_results(
        self,
        run_id: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export AutoML results."""
        
        run = self.active_runs.get(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        return {
            "run_id": run_id,
            "config": {
                "experiment_name": run.config.experiment_name,
                "backend": run.config.backend.value,
                "search_algorithm": run.config.search_algorithm.value,
                "max_iterations": run.config.max_iterations,
                "metric": run.config.metric,
                "mode": run.config.mode
            },
            "results": {
                "best_config": run.best_config,
                "best_metrics": run.best_trial.metrics if run.best_trial else None,
                "all_trials": [
                    {
                        "trial_id": t.trial_id,
                        "config": t.config,
                        "metrics": t.metrics,
                        "training_time": t.training_time_seconds
                    }
                    for t in run.trials
                ]
            },
            "optimization_history": run.optimization_history
        }
