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

@commands.command()
@parser(description="Start a new bet")
@option("statement", help="What the bet is on")
@option("type", choices=Bet.choices(), help="The game type")
async def bet(ctx, args):
    self = ctx.bot

    house = self.getHouse(ctx.guild)

    try:
        bet = house.newBet(args.type, args.statement)
    except BetException as e:
        await ctx.send(e)
        return

    embed = discord.Embed(
            title=bet.GAME_TYPE.name,
            description=bet.statement,
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

@commands.command()
@parser(description="Place a bet")
@option("amount", type=int, help="The amount you want to bet")
@option("gamble", choices=["yes", "no"], help="Expected outcome")
@option("--bet", "-b",
        help="ID of the bet to place (defaults to most recent bet)")
async def place(ctx, args):
    self = ctx.bot

    player = self.getPlayer(ctx.author)

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

class Gooble(commands.Bot):
    def __init__(self, *args, **kwargs):

        intents = discord.Intents.default()
        intents.messages = True

        super().__init__(command_prefix=DEFAULT_PREFIX, intents=intents, *args,
                **kwargs)

        self.add_command(bonk)
        self.add_command(bet)

        self.houses = {}

    def getHouse(self, guild):
        house = self.houses.get(guild.id, None)
        if house is None:
            house = House(guild.id)
            self.houses[guild.id] = house

        return house

