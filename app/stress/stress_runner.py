import time
import socket
import asyncio
import httpx
from typing import Dict, Any, List

class HighThroughputStressRunner:
    async def run_stress_test(self, target_url: str, concurrency: int = 50, total_requests: int = 200) -> Dict[str, Any]:
        """
        Executes real-time high-throughput load generator using httpx.AsyncClient worker pools & semaphores.
        Calculates exact real-time RPS throughput, total duration, and exact p50/p90/p95/p99 latency percentiles over the wire.
        """
        start_time = time.perf_counter()
        latencies: List[float] = []
        successful_requests = 0
        failed_requests = 0

        req_count = min(total_requests, 1000)
        worker_limit = max(1, min(concurrency, 100))
        semaphore = asyncio.Semaphore(worker_limit)

        async def worker(client: httpx.AsyncClient):
            nonlocal successful_requests, failed_requests
            async with semaphore:
                t0 = time.perf_counter()
                try:
                    resp = await client.get(target_url, timeout=5.0)
                    t1 = time.perf_counter()
                    lat = (t1 - t0) * 1000.0
                    latencies.append(lat)
                    if resp.status_code < 400:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                except Exception:
                    t1 = time.perf_counter()
                    lat = round((t1 - t0) * 1000.0, 2)
                    latencies.append(lat)
                    failed_requests += 1

        try:
            async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
                tasks = [worker(client) for _ in range(req_count)]
                await asyncio.gather(*tasks)
        except Exception:
            pass

        total_time = max(0.001, time.perf_counter() - start_time)
        rps = round(req_count / total_time, 1)

        latencies.sort()
        if not latencies:
            latencies = [0.0]

        p50 = round(latencies[int(len(latencies) * 0.50)], 2)
        p90 = round(latencies[int(len(latencies) * 0.90)], 2)
        p95 = round(latencies[int(len(latencies) * 0.95)], 2)
        p99 = round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))], 2)

        return {
            "status": "STRESS_TEST_COMPLETE",
            "target_url": target_url,
            "concurrency_workers": worker_limit,
            "total_requests": req_count,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "requests_per_second": rps,
            "total_duration_sec": round(total_time, 2),
            "percentiles_ms": {
                "p50": p50,
                "p90": p90,
                "p95": p95,
                "p99": p99,
                "min": round(min(latencies), 2),
                "max": round(max(latencies), 2)
            }
        }

stress_runner_instance = HighThroughputStressRunner()
