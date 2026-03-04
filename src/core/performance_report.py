"""Performance report generation and analysis.

Generates detailed performance reports from benchmark results, including
optimization recommendations and regression detection.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class PerformanceBaseline:
    """Performance baseline for a specific operation."""

    operation_name: str
    duration_ms: float
    acceptable_overhead_pct: float
    regression_threshold_pct: float = 15.0  # Alert if slower than baseline + 15%


class PerformanceReport:
    """Generate and manage performance reports."""

    def __init__(self):
        """Initialize report generator."""
        self.benchmarks: Dict[str, List[Dict[str, Any]]] = {}
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self.regressions: List[Dict[str, Any]] = []

    def add_benchmark(self, test_name: str, result: Dict[str, Any]) -> None:
        """Add benchmark result to report.

        Args:
            test_name: Name of test
            result: Benchmark result from BenchmarkComparison
        """
        if test_name not in self.benchmarks:
            self.benchmarks[test_name] = []
        self.benchmarks[test_name].append(result)

    def set_baseline(self, operation_name: str, baseline: PerformanceBaseline) -> None:
        """Set performance baseline for operation.

        Args:
            operation_name: Name of operation
            baseline: Performance baseline
        """
        self.baselines[operation_name] = baseline

    def check_regression(self, test_name: str, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if result represents regression.

        Args:
            test_name: Name of test
            result: Benchmark result

        Returns:
            Regression details if detected, None otherwise
        """
        if test_name not in self.baselines:
            return None

        baseline = self.baselines[test_name]
        orm_duration = result["orm"]["mean_duration_ms"]
        regression_threshold = baseline.duration_ms * (1 + baseline.regression_threshold_pct / 100)

        if orm_duration > regression_threshold:
            regression = {
                "test_name": test_name,
                "baseline_ms": baseline.duration_ms,
                "current_ms": orm_duration,
                "regression_pct": ((orm_duration - baseline.duration_ms) / baseline.duration_ms)
                * 100,
                "threshold_ms": regression_threshold,
                "timestamp": datetime.now(),
            }
            self.regressions.append(regression)
            logger.warning(f"Performance regression detected: {test_name}")
            return regression

        return None

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report.

        Returns:
            Detailed performance report
        """
        report: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_benchmarks": len(self.benchmarks),
                "total_tests": sum(len(v) for v in self.benchmarks.values()),
                "regressions_detected": len(self.regressions),
                "benchmarks_within_acceptable": 0,
                "benchmarks_over_threshold": 0,
            },
            "benchmarks": [],
            "regressions": self.regressions,
            "recommendations": [],
        }

        # Analyze each benchmark
        for test_name, results_list in self.benchmarks.items():
            if not results_list:
                continue

            latest_result = results_list[-1]
            benchmark_entry = {
                "name": test_name,
                "overhead_percentage": latest_result["overhead"]["percentage"],
                "orm_duration_ms": latest_result["orm"]["mean_duration_ms"],
                "sql_duration_ms": latest_result["sql"]["mean_duration_ms"],
                "orm_error_rate": latest_result["orm"]["error_rate"],
                "sql_error_rate": latest_result["sql"]["error_rate"],
                "orm_memory_bytes": latest_result["orm"]["memory_delta_bytes_mean"],
                "sql_memory_bytes": latest_result["sql"]["memory_delta_bytes_mean"],
                "acceptable": latest_result["overhead"]["acceptable"],
                "run_count": len(results_list),
            }

            # Get baseline if exists
            if test_name in self.baselines:
                baseline = self.baselines[test_name]
                benchmark_entry["baseline_ms"] = baseline.duration_ms
                benchmark_entry["acceptable_overhead"] = baseline.acceptable_overhead_pct

            report["benchmarks"].append(benchmark_entry)

            # Update counters
            if latest_result["overhead"]["acceptable"]:
                report["summary"]["benchmarks_within_acceptable"] += 1
            else:
                report["summary"]["benchmarks_over_threshold"] += 1

        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(report["benchmarks"])

        return report

    def generate_html_report(self, output_path: str = "performance_report.html") -> str:
        """Generate HTML performance report.

        Args:
            output_path: Path to write HTML report

        Returns:
            Path to generated report
        """
        report = self.generate_report()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
                .summary-card {{ background: #e8f4f8; padding: 15px; border-radius: 5px; border-left: 4px solid #0066cc; }}
                .summary-card.warning {{ background: #fff3cd; border-left-color: #ff9800; }}
                .summary-card.error {{ background: #f8d7da; border-left-color: #d32f2f; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #f0f0f0; font-weight: bold; }}
                tr:hover {{ background: #f5f5f5; }}
                .good {{ color: green; font-weight: bold; }}
                .warning {{ color: orange; font-weight: bold; }}
                .error {{ color: red; font-weight: bold; }}
                .recommendations {{ background: #f9f9f9; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .recommendation {{ margin: 10px 0; padding: 10px; background: white; border-left: 4px solid #0066cc; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Performance Validation Report</h1>
                <p>Generated: {report['timestamp']}</p>
            </div>

            <div class="summary">
                <div class="summary-card">
                    <h3>{report['summary']['total_tests']}</h3>
                    <p>Total Tests Run</p>
                </div>
                <div class="summary-card">
                    <h3>{report['summary']['benchmarks_within_acceptable']}</h3>
                    <p>Within Acceptable Range</p>
                </div>
                <div class="summary-card {'error' if report['summary']['benchmarks_over_threshold'] > 0 else ''}">
                    <h3>{report['summary']['benchmarks_over_threshold']}</h3>
                    <p>Over Threshold</p>
                </div>
                <div class="summary-card {'error' if report['summary']['regressions_detected'] > 0 else ''}">
                    <h3>{report['summary']['regressions_detected']}</h3>
                    <p>Regressions Detected</p>
                </div>
            </div>

            <h2>Benchmark Results</h2>
            <table>
                <tr>
                    <th>Test Name</th>
                    <th>ORM Duration (ms)</th>
                    <th>SQL Duration (ms)</th>
                    <th>Overhead (%)</th>
                    <th>Status</th>
                </tr>
                {''.join([f'''
                <tr>
                    <td>{b['name']}</td>
                    <td>{b['orm_duration_ms']:.2f}</td>
                    <td>{b['sql_duration_ms']:.2f}</td>
                    <td>{b['overhead_percentage']:.1f}%</td>
                    <td><span class="{'good' if b['acceptable'] else 'error'}">
                        {'✓ ACCEPTABLE' if b['acceptable'] else '✗ OVER THRESHOLD'}
                    </span></td>
                </tr>
                ''' for b in report['benchmarks']])}
            </table>

            {'<h2>Regressions Detected</h2>' + '<table>' + '<tr><th>Test</th><th>Baseline</th><th>Current</th><th>Regression %</th></tr>' + ''.join([f'<tr><td>{r["test_name"]}</td><td>{r["baseline_ms"]:.2f}ms</td><td>{r["current_ms"]:.2f}ms</td><td>{r["regression_pct"]:.1f}%</td></tr>' for r in report['regressions']]) + '</table>' if report['regressions'] else ''}

            <div class="recommendations">
                <h2>Optimization Recommendations</h2>
                {''.join([f'<div class="recommendation">{rec}</div>' for rec in report['recommendations']])}
            </div>
        </body>
        </html>
        """

        with open(output_path, "w") as f:
            f.write(html)

        logger.info(f"HTML report generated: {output_path}")
        return output_path

    def generate_json_report(self, output_path: str = "performance_report.json") -> str:
        """Generate JSON performance report.

        Args:
            output_path: Path to write JSON report

        Returns:
            Path to generated report
        """
        report = self.generate_report()

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"JSON report generated: {output_path}")
        return output_path

    def _generate_recommendations(self, benchmarks: List[Dict[str, Any]]) -> List[str]:
        """Generate optimization recommendations.

        Args:
            benchmarks: Benchmark results

        Returns:
            List of recommendations
        """
        recommendations = []

        for benchmark in benchmarks:
            overhead = benchmark["overhead_percentage"]

            if overhead > 50:
                recommendations.append(
                    f"🔴 CRITICAL: {benchmark['name']} has {overhead:.1f}% overhead. "
                    f"Investigate N+1 queries or missing indexes."
                )
            elif overhead > 25:
                recommendations.append(
                    f"⚠️ WARNING: {benchmark['name']} has {overhead:.1f}% overhead. "
                    f"Consider query optimization or batch loading."
                )
            elif overhead > 15:
                recommendations.append(
                    f"ℹ️ INFO: {benchmark['name']} has {overhead:.1f}% overhead. "
                    f"Monitor for regressions but acceptable for now."
                )

            # Memory analysis
            if benchmark.get("orm_memory_bytes", 0) > benchmark.get("sql_memory_bytes", 0) * 2:
                recommendations.append(
                    f"Memory: {benchmark['name']} uses {benchmark['orm_memory_bytes'] / 1024:.1f}KB. "
                    f"Consider caching or lazy loading."
                )

            # Error rate analysis
            if benchmark.get("orm_error_rate", 0) > 0.01:
                recommendations.append(
                    f"Errors: {benchmark['name']} ORM error rate is "
                    f"{benchmark['orm_error_rate'] * 100:.2f}%. Investigate failures."
                )

        if not recommendations:
            recommendations.append(
                "✓ All benchmarks within acceptable thresholds. No optimizations needed."
            )

        return recommendations
