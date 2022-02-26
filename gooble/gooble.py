import asyncio
import shelve
import argparse

import discord
from discord.ext import commands

from . import DEFAULT_PREFIX, DEFAULT_COLOR

from .util import parser, option
from .player import Player
from .bet import Bet, BetException
from .house import House, HouseException

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

# TODO:
# 1. Add a --games flag to bet to list all game types and descriptions
# 2. Add command to get the status of a bet (and to list active bets)
# 3. Add ability to get a set of all the bets a players is involved in (probably
#    just extend the stat command)
# 4. Add command to reset/cancel a player, house, or bet
# 5. Make a pot of money in a house such that if there are no winners in a bet,
#    the lost money has somwhere to go (instead of the void)
# 6. Automated testing cause we saucy like that

@commands.command()
async def bonk(ctx):
    await ctx.send("Go to horny jail")

def throwsGoobleException(func):
    async def wrapper(ctx, *args, **kwargs):
        try:
            return await func(ctx, *args, **kwargs)
        except (BetException, HouseException) as e:
            await ctx.send(e)
    wrapper.__name__ = func.__name__
    return wrapper

# Takes all values and concatenates them to a string
class ActionStatement(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, " ".join(values))

@commands.command()
@parser(description="Start a new bet")
@option("type", choices=Bet.choices())
@option("statement", nargs="+", action=ActionStatement,
        help="What the bet is on")
@throwsGoobleException
async def bet(ctx, args):
    logger.debug("BET: {}".format(args))

    self = ctx.bot

    house = self.getHouse(ctx.guild)
    bet = house.newBet(args.type, args.statement)

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
@throwsGoobleException
async def place(ctx, args):
    logger.debug("PLACE: {}".format(args))
    self = ctx.bot

    house = self.getHouse(ctx.guild)
    player = house.getPlayer(ctx.author)

    bet = house.getBet(args.bet)

    bet.addPlayer(player, args.stake, args.wager)
    await ctx.send("{}'s has placed their wager".format(player.name))

@commands.command()
@parser(description="List balances of all registered players")
@option("--me", action="store_true", help="Only list your balance")
@throwsGoobleException
async def stat(ctx, args):
    logger.debug("STAT: {}".format(args))
    self = ctx.bot

    house = self.getHouse(ctx.guild)

    if args.me:
        player = house.getPlayer(ctx.author)
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
            ["{}, {}".format(p.name, p.balance) for p in \
                    house.players.values()])
        embed.add_field(name="balances", value=value or "No players")

    await ctx.send(embed=embed)

@commands.command()
@parser(description="End a gamble")
@option("result", help="The result of the bet")
@option("--bet", "-b",
        help="ID of the bet to place (defaults to most recent bet)")
@throwsGoobleException
async def payout(ctx, args):
    logger.debug("PAYOUT: {}".format(args))
    self = ctx.bot

    house = self.getHouse(ctx.guild)
    bet, deltas = house.endBet(args.bet, args.result)

    embed = discord.Embed(
            title="Bet results",
            description=bet.statement,
            color=DEFAULT_COLOR
    )

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
        self.add_command(place)
        self.add_command(stat)
        self.add_command(payout)

        with shelve.open(self.DB_NAME) as db:
            self.houses = db.get("houses", {})

    async def close(self, *args, **kwargs):
        await super().close(*args, **kwargs)

        with shelve.open(self.DB_NAME) as db:
            db["houses"] = self.houses

    def getHouse(self, guild):
        return self.houses.setdefault(guild.id, House(guild.id))

