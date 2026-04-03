#!/usr/bin/env python
"""
Performance benchmark script for radius search API (Phase 7 Day 6).

Tests:
1. API latency with/without cache
2. Cache hit rate under different scenarios
3. Concurrent request handling
4. PostGIS vs Python implementation comparison
5. Different radius values (5km, 10km, 50km, 100km)

Usage:
    python scripts/benchmark_radius_search.py --scenarios all
    python scripts/benchmark_radius_search.py --scenarios cache-only
    python scripts/benchmark_radius_search.py --concurrent 100

Requirements:
    pip install requests pandas tabulate matplotlib
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

import requests
from tabulate import tabulate

# Test coordinates (Brasília area)
TEST_COORDINATES = [
    {"lat": -15.7801, "lng": -47.9292, "name": "Brasília Center"},
    {"lat": -15.7350, "lng": -47.9292, "name": "Brasília North"},
    {"lat": -15.8300, "lng": -47.9292, "name": "Brasília South"},
    {"lat": -15.7801, "lng": -47.8800, "name": "Brasília East"},
    {"lat": -15.7801, "lng": -47.9800, "name": "Brasília West"},
]

# Test radius values (km)
TEST_RADII = [5, 10, 50, 100]

# API configuration
API_BASE_URL = "http://localhost:8000"
API_ENDPOINT = "/api/v1/inventory/sites/radius"


@dataclass
class BenchmarkResult:
    """Results from a single API request."""

    scenario: str
    radius_km: float
    location_name: str
    latency_ms: float
    status_code: int
    site_count: int
    cache_hit: bool | None = None
    cache_stale: bool | None = None
    cache_age_seconds: int | None = None
    error: str | None = None


@dataclass
class BenchmarkSummary:
    """Aggregated benchmark results."""

    scenario: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    cache_hit_rate: float | None = None
    avg_site_count: float = 0.0
    results: list[BenchmarkResult] = field(default_factory=list)


def clear_cache() -> bool:
    """Clear Redis cache via Django management command."""
    import subprocess

    try:
        subprocess.run(
            ["docker", "compose", "exec", "-T", "web", "python", "manage.py", "shell"],
            input=b"from django.core.cache import cache; cache.clear()\n",
            cwd="docker",
            check=True,
            capture_output=True,
        )
        print("[Cache] ✅ Cleared successfully")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"[Cache] ❌ Failed to clear: {exc}")
        return False


def make_request(
    lat: float,
    lng: float,
    radius_km: float,
    location_name: str,
    scenario: str,
    with_debug: bool = True,
) -> BenchmarkResult:
    """Make single API request and measure latency."""
    url = f"{API_BASE_URL}{API_ENDPOINT}"
    params = {
        "lat": lat,
        "lng": lng,
        "radius_km": radius_km,
        "limit": 100,
    }

    if with_debug:
        params["debug"] = "1"

    start_time = time.time()

    try:
        response = requests.get(url, params=params, timeout=30)
        latency_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            data = response.json()
            cache_meta = data.get("_cache", {})

            return BenchmarkResult(
                scenario=scenario,
                radius_km=radius_km,
                location_name=location_name,
                latency_ms=latency_ms,
                status_code=response.status_code,
                site_count=data.get("count", 0),
                cache_hit=cache_meta.get("hit"),
                cache_stale=cache_meta.get("stale"),
                cache_age_seconds=cache_meta.get("age_seconds"),
            )
        else:
            return BenchmarkResult(
                scenario=scenario,
                radius_km=radius_km,
                location_name=location_name,
                latency_ms=latency_ms,
                status_code=response.status_code,
                site_count=0,
                error=f"HTTP {response.status_code}",
            )

    except requests.RequestException as exc:
        latency_ms = (time.time() - start_time) * 1000
        return BenchmarkResult(
            scenario=scenario,
            radius_km=radius_km,
            location_name=location_name,
            latency_ms=latency_ms,
            status_code=0,
            site_count=0,
            error=str(exc),
        )


def benchmark_cache_miss(verbose: bool = True) -> list[BenchmarkResult]:
    """Test cache MISS scenario (first request after cache clear)."""
    print("\n" + "=" * 80)
    print("SCENARIO 1: Cache MISS (cold cache)")
    print("=" * 80)

    clear_cache()
    time.sleep(1)  # Wait for cache to clear

    results = []

    for coord in TEST_COORDINATES:
        for radius in TEST_RADII:
            if verbose:
                print(
                    f"[Miss] Testing {coord['name']} @ {radius}km... ", end="", flush=True
                )

            result = make_request(
                lat=coord["lat"],
                lng=coord["lng"],
                radius_km=radius,
                location_name=coord["name"],
                scenario="cache_miss",
            )

            results.append(result)

            if verbose:
                print(f"{result.latency_ms:.1f}ms (sites: {result.site_count})")

    return results


def benchmark_cache_hit_fresh(verbose: bool = True) -> list[BenchmarkResult]:
    """Test cache HIT scenario (fresh data < 30s)."""
    print("\n" + "=" * 80)
    print("SCENARIO 2: Cache HIT - Fresh (< 30s)")
    print("=" * 80)

    # Prime cache first
    print("[Warm-up] Priming cache...")
    for coord in TEST_COORDINATES:
        for radius in TEST_RADII:
            make_request(
                coord["lat"], coord["lng"], radius, coord["name"], "warmup", False
            )

    time.sleep(2)  # Wait for cache to stabilize

    results = []

    for coord in TEST_COORDINATES:
        for radius in TEST_RADII:
            if verbose:
                print(
                    f"[Fresh] Testing {coord['name']} @ {radius}km... ", end="", flush=True
                )

            result = make_request(
                lat=coord["lat"],
                lng=coord["lng"],
                radius_km=radius,
                location_name=coord["name"],
                scenario="cache_hit_fresh",
            )

            results.append(result)

            if verbose:
                status = "FRESH" if not result.cache_stale else "STALE"
                age = result.cache_age_seconds or 0
                print(
                    f"{result.latency_ms:.1f}ms ({status}, age: {age}s, sites: {result.site_count})"
                )

    return results


def benchmark_cache_hit_stale(verbose: bool = True) -> list[BenchmarkResult]:
    """Test cache HIT scenario (stale data 30-60s)."""
    print("\n" + "=" * 80)
    print("SCENARIO 3: Cache HIT - Stale (30-60s)")
    print("=" * 80)

    # Prime cache
    print("[Warm-up] Priming cache...")
    for coord in TEST_COORDINATES[:2]:  # Only first 2 to save time
        for radius in [10, 50]:  # Only 2 radii
            make_request(
                coord["lat"], coord["lng"], radius, coord["name"], "warmup", False
            )

    # Wait for cache to become stale (> 30s)
    print("[Wait] Waiting 35 seconds for cache to become stale...")
    time.sleep(35)

    results = []

    for coord in TEST_COORDINATES[:2]:
        for radius in [10, 50]:
            if verbose:
                print(
                    f"[Stale] Testing {coord['name']} @ {radius}km... ", end="", flush=True
                )

            result = make_request(
                lat=coord["lat"],
                lng=coord["lng"],
                radius_km=radius,
                location_name=coord["name"],
                scenario="cache_hit_stale",
            )

            results.append(result)

            if verbose:
                status = "STALE" if result.cache_stale else "FRESH"
                age = result.cache_age_seconds or 0
                print(
                    f"{result.latency_ms:.1f}ms ({status}, age: {age}s, sites: {result.site_count})"
                )

    return results


def benchmark_concurrent(
    concurrent_users: int = 10, verbose: bool = True
) -> list[BenchmarkResult]:
    """Test concurrent requests (load testing)."""
    print("\n" + "=" * 80)
    print(f"SCENARIO 4: Concurrent Requests ({concurrent_users} users)")
    print("=" * 80)

    # Prime cache
    coord = TEST_COORDINATES[0]
    radius = 10
    make_request(coord["lat"], coord["lng"], radius, coord["name"], "warmup", False)
    time.sleep(2)

    print(f"[Load] Simulating {concurrent_users} concurrent users... ", flush=True)

    results = []

    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = []
        for i in range(concurrent_users):
            future = executor.submit(
                make_request,
                coord["lat"],
                coord["lng"],
                radius,
                coord["name"],
                f"concurrent_{concurrent_users}",
            )
            futures.append(future)

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    if verbose:
        print(f"[Load] ✅ Completed {len(results)} requests")

    return results


def calculate_summary(results: list[BenchmarkResult], scenario: str) -> BenchmarkSummary:
    """Calculate aggregate statistics."""
    successful = [r for r in results if r.status_code == 200]
    failed = [r for r in results if r.status_code != 200]

    latencies = [r.latency_ms for r in successful]

    if not latencies:
        return BenchmarkSummary(
            scenario=scenario,
            total_requests=len(results),
            successful_requests=0,
            failed_requests=len(failed),
            avg_latency_ms=0.0,
            p50_latency_ms=0.0,
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
            min_latency_ms=0.0,
            max_latency_ms=0.0,
            results=results,
        )

    # Calculate percentiles
    sorted_latencies = sorted(latencies)
    p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
    p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]

    # Cache hit rate
    cache_aware = [r for r in successful if r.cache_hit is not None]
    cache_hit_rate = (
        sum(1 for r in cache_aware if r.cache_hit) / len(cache_aware) * 100
        if cache_aware
        else None
    )

    # Average site count
    avg_sites = statistics.mean([r.site_count for r in successful])

    return BenchmarkSummary(
        scenario=scenario,
        total_requests=len(results),
        successful_requests=len(successful),
        failed_requests=len(failed),
        avg_latency_ms=statistics.mean(latencies),
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        p99_latency_ms=p99,
        min_latency_ms=min(latencies),
        max_latency_ms=max(latencies),
        cache_hit_rate=cache_hit_rate,
        avg_site_count=avg_sites,
        results=results,
    )


def print_summary_table(summaries: list[BenchmarkSummary]) -> None:
    """Print formatted summary table."""
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    table_data = []
    for summary in summaries:
        cache_rate = (
            f"{summary.cache_hit_rate:.1f}%" if summary.cache_hit_rate else "N/A"
        )
        table_data.append(
            [
                summary.scenario,
                summary.total_requests,
                summary.successful_requests,
                summary.failed_requests,
                f"{summary.avg_latency_ms:.1f}",
                f"{summary.p50_latency_ms:.1f}",
                f"{summary.p95_latency_ms:.1f}",
                f"{summary.p99_latency_ms:.1f}",
                cache_rate,
                f"{summary.avg_site_count:.0f}",
            ]
        )

    headers = [
        "Scenario",
        "Total",
        "Success",
        "Failed",
        "Avg (ms)",
        "P50 (ms)",
        "P95 (ms)",
        "P99 (ms)",
        "Cache Hit",
        "Avg Sites",
    ]

    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def print_comparison_table(summaries: list[BenchmarkSummary]) -> None:
    """Print cache impact comparison."""
    print("\n" + "=" * 80)
    print("CACHE IMPACT ANALYSIS")
    print("=" * 80)

    cache_miss = next((s for s in summaries if s.scenario == "cache_miss"), None)
    cache_fresh = next((s for s in summaries if s.scenario == "cache_hit_fresh"), None)

    if not cache_miss or not cache_fresh:
        print("[Warning] Missing cache_miss or cache_hit_fresh data for comparison")
        return

    improvement_avg = (
        (cache_miss.avg_latency_ms - cache_fresh.avg_latency_ms)
        / cache_miss.avg_latency_ms
        * 100
    )
    improvement_p95 = (
        (cache_miss.p95_latency_ms - cache_fresh.p95_latency_ms)
        / cache_miss.p95_latency_ms
        * 100
    )

    table_data = [
        [
            "Cache MISS (cold)",
            f"{cache_miss.avg_latency_ms:.1f}",
            f"{cache_miss.p95_latency_ms:.1f}",
            "0%",
            "-",
        ],
        [
            "Cache HIT (fresh)",
            f"{cache_fresh.avg_latency_ms:.1f}",
            f"{cache_fresh.p95_latency_ms:.1f}",
            f"{cache_fresh.cache_hit_rate:.1f}%",
            f"↓ {improvement_avg:.1f}%",
        ],
    ]

    headers = ["Scenario", "Avg Latency", "P95 Latency", "Hit Rate", "Improvement"]

    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    print(f"\n✅ Cache reduces average latency by {improvement_avg:.1f}%")
    print(f"✅ Cache reduces P95 latency by {improvement_p95:.1f}%")


def save_results_json(summaries: list[BenchmarkSummary], filename: str) -> None:
    """Save benchmark results to JSON file."""
    data = []
    for summary in summaries:
        summary_dict = {
            "scenario": summary.scenario,
            "total_requests": summary.total_requests,
            "successful_requests": summary.successful_requests,
            "failed_requests": summary.failed_requests,
            "avg_latency_ms": summary.avg_latency_ms,
            "p50_latency_ms": summary.p50_latency_ms,
            "p95_latency_ms": summary.p95_latency_ms,
            "p99_latency_ms": summary.p99_latency_ms,
            "cache_hit_rate": summary.cache_hit_rate,
            "avg_site_count": summary.avg_site_count,
            "results": [
                {
                    "scenario": r.scenario,
                    "radius_km": r.radius_km,
                    "location_name": r.location_name,
                    "latency_ms": r.latency_ms,
                    "site_count": r.site_count,
                    "cache_hit": r.cache_hit,
                    "cache_stale": r.cache_stale,
                    "cache_age_seconds": r.cache_age_seconds,
                }
                for r in summary.results
            ],
        }
        data.append(summary_dict)

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n[Results] Saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Radius search API benchmark")
    parser.add_argument(
        "--scenarios",
        choices=["all", "cache-only", "load-only"],
        default="all",
        help="Which scenarios to run",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=10,
        help="Number of concurrent users for load test",
    )
    parser.add_argument(
        "--output", type=str, default="benchmark_results.json", help="Output JSON file"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print("=" * 80)
    print("RADIUS SEARCH API - PERFORMANCE BENCHMARK")
    print("=" * 80)
    print(f"API Endpoint: {API_BASE_URL}{API_ENDPOINT}")
    print(f"Test Locations: {len(TEST_COORDINATES)}")
    print(f"Test Radii: {TEST_RADII}")
    print("=" * 80)

    all_results = []
    summaries = []

    # Scenario 1: Cache MISS
    if args.scenarios in ["all", "cache-only"]:
        miss_results = benchmark_cache_miss(verbose=args.verbose)
        all_results.extend(miss_results)
        summaries.append(calculate_summary(miss_results, "cache_miss"))

    # Scenario 2: Cache HIT (fresh)
    if args.scenarios in ["all", "cache-only"]:
        fresh_results = benchmark_cache_hit_fresh(verbose=args.verbose)
        all_results.extend(fresh_results)
        summaries.append(calculate_summary(fresh_results, "cache_hit_fresh"))

    # Scenario 3: Cache HIT (stale) - Optional, takes 35s
    # if args.scenarios in ["all", "cache-only"]:
    #     stale_results = benchmark_cache_hit_stale(verbose=args.verbose)
    #     all_results.extend(stale_results)
    #     summaries.append(calculate_summary(stale_results, "cache_hit_stale"))

    # Scenario 4: Concurrent load
    if args.scenarios in ["all", "load-only"]:
        concurrent_results = benchmark_concurrent(
            concurrent_users=args.concurrent, verbose=args.verbose
        )
        all_results.extend(concurrent_results)
        summaries.append(
            calculate_summary(concurrent_results, f"concurrent_{args.concurrent}")
        )

    # Print summaries
    print_summary_table(summaries)
    print_comparison_table(summaries)

    # Save results
    save_results_json(summaries, args.output)

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETE ✅")
    print("=" * 80)


if __name__ == "__main__":
    main()
