import asyncio
from openbeers_api.client import OpenBeersClient

async def main() -> None:
    client = await OpenBeersClient.from_config()
    await client.prepare_basopra_input()
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())