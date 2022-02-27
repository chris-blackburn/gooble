import asyncio
import shelve
import argparse
from random import choice

import discord
from discord.ext import commands

from . import DEFAULT_PREFIX, DEFAULT_COLOR, CELEBRATORY_MSGS

from .bet import Bet, BetException, _BETS_BY_TYPE
from .house import House, HouseException
from .player import Player, LeaderboardTypes

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
        def _nameFromMember(ctx, /, member=None):
            member = ctx.author if member is None else member
            return member.nick if member.nick else member.name

        async def _playerName(ctx, player: Player):
            try:
                member = await ctx.guild.fetch_member(player.id)
                return _nameFromMember(ctx, member)
            except Exception as e:
                logger.error("could not get player name; {}".format(e))
                return "Unknown Player"

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
                setattr(ctx, "playerName",
                        lambda player: _playerName(ctx, player))
                setattr(ctx, "memberName",
                        lambda member: _nameFromMember(ctx, member))
                setattr(ctx, "author_name", _nameFromMember(ctx, ctx.author))

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

            # The database should be a dictionary where each key is a House ID and its
            # corresponding value is a House definition dictionary.
            for houseDict in db.get("houses", []):

                import json
                print(json.dumps(houseDict))

                newHouse = House.fromJSON(houseDict)
                self.houses[newHouse.id] = newHouse

            # TODO: Do some post processing to check that all the loaded guilds
            # actually exist. For each guild that does exist, check that all of its
            # members exist. For any House or Player that doesn't exist, remove it
            # from the corresponding map.

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
        houses = []
        with shelve.open(self.DB_NAME) as db:
            houses = list(map(lambda k: k.json, self.houses.values()))
            db["houses"] = houses

        logger.debug("State saved")

    def getHouse(self, guild) -> House:
        return self.houses.setdefault(guild.id, House(guild.id))

@Gooble.command(help="Lists all of the available games.")
async def games(ctx):
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

@Gooble.command(help="Give all players some funds! 💰")
async def giftall(ctx, amount: int):
    house = ctx.house

    # For all known players, grant them the specified amount.
    # TODO: gift to all players in server?
    for player in house.players.values():
        player.grant(amount)

    embed = discord.Embed(
        title="💰 Payday Is Here! 💰",
        description="{} has granted everyone {}! {}".format(
            ctx.author_name, amount, choice(CELEBRATORY_MSGS)
        )
    )

    await ctx.send(embed=embed)

@Gooble.command(help="Start a new bet")
async def bet(ctx, game, *, statement):
    self = ctx.bot

    bet = ctx.house.newBet(game, statement)

    embed = discord.Embed(
            title=bet.FRIENDLY_NAME,
            description=bet.statement,
            color=DEFAULT_COLOR
    )

    embed.add_field(name="Unique Identifier", value=str(bet.id))
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
                title="Player {}".format(ctx.memberName(member)),
                color=DEFAULT_COLOR
        )

        embed.add_field(name="Balance", value=player.balance, inline=False)
        embed.add_field(name="Wins", value=player.wins, inline=True)
        embed.add_field(name="Losses", value=player.losses, inline=True)
        embed.add_field(name="Win Rate", value=str(player.win_rate) + "%", inline=True)

    else:
        embed = discord.Embed(
                title="Current Balances",
                color=DEFAULT_COLOR
        )

        value = "\n".join(
            ["{}, {}".format(await ctx.playerName(p), p.balance) \
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

@Gooble.command(help="Display details about the current state of a bet")
async def details(ctx, betid=None):
    self = ctx.bot

    # Get the House for guild in which the command was sent.
    house = ctx.house
    # Get the Bet specified in the command.
    bet = house.getBet(betid)

    # Get a list of stakes for the bet.
    stakes = bet.getStakes()

    embed = discord.Embed(
        title="",
        description=bet.statement,
    )

    # Serialize the stake tuples for use in the embed.
    serial_stakes = "\n".join([
        "{0} : {1} on \"{2}\"".format(await ctx.playerName(player), stake, wager)
            for player, stake, wager in stakes
    ])

    embed.add_field(name="Stakes", value=serial_stakes or "No Stakes!")
    await ctx.send(embed=embed)

@Gooble.command(help="End a gamble")
async def payout(ctx, result, betid=None):
    self = ctx.bot

    bet, deltas = ctx.house.endBet(betid, result)

    embed = discord.Embed(
            title="Bet Results",
            description=bet.statement,
            color=DEFAULT_COLOR
    )

    value = "\n".join(
        ["{0}, {1:+} ({2})".format(await ctx.playerName(p), d, p.balance) \
                for p, d in deltas])
    embed.add_field(name="Type", value=bet.FRIENDLY_NAME)
    embed.add_field(name="Unique Identifier", value=bet.id)
    embed.add_field(name="Results", value=value or "No Bets Placed",
            inline=False)

    await ctx.send(embed=embed)

@Gooble.command(help="Transfer funds to another player or make a donation to the House.")
async def transfer(ctx, amount: int, recipient: commands.MemberConverter=None):
    house = ctx.house
    player = ctx.player

    # Assume no target player to start.
    targetPlayer = None

    # If a target player was specified, attempt to look that Member up.
    if recipient is not None:
        targetPlayer = house.getPlayer(recipient.id)

    house.transferFunds(player, amount, targetPlayer)
    
    recipientName = await ctx.playerName(recipient) if targetPlayer else \
            "The House"
    embed = discord.Embed(
        title="Funds Transferred",
        description="{} was transferred to {}.".format(amount, recipientName),
        color=DEFAULT_COLOR
    )

    embed.add_field(
        name="House Community Pool",
        value=house.community_pool,
        inline=False
    )

    await ctx.send(embed=embed)

@Gooble.command(
    help="Displays a leaderboard. Available leaderboards are {}".format(
        ", ".join([ e.name.replace("_", " ") for e in LeaderboardTypes ])
    )
)
async def leaderboard(ctx, *, type: str):
    
    leaderboard_type = LeaderboardTypes[type.upper().replace(" ", "_")]
    leaderboard_items = ctx.house.getLeaderboard(leaderboard_type)

    embed = discord.Embed(
        title="{} Leaderboard".format(
            leaderboard_type.name.replace("_", " ").title()
        )
    )

    leaderboard_list = "\n".join(
        [ "`{:<20} {:>4}`".format(await ctx.playerName(player), value)
            for player, value in leaderboard_items ]
    )

    embed.add_field(
        name="Top Players",
        value=leaderboard_list,
        inline=False
    )

    await ctx.send(embed=embed)