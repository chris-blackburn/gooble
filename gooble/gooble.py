import asyncio
import shelve
import argparse

import discord
from discord.ext import commands

from . import DEFAULT_PREFIX, DEFAULT_COLOR

from .util import parser, option
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
    logger.info("BET: {}".format(args))

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
    logger.info("PLACE: {}".format(args))
    self = ctx.bot

    house = self.getHouse(ctx.guild)
    player = house.getPlayer(ctx.author)

    bet = house.getBet(args.bet)

    bet.addPlayer(player, args.stake, args.wager)
    await ctx.send("{} has placed their wager".format(player.name))

@commands.command()
@parser(description="List balances of all registered players")
@option("--me", action="store_true", help="Only list your balance")
@throwsGoobleException
async def stat(ctx, args):
    logger.info("STAT: {}".format(args))
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
@parser(description="Display details about the current state of a bet.")
@option("--bet", "-b",
        help="The ID of the bet. If not provided, the most recent bet opened is assumed.")
async def details(ctx, args):
    logger.info("DETAILS: {}".format(args))
    self = ctx.bot

    # Get the House for guild in which the command was sent.
    house = self.getHouse(ctx.guild)
    # Get the Bet specified in the command.
    bet = house.getBet(args.bet)

    # Get a list of stakes for the bet.
    stakes = bet.getStakes()

    embed = discord.Embed(
        title="",
        description=bet.statement,
    )

    # Serialize the stake tuples for use in the embed.
    serial_stakes = "\n".join([
        "{0} : {1} on \"{2}\"".format(player.name, stake, wager)
            for player, stake, wager in stakes
    ])

    embed.add_field(name="Stakes", value=serial_stakes or "No Stakes!")
    await ctx.send(embed=embed)

@commands.command()
@parser(description="End a gamble")
@option("result", help="The result of the bet")
@option("--bet", "-b",
        help="ID of the bet to place (defaults to most recent bet)")
@throwsGoobleException
async def payout(ctx, args):
    logger.info("PAYOUT: {}".format(args))
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

        kwargs.setdefault("command_prefix", DEFAULT_PREFIX)
        kwargs.setdefault("intents", intents)
        super().__init__(*args, **kwargs)

        self.houses = {}

        # Continue initialization after we are connected
        self.listen("on_connect")(self.restoreState)

    async def restoreState(self):
        logger.debug("Rebuilding internal state")
        with shelve.open(self.DB_NAME) as db:
            housedict = db.get("houses", {})

            # For each guild id we have
            for houseid, records in housedict.items():
                try:
                    guild = await self.fetch_guild(houseid)
                    if not guild:
                        continue
                except Exception as e:
                    logger.error("Could not fetch guild {}; {}".format(
                        houseid, e))
                    continue

                # For each member id we have
                logger.debug("Found house id {}".format(houseid))
                self.houses[houseid] = House(houseid)
                for pid, balance in records:
                    try:
                        member = await guild.fetch_member(pid)
                        if not member:
                            continue
                    except Exception as e:
                        logger.error("Could not fetch member {} from guild {}; {}".format(
                            pid, houseid, e))
                        continue

                    logger.debug("Found pid {}, balance={}".format(
                        pid, balance))
                    self.houses[houseid].getPlayer(member, balance)

            # Add commands now that internal state has been resolved
            self.add_command(bonk)
            self.add_command(bet)
            self.add_command(place)
            self.add_command(stat)
            self.add_command(payout)
            self.add_command(details)
            logger.debug("Bot initialized")

    async def close(self, *args, **kwargs):
        await super().close(*args, **kwargs)

        # Save just the players and their balances per house id so we don't get
        # in trouble later with trying to unpickle classes
        logger.debug("Saving state to db")
        with shelve.open(self.DB_NAME) as db:
            housedict = {}
            for house in self.houses.values():
                logger.debug("Saving house id {}".format(house.id))

                records = []
                for player in house.players.values():
                    logger.debug("Saving pid {}, balance={}".format(
                        player.id, player.balance))
                    records.append((player.id, player.balance))
                housedict[house.id] = records

            db["houses"] = housedict

        logger.debug("State saved")

    def getHouse(self, guild) -> House:
        return self.houses.setdefault(guild.id, House(guild.id))
