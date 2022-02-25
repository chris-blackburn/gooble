import discord

from .player import Player
from .bet import Bet

class House:
    """
    Container
    """
    def __init__(self, guildid):
        self.id = guildid

        self.players = {}
        self.bets = {}

    def getPlayer(self, author):
        return self.players.setdefault(author.id,
                Player(author.id, author.nick))

    def newBet(self, betcls, statement):
        bet = betcls(statement)

        self.bets[bet.id] = bet
        return bet
