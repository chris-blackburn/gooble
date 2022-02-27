import asyncio
import shelve
import argparse
from random import choice

import discord
from discord.ext import commands

from . import DEFAULT_PREFIX, DEFAULT_COLOR, CELEBRATORY_MSGS

from .util import parser, option, ActionStatement
from .bet import Bet, BetException, _BETS_BY_TYPE
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
            async def wrapper(ctx, *args, **kwargs):
                setattr(ctx, "author_name", nameFromMember(ctx, ctx.author))
                setattr(ctx, "house", ctx.bot.getHouse(ctx.guild))

                try:
                    return await func(ctx, *args, **kwargs)
                except (BetException, HouseException) as e:
                    await ctx.send(e)

            # Pass to the actual command decorator
            wrapper.__name__ = func.__name__
            command = commands.command(*deco_args, **deco_kwargs)(wrapper)

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

            # The database should be a dictionary where each key is a House ID and its
            # corresponding value is a House definition dictionary.
            for houseid, houseDict in db.items():
                houseid = int(houseid)
                try:
                    guild = await self.fetch_guild(houseid)
                    if not guild:
                        continue
                except Exception as e:
                    logger.error("Could not fetch guild {}; {}".format(
                        houseid, e))
                    continue

                logger.debug("Found house id {}".format(houseid))
                self.houses[houseid] = House(houseid)

                # If a list of records are included in this House definition, parse
                # them.
                if "records" in houseDict:
                    for pid, balance in houseDict["records"]:
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
                        
                        # "Get" the players. This will create a new Player instance
                        # in the House if they don't already exist.
                        self.houses[houseid].getPlayer(member.id, balance)
                
                # If a value for the community pool is defined in this House definition,
                # transfer it over.
                if "community_pool" in houseDict:
                    self.houses[houseid].community_pool = houseDict["community_pool"]


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

            # For each of the House instances, create a new key in the dictionary.
            for house in self.houses.values():
                logger.debug("Saving House {}".format(house.id))

                # Create a new dictionary that represents the internal state of
                # the House.
                houseDict = { "records": [], "community_pool": 0 }

                # Add all of the player balances for the House.
                for player in house.players.values():
                    logger.debug("Saving pid {}, balance={}".format(
                        player.id, player.balance))
                    houseDict["records"].append((player.id, player.balance))

                # Copy over the value of the community pool.
                houseDict["community_pool"] = house.community_pool

                # Add a new entry to the database dictionary for this house,
                # associating the ID with the internal state object (dict).
                db[str(house.id)] = houseDict

        logger.debug("State saved")

    def getHouse(self, guild) -> House:
        return self.houses.setdefault(guild.id, House(guild.id))

@Gooble.command()
@parser(description="Lists all of the available games.")
async def games(ctx, args):
    embed = discord.Embed(
        title="Available Games",
        description="This bot currently supports the following games:",
        color=DEFAULT_COLOR
    )

    for game, _ in _BETS_BY_TYPE.values():
        embed.add_field(
            name=game.FRIENDLY_NAME,
            value=game.FRIENDLY_DESCRIPTION,
            inline=False
        )

    await ctx.send(embed=embed)

@Gooble.command()
@parser(description="Give all players some funds! 💰")
@option("amount", help="""How much to give everyone. Negative numbers
        can be used to deduct funds.""")
async def giftall(ctx, args):

    house = ctx.house
    author = ctx.author.name

    # For all known players, grant them the specified amount.
    for player in house.players.values():
        player.grant(int(args.amount))

    embed = discord.Embed(
        title="Payday Is Here! 💰",
        description="{} has granted everyone {}! {}".format(
            author, args.amount, choice(CELEBRATORY_MSGS)
        )
    )

    await ctx.send(embed=embed)

@Gooble.command()
@parser(description="Start a new bet")
@option("type", choices=Bet.choices())
@option("statement", nargs="+", action=ActionStatement,
        help="What the bet is on")
async def bet(ctx, args):
    logger.info("BET: {}".format(args))
    self = ctx.bot

    bet = ctx.house.newBet(args.type, args.statement)

    embed = discord.Embed(
            title=bet.FRIENDLY_NAME,
            description=bet.statement,
            color=DEFAULT_COLOR
    )

    embed.add_field(name="id", value=str(bet.id))
    await ctx.send(embed=embed)

@Gooble.command()
@parser(description="Place a bet")
@option("stake", type=int, help="The amount you want to bet")
@option("wager", help="The outcome you expect")
@option("--bet", "-b",
        help="ID of the bet to place (defaults to most recent bet)")
async def place(ctx, args):
    logger.info("PLACE: {}".format(args))
    self = ctx.bot

    player = ctx.house.getPlayer(ctx.author.id)

    bet = ctx.house.getBet(args.bet)

    bet.addPlayer(player, args.stake, args.wager)
    await ctx.send("{} has placed their wager".format(ctx.author_name))

@Gooble.command()
@parser(description="List balances of all registered players")
@option("--me", action="store_true", help="Only list your balance")
async def stat(ctx, args):
    logger.info("STAT: {}".format(args))
    self = ctx.bot

    if args.me:
        player = ctx.house.getPlayer(ctx.author.id)
        embed = discord.Embed(
                title="Balance for {}".format(ctx.author_name),
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
        embed.add_field(
            name="Player Balances",
            value=value or "No players",
            inline=False
        )

        # Add the community pool for the House.
        embed.add_field(
            name="House Community Pool",
            value=ctx.house.community_pool,
            inline=False
        )

    await ctx.send(embed=embed)

@Gooble.command()
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

@Gooble.command()
@parser(description="End a gamble")
@option("result", help="The result of the bet")
@option("--bet", "-b",
        help="ID of the bet to place (defaults to most recent bet)")
async def payout(ctx, args):
    logger.info("PAYOUT: {}".format(args))
    self = ctx.bot

    bet, deltas = ctx.house.endBet(args.bet, args.result)

    embed = discord.Embed(
            title="Bet Results",
            description=bet.statement,
            color=DEFAULT_COLOR
    )

    value = "\n".join(
        ["{0}, {1:+} ({2})".format(await playerName(ctx, p), d, p.balance) \
                for p, d in deltas])
    embed.add_field(name="Type", value=bet.FRIENDLY_NAME)
    embed.add_field(name="Unique ID", value=bet.id)
    embed.add_field(name="Results", value=value or "No Bets Placed", inline=False)

    await ctx.send(embed=embed)

@Gooble.command()
@parser(description="Transfer funds to another player or make a donation to the House.")
@option("amount", help="The amount to transfer.")
@option("player", help="""The player to transfer to. If this is omitted,
    the funds are transferred to the house.""", nargs="?")
async def transfer(ctx, args):

    # Get the House for guild in which the command was sent.
    house = ctx.house
    # Get the player that sent the transfer request.
    player = house.getPlayer(ctx.author.id)

    # message = ctx.message

    # Assume no target player to start.
    targetPlayer = None

    # If a target player was specified, attempt to look that Member up.
    if args.player is not None:
        print(args.player)
        targetMember = await commands.MemberConverter().convert(ctx, args.player)
        targetPlayer = house.getPlayer(targetMember.id)

    recipient = house.transferFunds(player, targetPlayer, int(args.amount))
    
    embed = discord.Embed(
        title="Funds Transferred",
        description="{} was transferred to {}.".format(
            args.amount, (await playerName(ctx, recipient)) if recipient else "The House"
        ),
        color=DEFAULT_COLOR
    )

    if recipient == None:
        embed.add_field(
            name="House Community Pool",
            value=house.community_pool,
            inline=False
        )

    await ctx.send(embed=embed)
