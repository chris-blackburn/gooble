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
        """
        Player factory
        """
        key = author.id
        player = self.players.get(key, None)
        if player is None:
            player = Player(key, author.nick)
            self.players[key] = player

        return player

    def newBet(self, gtnick, statement):
        bet = Bet.newBet(gtnick, statement)

        self.bets[bet.id] = bet
        return bet
