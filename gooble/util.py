import argparse
import shlex

import discord
from discord.ext import commands

from .logs import getLogger
logger = getLogger()

DEFAULT_PREFIX = "$"
DEFAULT_COLOR = 0xffd700

def parser(*deco_args, **deco_kwargs):
    def decorator(function):
        deco_kwargs.setdefault("prog", function.__name__)
        parser = argparse.ArgumentParser(*deco_args, **deco_kwargs)
        parser._print_message = lambda *args: None

        _args = getattr(function, "_args", [])
        for args, kwargs in _args:
            parser.add_argument(*args, **kwargs)

        desc = "\n".join(["\u200b" + line for line in \
                parser.format_help().split("\n")])

        async def wrapper(ctx, *args):
            try:
                parsed = parser.parse_args(args)
            except (argparse.ArgumentError, SystemExit):
                embed = discord.Embed(
                        title="Command Help",
                        description=desc,
                        color=DEFAULT_COLOR
                )

                await ctx.send(embed=embed)
                return

            return await function(ctx, parsed)
        wrapper.__name__ = function.__name__
        return wrapper
    return decorator

def option(*args, **kwargs):
    def decorator(function):
        if not hasattr(function, "_args"):
            setattr(function, "_args", [])

        _args = getattr(function, "_args")
        _args.insert(0, (args, kwargs))
        return function
    return decorator

def partition(pred, iterable):
    trues = []
    falses = []
    for item in iterable:
        if pred(item):
            trues.append(item)
        else:
            falses.append(item)
    return trues, falses
