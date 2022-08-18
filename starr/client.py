from typing import Any, Optional, cast
from typing_extensions import Self
import revolt
from revolt.ext import commands
import toml
import aiohttp
import asyncpg

class Client(commands.CommandsClient):
    def __init__(self, session: aiohttp.ClientSession, config: dict[str, Any], pool: asyncpg.Pool):
        self.config = config
        self.pool = pool
        self.prefix_cache: dict[str, str] = {}

        super().__init__(session, self.config["bot"]["token"])

        self.load_extension("starr.cogs.config")
        self.load_extension("starr.cogs.admin")

    @classmethod
    async def from_config(cls, session: aiohttp.ClientSession, config_file: str):
        with open(config_file) as f:
            config = toml.load(f)

        pool = cast(asyncpg.Pool, await asyncpg.create_pool(**config["database"]))

        return cls(session, config, pool)

    async def get_prefix(self, message: revolt.Message) -> list[str]:
        if not message.channel.server_id:
            return self.config["bot"]["default_prefix"]

        if not (prefix := self.prefix_cache.get(message.server.id)):  # type: ignore
            async with self.pool.acquire() as conn:
                conn: asyncpg.Connection
                async with conn.transaction():
                    prefix: str = await conn.fetchval("select prefix from server_configs where server_id=$1", message.server.id) or self.config["bot"]["default_prefix"]

                self.prefix_cache[message.server.id] = prefix

        return [prefix, self.user.mention]

    async def on_server_join(self, server: revolt.Server):
        print("foo")
        async with self.pool.acquire() as conn:
            conn: asyncpg.Connection
            async with conn.transaction():
                await conn.execute("insert into server_configs (server_id) values ($1)", server.id)


    async def on_raw_reaction_add(self, channel_id: str, message_id: str, user_id: str, emoji: str):
        channel = self.get_channel(channel_id)
        assert isinstance(channel, revolt.TextChannel)

        if emoji != "⭐" or channel.server_id is None:
            return

        async with self.pool.acquire() as conn:
            conn: asyncpg.Connection
            async with conn.transaction():
                try:
                    await conn.execute("insert into stars values ($1, $2, $3, $4)", user_id, channel.server.id, channel_id, message_id)
                except asyncpg.IntegrityConstraintViolationError:
                    pass  # they already have reacted - ignore

                current_star_count: int = await conn.fetchval("select count(*) from stars where message_id=$1", message_id)  # type: ignore
                row = await conn.fetchrow("select starboard_channel, star_count from server_configs where server_id=$1", channel.server.id)
                required_star_count: int = row["star_count"]  # type: ignore
                starboard_channel_id = row["starboard_channel"]  # type: ignore

                if starboard_channel_id == channel_id:
                    message = await channel.fetch_message(message_id)
                    parts = str(message.content).split(" ")
                    parts[1] = str(current_star_count)

                    await message.edit(content=" ".join(parts))

                elif current_star_count >= required_star_count:
                    starboard_message_id: str | None = await conn.fetchval("select starboard_channel_message from starred_messages where original_message=$1", message_id)  # type: ignore

                    starboard_channel = self.get_channel(starboard_channel_id)
                    assert isinstance(starboard_channel, revolt.TextChannel)
                    message = await channel.fetch_message(message_id)

                    content = f"⭐ {current_star_count} {channel.mention} ID: {message_id}"

                    if starboard_message_id:
                        starboard_message = await starboard_channel.fetch_message(starboard_message_id)
                        await starboard_message.edit(content=content)
                    else:
                        embed = revolt.SendableEmbed()
                        embed.icon_url = message.author.avatar.url if message.author.avatar else None
                        embed.title = message.author.name

                        jump_link = f"https://app.revolt.chat/server/{channel.server.id}/channel/{channel_id}/{message_id}"
                        embed.description = f"{message.content}\n\nOriginal: [Jump!]({jump_link})"
                        embed.colour = "#FFC71E"

                        interactions = revolt.MessageInteractions(reactions=["⭐"])

                        starboard_message = await starboard_channel.send(content, embed=embed, interactions=interactions)
                        await conn.execute("insert into starred_messages values ($1, $2)", starboard_message.id, message_id)


    async def on_raw_reaction_remove(self, channel_id: str, message_id: str, user_id: str, emoji: str):
        channel = self.get_channel(channel_id)
        assert isinstance(channel, revolt.TextChannel)

        if emoji != "⭐" or channel.server_id is None:
            return

        async with self.pool.acquire() as conn:
            conn: asyncpg.Connection
            async with conn.transaction():

                row = await conn.fetchrow("select starboard_channel, star_count from server_configs where server_id=$1", channel.server.id)
                required_star_count: int = row["star_count"]  # type: ignore
                starboard_channel_id = row["starboard_channel"]  # type: ignore

                if channel_id == starboard_channel_id:
                    original_message_id: str = await conn.fetchval("select original_message from starred_messages where starboard_channel_message=$1", message_id)  # type: ignore
                    starboard_message_id = message_id

                else:
                    original_message_id = message_id
                    starboard_message_id: str | None = await conn.fetchval("select starboard_channel_message from starred_messages where original_message=$1", message_id)  # type: ignore

                await conn.execute("delete from stars where user_id=$1 and message_id=$2", user_id, original_message_id)

                if starboard_message_id:
                    starboard_channel = self.get_channel(starboard_channel_id)
                    assert isinstance(starboard_channel, revolt.TextChannel)

                    new_star_count: int = await conn.fetchval("select count(*) from stars where message_id=$1", original_message_id)  # type: ignore
                    message = await starboard_channel.fetch_message(starboard_message_id)

                    if new_star_count < required_star_count:
                        await message.delete()
                        await conn.execute("delete from starred_messages where starboard_channel_message=$1", starboard_message_id)
                    else:
                        parts = str(message.content).split(" ")

                        parts[1] = str(new_star_count)

                        await message.edit(content=" ".join(parts))

    async def on_command_error(self, ctx: commands.Context[Self], error: Exception):
        if isinstance(error, commands.CheckError):
            await ctx.send("You cant use this command")
