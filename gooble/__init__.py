import asyncio
import shelve
import argparse

import discord
from discord.ext import commands

from .player import Player
from .bet import Bet, BetException
from .util import parser, option
from .util import DEFAULT_PREFIX, DEFAULT_COLOR

from .logs import getLogger
logger = getLogger()

@commands.command()
async def bonk(ctx):
    await ctx.send("Go to horny jail")

@commands.command()
@parser(description="Start a new bet")
@option("statement", help="A statement of a yes/no bet")
async def bet(ctx, args):
    self = ctx.bot

    bet = Bet(stmt=args.statement)
    self.addBet(bet)

    embed = discord.Embed(
            title="New bet",
            description=args.statement,
            color=DEFAULT_COLOR
    )

    embed.add_field(name="id", value=str(bet.id))
    await ctx.send(embed=embed)

@commands.command()
@parser(description="List balances of all registered players")
@option("--me", action="store_true", help="Only list your balance")
async def stat(ctx, args):
    self = ctx.bot

    if args.me:
        player = self.getPlayer(ctx.author)
        embed = discord.Embed(
                title="Balance for {}".format(player.name),
                description=player.balance,
                color=DEFAULT_COLOR
        )

    else:
        embed = discord.Embed(
                title="Current Balances",
                color=DEFAULT_COLOR
        )

        value = "\n".join(
            ["{}, {}".format(p.name, p.balance) for p in self.players.values()])
        embed.add_field(name="balances", value=value or "No players")

    await ctx.send(embed=embed)

@commands.command()
@parser(description="End a gamble")
@option("result", choices=["yes", "no"], help="The result of the bet")
async def payout(ctx, args):
    """
    End a gambling session
    """
    self = ctx.bot

    bet = self.running_bet
    if not bet:
        embed = discord.Embed(
                title="Bet results",
                description="No running bets",
                color=DEFAULT_COLOR
        )

    deltas = bet.end(args.result == "yes")
    self.removeBet(bet)

    embed = discord.Embed(
            title="Bet results",
            description=bet.statement,
            color=DEFAULT_COLOR
    )

    embed.add_field(name="id", value=str(bet.id))

    value = "\n".join(
        ["{0}, {1:+} ({2})".format(p.name, d, p.amount) for p, d in deltas])
    embed.add_field(name="results", value=value, inline=False)

    await ctx.send(embed=embed)

@commands.command()
@parser(description="End a gamble")
@option("amount", type=int, help="The amount you want to bet")
@option("gamble", choices=["yes", "no"], help="Expected outcome")
async def place(ctx, args):
    """
    Place a bet on a session
    """
    self = ctx.bot

    player = self.getPlayer(ctx.author)

    bet = self.running_bet
    if not bet:
        await ctx.send("No running bet")
        return

    try:
        bet.addPlayer(player, args.amount, args.gamble)
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

        # TODO: Make lists of players and bets unique per server
        # TODO: Handle multiple bets, but also track the running bet
        self.players = {}
        self.running_bet = None

    def addBet(self, bet):
        self.running_bet = bet

    def removeBet(self, bet):
        self.running_bet = None

    def getPlayer(self, author):
        key = author.id
        player = self.players.get(key, None)
        if player is None:
            player = Player(author.name)
            self.players[key] = player

        return player
