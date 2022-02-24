#!/usr/bin/env python3

import asyncio
import shelve

import discord
from discord.ext import commands

from .session import *

from .logs import getLogger
logger = getLogger()

DEFAULT_PREFIX="$"

@commands.command()
async def bonk(ctx):
    await ctx.send("Go to horny jail")

@commands.command()
async def bet(ctx, *stmt):
    """
    Start a new bet
    """
    self = ctx.bot

    stmt = " ".join(stmt)

    bet = Bet(stmt=stmt)
    self.addBet(bet)

    embed = discord.Embed(
            title="New bet",
            description=stmt,
            color=0xffd700
    )

    embed.add_field(name="id", value=str(bet.id))
    await ctx.send(embed=embed)

@commands.command()
async def stat(ctx):
    """
    List all balances
    """
    self = ctx.bot

    embed = discord.Embed(
            title="Current Balances",
            color=0xffd700
    )

    value = "\n".join(
        ["{}, {}".format(p.name, p.amount) for p in self.players.values()]) or \
                "No players"
    logger.debug(value)
    embed.add_field(name="balances", value=value)

    await ctx.send(embed=embed)

@commands.command()
async def payout(ctx, result):
    """
    End a gambling session
    """
    self = ctx.bot

    bet = self.running_bet
    deltas = bet.end(result == "Y")

    embed = discord.Embed(
            title="Bet results",
            description=bet.statement,
            color=0xffd700
    )
    
    embed.add_field(name="id", value=str(bet.id))

    value = "\n".join(
        ["{0}, {1:+} ({2})".format(p.name, d, p.amount) for p, d in deltas])
    embed.add_field(name="results", value=value, inline=False)

    await ctx.send(embed=embed)

@commands.command()
async def place(ctx, amount, result):
    """
    Place a bet on a session
    """
    self = ctx.bot

    player = self.getPlayer(ctx.author.nick)

    bet = self.running_bet

    try:
        bet.addPlayer(player, int(amount), result)
    except BetException as e:
        await ctx.send(e)
        return

    # TODO: send random discouraging messages
    await ctx.send("Are you sure you want to do that?")

class Gooble(commands.Bot):
    def __init__(self, *args, **kwargs):

        intents = discord.Intents.default()
        intents.messages = True

        super().__init__(command_prefix=DEFAULT_PREFIX, intents=intents, *args,
                **kwargs)

        self.add_command(bonk)
        self.add_command(bet)
        self.add_command(stat)
        self.add_command(payout)
        self.add_command(place)

        self.running_bet = None

        # TODO: Move players to games classes when I make them
        self.players = {}

    def addBet(self, bet):
        self.running_bet = bet

    def getPlayer(self, username):
        player = self.players.get(username, None)
        if player is None:
            player = Player(username)
            self.players[username] = player

        return player
