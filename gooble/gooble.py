import asyncio
import shelve
import argparse

import discord
from discord.ext import commands

from . import DEFAULT_PREFIX, DEFAULT_COLOR

from .bet import Bet, BetException
from .house import House, HouseException
from .player import Player

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

def nameFromMember(ctx, /, member=None):
    member = ctx.author if member is None else member
    return member.nick if member.nick else member.name

async def playerName(ctx, player: Player):
    try:
        member = await ctx.guild.fetch_member(player.id)
        return nameFromMember(ctx, member)
    except Exception as e:
        logger.error("could not get player name; {}".format(e))
        return "Unknown Player"

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

    # Decorator that allows us to add commands to the gooble class. Special
    # attributes are added to these commands
    @classmethod
    def command(cls, *deco_args, **deco_kwargs):
        def decorator(func):
            async def on_error(ctx, error):
                e = error.__cause__ if error.__cause__ else error
                await ctx.send(e)

            async def on_call(ctx):
                logger.info("Request '{}'".format(func.__name__.upper()))
                house = ctx.bot.getHouse(ctx.guild)
                player = house.getPlayer(ctx.author.id)

                setattr(ctx, "house", house)
                setattr(ctx, "player", player)
                setattr(ctx, "author_name", nameFromMember(ctx, ctx.author))

            # Pass to the actual command decorator
            command = commands.command(*deco_args, **deco_kwargs)(func)
            command.before_invoke(on_call)
            command.error(on_error)

            if not hasattr(cls, "_gooble_commands"):
                setattr(cls, "_gooble_commands", [])

            # add it to the class
            _gooble_commands = getattr(cls, "_gooble_commands")
            _gooble_commands.append(command)

            logger.debug("Generated command {}".format(func.__name__))
            return command
        return decorator

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
                    self.houses[houseid].getPlayer(member.id, balance)

            self.add_command(bonk)

            # Add commands now that internal state has been resolved
            for command in getattr(self, "_gooble_commands", []):
                logger.debug("Adding command: {}".format(command.name))
                self.add_command(command)
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

    def getHouse(self, guild):
        return self.houses.setdefault(guild.id, House(guild.id))

@Gooble.command(help="Start a new bet")
async def bet(ctx, game, *, statement):
    self = ctx.bot

    bet = ctx.house.newBet(game, statement)

    embed = discord.Embed(
            title=bet.FRIENDLY_NAME,
            description=bet.statement,
            color=DEFAULT_COLOR
    )

    embed.add_field(name="id", value=str(bet.id))
    await ctx.send(embed=embed)

@Gooble.command(help="Place your stake and wager on a bet")
async def place(ctx, stake: int, wager, betid=None):
    self = ctx.bot

    bet = ctx.house.getBet(betid)

    bet.addPlayer(ctx.player, stake, wager)
    await ctx.send("{} has placed their wager".format(ctx.author_name))

@Gooble.command(help="List balances for all registered players")
async def stat(ctx, member: commands.MemberConverter = None):
    self = ctx.bot

    if member:
        player = ctx.house.getPlayer(member.id)
        embed = discord.Embed(
                title="Balance for {}".format(nameFromMember(ctx, member)),
                description=player.balance,
                color=DEFAULT_COLOR
        )
    else:
        embed = discord.Embed(
                title="Current Balances",
                color=DEFAULT_COLOR
        )

        value = "\n".join(
            ["{}, {}".format(await playerName(ctx, p), p.balance) \
                    for p in ctx.house.players.values()])
        embed.add_field(name="balances", value=value or "No players")
    await ctx.send(embed=embed)

@Gooble.command(help="End a gamble")
async def payout(ctx, result, betid=None):
    self = ctx.bot

    bet, deltas = ctx.house.endBet(betid, result)

    embed = discord.Embed(
            title="Bet results",
            description=bet.statement,
            color=DEFAULT_COLOR
    )

    value = "\n".join(
        ["{0}, {1:+} ({2})".format(await playerName(ctx, p), d, p.balance) \
                for p, d in deltas])
    embed.add_field(name="results", value=value, inline=False)

    await ctx.send(embed=embed)
