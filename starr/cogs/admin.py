# from __future__ import annotations

from revolt.ext import commands
import re
import inspect
import traceback
from ..client import Client

codeblock_regex = re.compile(r"```(?:\w*)\n((?:.|\n)+)\n```")


class Admin(commands.Cog):
    def __init__(self):
        self.previous_eval = {}

    @commands.command()
    @commands.check(lambda ctx: ctx.author.id == "01FD58YK5W7QRV5H3D64KTQYX3")
    async def eval(self, ctx: commands.Context[Client], *, code: str):
        if match := codeblock_regex.match(code):
            code = match.group(1)

        lines = code.split("\n")
        lines[-1] = f"return {lines[-1]}"
        indented_code = "\n\t".join(lines)

        code = f"""async def _eval():\n\t{indented_code}"""

        globs = globals().copy()
        globs["ctx"] = ctx
        globs["client"] = ctx.client
        globs["server"] = ctx.server
        globs["channel"] = ctx.channel
        globs["author"] = ctx.author
        globs["message"] = ctx.message
        globs["_"] = self.previous_eval

        try:
            exec(code, globs)
            result = globs["_eval"]()

            if inspect.isasyncgen(result):
                async for value in result:
                    await ctx.send(repr(value))
                    result = None
            else:
                result = await result

                await ctx.send(str(result))

            self.previous_eval = result

        except Exception as e:
            return await ctx.send(f"```py\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}\n```")

    @eval.error
    async def on_eval_error(self, ctx: commands.Context, error: Exception):
        await ctx.send(repr(error))

def setup(client: commands.CommandsClient):
    client.add_cog(Admin())

def teardown(client: commands.CommandsClient):
    client.remove_cog("Admin")
