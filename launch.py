import starr
import asyncio
import revolt
import logging

logging.basicConfig(level=logging.DEBUG)

async def main():
    async with revolt.utils.client_session() as session:
        client = await starr.Client.from_config(session, "config.toml")
        await client.start()

asyncio.run(main())
