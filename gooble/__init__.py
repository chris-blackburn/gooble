import asyncio
import shelve
import argparse

import discord
from discord.ext import commands

from .player import Player
from .bet import Bet, BetException
from .house import House
from .util import parser, option
from .util import DEFAULT_PREFIX, DEFAULT_COLOR

from .logs import getLogger
logger = getLogger()

# 1. Each guild is considered to be a house (or game)
#   - Houses can be reset (all bets and monies are cleared)
#     * We can also add some base payout so people who hit zero aren't dead in
#       the water
#   - Players are provided a balance the first time they place a bet (or request
#     a summary of their funds)
#     * Maybe we can use a decorator on all functions to do this?
# 2. In a house, players can start new bets and place their wagers
#   - A bet will have a win criteria
#   - All bets are zero-sum (the total loses equal total winnings)
#   - Players can place stakes and wagers on a bet (the amount they are gambling
#     on a particular outcome)
# 3. Payouts close bets and distribute the winnings

@commands.command()
async def bonk(ctx):
    await ctx.send("Go to horny jail")

# Convert a nickname to a subclass we can instantiate later
class ActionGameType(argparse.Action):
    def __call__(self, parser, namespace, gtnick, option_string=None):
        cls = Bet.byNickname(gtnick)
        if not cls:
            raise ValueError(
                    "Invalid game type specified '{}'".format(self.dest))

        setattr(namespace, self.dest, cls)

class ActionStatement(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, " ".join(values))

@commands.command()
@parser(description="Start a new bet")
@option("type", choices=Bet.choices(), action=ActionGameType)
@option("statement", nargs="+", action=ActionStatement,
        help="What the bet is on")
async def bet(ctx, args):
    self = ctx.bot

    house = self.getHouse(ctx.guild)

    try:
        bet = house.newBet(args.type, args.statement)
    except BetException as e:
        await ctx.send(e)
        return

    embed = discord.Embed(
            title=bet.FRIENDLY_NAME,
            description=bet.statement,
            color=DEFAULT_COLOR
    )

    embed.add_field(name="id", value=str(bet.id))
    await ctx.send(embed=embed)

@commands.command()
@parser(description="Place a bet")
@option("stake", type=int, help="The amount you want to bet")
@option("wager", help="The outcome you expect")
@option("--bet", "-b",
        help="ID of the bet to place (defaults to most recent bet)")
async def place(ctx, args):
    self = ctx.bot

    player = self.getPlayer(ctx.author)

    # TODO: get the relevant bet (if there is one)
    # TODO: add the player to the bet

    bet = self.running_bet
    if not bet:
        await ctx.send("No running bet")
        return

    try:
        bet.addPlayer(player, args.amount, args.gamble == "yes")
    except BetException as e:
        await ctx.send(e)
        return

    # TODO: send random discouraging messages
    await ctx.send("Are you sure you want to do that?")

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
        ["{0}, {1:+} ({2})".format(p.name, d, p.balance) for p, d in deltas])
    embed.add_field(name="results", value=value, inline=False)

    await ctx.send(embed=embed)

class Gooble(commands.Bot):
    DB_NAME = "gooble.db"

    def __init__(self, *args, **kwargs):

        intents = discord.Intents.default()
        intents.messages = True

        super().__init__(command_prefix=DEFAULT_PREFIX, intents=intents, *args,
                **kwargs)

        self.add_command(bonk)
        self.add_command(bet)

        with shelve.open(self.DB_NAME) as db:
            self.houses = db.get("houses", {})

    async def close(self, *args, **kwargs):
        await super().close(*args, **kwargs)

        with shelve.open(self.DB_NAME) as db:
            db["houses"] = self.houses

    def getHouse(self, guild):
        return self.houses.setdefault(guild.id, House(guild.id))

