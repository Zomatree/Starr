# from __future__ import annotations

from typing import Optional, TYPE_CHECKING
import revolt
from revolt.ext import commands
import asyncpg
from ..client import Client

class Config(commands.Cog):

    @commands.command()
    @commands.check(lambda ctx: bool(ctx.message.channel.server_id))
    async def prefix(self, ctx: commands.Context[Client], prefix: Optional[str] = None):
        if prefix is None:
            prefixes = await ctx.client.get_prefix(ctx.message)
            return await ctx.send(f"The server prefixes are {', '.join(prefixes)}")
        else:
            async with ctx.client.pool.acquire() as conn:
                conn: asyncpg.Connection
                async with conn.transaction():
                    await conn.execute("update server_configs set prefix=$1 where server_id=$2", prefix, ctx.server.id)
                    ctx.client.prefix_cache[ctx.server.id] = prefix

    @commands.command()
    @commands.check(lambda ctx: ctx.server.owner_id == ctx.author.id)
    @commands.check(lambda ctx: bool(ctx.message.channel.server_id))
    async def starboard(self, ctx: commands.Context[Client], channel: Optional[commands.ChannelConverter] = None):
        async with ctx.client.pool.acquire() as conn:
            conn: asyncpg.Connection
            async with conn.transaction():
                if channel is None:
                    starboard_channel = await conn.fetchval("select starboard_channel from server_configs where server_id=$1", ctx.server.id)
                    return await ctx.send(f"The starboard channel is {f'<#{starboard_channel}>' if starboard_channel else 'unset'}")

                if not isinstance(channel, revolt.TextChannel):
                    return await ctx.send("That channel isnt a text channel")

                await conn.execute("update server_configs set starboard_channel=$1 where server_id=$2", channel.id, ctx.server.id)

def setup(client: commands.CommandsClient):
    client.add_cog(Config())

def teardown(client: commands.CommandsClient):
    client.remove_cog("Config")
