import asyncio
import httpx
import time
import os
import random

# Configuration
BASE_URL = os.getenv("API_URL", "http://localhost:8000")
NUM_VPCS = int(os.getenv("NUM_VPCS", "500"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "50"))


async def create_vpc(client, idx):
    try:
        start = time.time()
        response = await client.post(
            f"{BASE_URL}/vpcs",
            json={
                "name": f"scale-vpc-{idx}",
                "cidr": f"10.{idx // 256}.{idx % 256}.0/24",
                "region": "us-east-1",
            },
        )
        duration = time.time() - start
        if response.status_code == 201:
            return True, duration
        else:
            return False, duration
    except Exception as e:
        return False, 0.0


async def main():
    print(f"Starting Load Simulator: {NUM_VPCS} VPCs, Concurrency {CONCURRENCY}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check health
        try:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code != 200:
                print("API not healthy. Exiting.")
                return
        except Exception:
            print(f"Could not connect to {BASE_URL}. Start the server first!")
            return

        tasks = []
        start_total = time.time()

        # Semaphore for concurrency control
        sem = asyncio.Semaphore(CONCURRENCY)

        async def worker(idx):
            async with sem:
                return await create_vpc(client, idx)

        for i in range(NUM_VPCS):
            tasks.append(worker(i))

        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_total
        success_count = sum(1 for r in results if r[0])
        fail_count = NUM_VPCS - success_count
        avg_latency = sum(r[1] for r in results) / NUM_VPCS if NUM_VPCS > 0 else 0

        print(f"\nSimulation Complete in {total_time:.2f}s")
        print(f"Success: {success_count}")
        print(f"Failed: {fail_count}")
        print(f"Avg Latency: {avg_latency*1000:.2f}ms")
        print(f"Throughput: {NUM_VPCS / total_time:.2f} req/s")


if __name__ == "__main__":
    asyncio.run(main())
