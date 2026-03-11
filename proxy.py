import asyncio
import time

PROXIES = [
    "192.168.1.34:2000",
    "192.168.1.34:2001",
]

TIMEOUT = 3
CONCURRENCY = 500

async def test_proxy(semaphore, proxy):
    ip, port = proxy.split(":")

    async with semaphore:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, int(port)),
                timeout=TIMEOUT
            )

            writer.close()
            await writer.wait_closed()

            print(f"[OK] {proxy}")
            return proxy

        except:
            print(f"[FAIL] {proxy}")
            return None


async def main():
    semaphore = asyncio.Semaphore(CONCURRENCY)

    start = time.time()

    tasks = [test_proxy(semaphore, proxy) for proxy in PROXIES]

    results = await asyncio.gather(*tasks)

    live = [p for p in results if p]

    print("\nDone")
    print("Live proxies:", len(live))
    print("Time:", round(time.time() - start, 2), "s")


asyncio.run(main())