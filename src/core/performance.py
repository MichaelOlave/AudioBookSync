"""Performance monitoring and benchmarking utilities.

Provides tools for measuring query performance, resource usage, and comparing
ORM vs SQL implementations during Phase 6 validation.
"""

import asyncio
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import datetime
from statistics import mean, median, stdev
from typing import Any, Callable, Coroutine, Dict, List, Optional

from loguru import logger


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single operation."""

    operation_name: str
    duration_ms: float
    memory_bytes: int
    memory_delta_bytes: int
    success: bool
    error: Optional[str] = None
    query_count: Optional[int] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat() if self.timestamp else None
        return data


@dataclass
class BenchmarkResult:
    """Results from benchmark run."""

    name: str
    implementation: str  # "ORM" or "SQL"
    total_runs: int
    successful_runs: int
    failed_runs: int
    duration_ms_min: float
    duration_ms_max: float
    duration_ms_mean: float
    duration_ms_median: float
    duration_ms_stdev: Optional[float]
    memory_bytes_mean: float
    memory_delta_bytes_mean: float
    error_rate: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class PerformanceProfiler:
    """Profile performance of async functions."""

    def __init__(self, enable_memory_tracking: bool = True):
        """Initialize profiler.

        Args:
            enable_memory_tracking: Whether to track memory usage
        """
        self.enable_memory_tracking = enable_memory_tracking
        self.metrics: List[PerformanceMetrics] = []

    async def profile(
        self,
        func: Callable[..., Coroutine],
        *args,
        operation_name: str = "",
        **kwargs,
    ) -> tuple[Any, PerformanceMetrics]:
        """Profile an async function call.

        Args:
            func: Async function to profile
            *args: Positional arguments for function
            operation_name: Name for this operation
            **kwargs: Keyword arguments for function

        Returns:
            Tuple of (function_result, metrics)
        """
        if self.enable_memory_tracking:
            tracemalloc.start()
            snapshot_before = tracemalloc.take_snapshot()
            memory_before = sum(stat.size for stat in snapshot_before.statistics("lineno"))
        else:
            memory_before = 0

        operation_name = operation_name or func.__name__
        start_time = time.perf_counter()
        error = None
        result = None
        success = True

        try:
            result = await func(*args, **kwargs)
        except Exception as e:
            success = False
            error = str(e)
            logger.error(f"Profiling failed for {operation_name}: {e}")
            raise

        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            if self.enable_memory_tracking:
                snapshot_after = tracemalloc.take_snapshot()
                memory_after = sum(stat.size for stat in snapshot_after.statistics("lineno"))
                memory_delta_bytes = memory_after - memory_before
                tracemalloc.stop()
            else:
                memory_after = 0
                memory_delta_bytes = 0

            metrics = PerformanceMetrics(
                operation_name=operation_name,
                duration_ms=duration_ms,
                memory_bytes=memory_after,
                memory_delta_bytes=memory_delta_bytes,
                success=success,
                error=error,
                timestamp=datetime.now(),
            )

            self.metrics.append(metrics)

        return result, metrics

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all profiled operations.

        Returns:
            Dictionary with summary statistics
        """
        if not self.metrics:
            return {"total_operations": 0, "operations": {}}

        by_operation = {}
        for metric in self.metrics:
            if metric.operation_name not in by_operation:
                by_operation[metric.operation_name] = []
            by_operation[metric.operation_name].append(metric)

        summary = {"total_operations": len(self.metrics), "operations": {}}

        for op_name, metrics_list in by_operation.items():
            successful = [m for m in metrics_list if m.success]
            failed = [m for m in metrics_list if not m.success]

            if successful:
                durations = [m.duration_ms for m in successful]
                memory_deltas = [m.memory_delta_bytes for m in successful]

                summary["operations"][op_name] = {
                    "total_runs": len(metrics_list),
                    "successful_runs": len(successful),
                    "failed_runs": len(failed),
                    "duration_ms": {
                        "min": min(durations),
                        "max": max(durations),
                        "mean": mean(durations),
                        "median": median(durations),
                        "stdev": stdev(durations) if len(durations) > 1 else 0,
                    },
                    "memory_delta_bytes": {
                        "mean": mean(memory_deltas),
                        "max": max(memory_deltas),
                    },
                    "error_rate": len(failed) / len(metrics_list),
                }
            else:
                summary["operations"][op_name] = {
                    "total_runs": len(metrics_list),
                    "successful_runs": 0,
                    "failed_runs": len(failed),
                    "error_rate": 1.0,
                }

        return summary

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()


class BenchmarkComparison:
    """Compare performance between ORM and SQL implementations."""

    def __init__(self):
        """Initialize benchmark comparison."""
        self.results: Dict[str, List[BenchmarkResult]] = {}

    async def compare(
        self,
        test_name: str,
        orm_func: Callable[..., Coroutine],
        sql_func: Callable[..., Coroutine],
        iterations: int = 100,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """Compare ORM vs SQL performance.

        Args:
            test_name: Name of this benchmark
            orm_func: ORM implementation
            sql_func: SQL implementation
            iterations: Number of times to run each
            *args: Arguments for functions
            **kwargs: Keyword arguments for functions

        Returns:
            Comparison results
        """
        logger.info(f"Starting benchmark comparison: {test_name} ({iterations} iterations)")

        # Profile ORM
        orm_profiler = PerformanceProfiler()
        orm_results = []
        for i in range(iterations):
            try:
                _, metrics = await orm_profiler.profile(
                    orm_func,
                    *args,
                    operation_name=f"{test_name}_ORM_{i}",
                    **kwargs,
                )
                orm_results.append(metrics)
            except Exception as e:
                logger.error(f"ORM iteration {i} failed: {e}")

        # Profile SQL
        sql_profiler = PerformanceProfiler()
        sql_results = []
        for i in range(iterations):
            try:
                _, metrics = await sql_profiler.profile(
                    sql_func,
                    *args,
                    operation_name=f"{test_name}_SQL_{i}",
                    **kwargs,
                )
                sql_results.append(metrics)
            except Exception as e:
                logger.error(f"SQL iteration {i} failed: {e}")

        # Analyze results
        orm_profiler.get_summary()
        sql_profiler.get_summary()

        # Calculate overhead
        orm_mean = mean([m.duration_ms for m in orm_results if m.success])
        sql_mean = mean([m.duration_ms for m in sql_results if m.success])
        overhead_pct = ((orm_mean - sql_mean) / sql_mean) * 100 if sql_mean > 0 else 0

        comparison = {
            "test_name": test_name,
            "iterations": iterations,
            "orm": {
                "mean_duration_ms": orm_mean,
                "min_duration_ms": min(m.duration_ms for m in orm_results),
                "max_duration_ms": max(m.duration_ms for m in orm_results),
                "median_duration_ms": median(m.duration_ms for m in orm_results),
                "error_rate": len([m for m in orm_results if not m.success]) / len(orm_results),
                "memory_delta_bytes_mean": mean(
                    m.memory_delta_bytes for m in orm_results if m.success
                ),
            },
            "sql": {
                "mean_duration_ms": sql_mean,
                "min_duration_ms": min(m.duration_ms for m in sql_results),
                "max_duration_ms": max(m.duration_ms for m in sql_results),
                "median_duration_ms": median(m.duration_ms for m in sql_results),
                "error_rate": len([m for m in sql_results if not m.success]) / len(sql_results),
                "memory_delta_bytes_mean": mean(
                    m.memory_delta_bytes for m in sql_results if m.success
                ),
            },
            "overhead": {
                "percentage": overhead_pct,
                "duration_ms": orm_mean - sql_mean,
                "acceptable": overhead_pct <= 20,  # 20% is acceptable
            },
            "timestamp": datetime.now(),
        }

        # Store results
        if test_name not in self.results:
            self.results[test_name] = []
        self.results[test_name].append(comparison)

        logger.info(
            f"Benchmark complete: {test_name}. "
            f"ORM: {orm_mean:.2f}ms, SQL: {sql_mean:.2f}ms, "
            f"Overhead: {overhead_pct:.1f}%"
        )

        return comparison

    def get_report(self) -> Dict[str, Any]:
        """Generate performance report.

        Returns:
            Comprehensive performance report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": [],
            "summary": {
                "total_benchmarks": len(self.results),
                "acceptable_benchmarks": 0,
                "problematic_benchmarks": 0,
                "average_overhead": 0,
            },
        }

        total_overhead = 0
        for test_name, results_list in self.results.items():
            if results_list:
                latest = results_list[-1]
                benchmark_entry = {
                    "name": test_name,
                    "overhead_percentage": latest["overhead"]["percentage"],
                    "orm_duration_ms": latest["orm"]["mean_duration_ms"],
                    "sql_duration_ms": latest["sql"]["mean_duration_ms"],
                    "acceptable": latest["overhead"]["acceptable"],
                    "runs": len(results_list),
                }
                report["benchmarks"].append(benchmark_entry)

                if latest["overhead"]["acceptable"]:
                    report["summary"]["acceptable_benchmarks"] += 1
                else:
                    report["summary"]["problematic_benchmarks"] += 1

                total_overhead += latest["overhead"]["percentage"]

        if report["benchmarks"]:
            report["summary"]["average_overhead"] = total_overhead / len(report["benchmarks"])

        return report

    def reset(self) -> None:
        """Reset all benchmarks."""
        self.results.clear()


class LoadTester:
    """Test performance under load."""

    def __init__(self, target_rps: int = 100):
        """Initialize load tester.

        Args:
            target_rps: Target requests per second
        """
        self.target_rps = target_rps
        self.results = []

    async def run_load_test(
        self,
        test_name: str,
        func: Callable[..., Coroutine],
        duration_seconds: int = 60,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """Run load test for specified duration.

        Args:
            test_name: Name of test
            func: Function to load test
            duration_seconds: How long to run test
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Load test results
        """
        logger.info(
            f"Starting load test: {test_name} at {self.target_rps} RPS " f"for {duration_seconds}s"
        )

        request_interval = 1.0 / self.target_rps
        start_time = time.time()
        request_count = 0
        success_count = 0
        error_count = 0

        while time.time() - start_time < duration_seconds:
            request_start = time.perf_counter()

            try:
                await func(*args, **kwargs)
                success_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Request failed in load test: {e}")

            request_duration = time.perf_counter() - request_start
            request_count += 1

            # Throttle to target RPS
            sleep_time = request_interval - request_duration
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        elapsed_time = time.time() - start_time
        actual_rps = request_count / elapsed_time

        result = {
            "test_name": test_name,
            "duration_seconds": duration_seconds,
            "target_rps": self.target_rps,
            "actual_rps": actual_rps,
            "total_requests": request_count,
            "successful_requests": success_count,
            "failed_requests": error_count,
            "success_rate": success_count / request_count if request_count > 0 else 0,
            "timestamp": datetime.now(),
        }

        logger.info(
            f"Load test complete: {test_name}. "
            f"Target: {self.target_rps} RPS, Actual: {actual_rps:.1f} RPS, "
            f"Success rate: {result['success_rate'] * 100:.1f}%"
        )

        self.results.append(result)
        return result


# Global profiler instance
profiler = PerformanceProfiler()


def reset_profiler() -> None:
    """Reset global profiler."""
    profiler.reset()


def get_profiler_summary() -> Dict[str, Any]:
    """Get summary from global profiler."""
    return profiler.get_summary()
