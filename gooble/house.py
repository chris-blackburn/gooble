import discord

from .player import Player
from .bet import Bet

DEFAULT_STARTING_AMOUNT = 1000

class HouseException(Exception):
    pass

class House:
    def __init__(self, guildid):
        self.id = guildid

        self.players = {}
        self.bets = {}

        self.running = None

    @property
    def running(self):
        return self.bets.get(self._running_id, None)

    @running.setter
    def running(self, bet: Bet):
        self._running_id = bet.id if bet else None

    @running.deleter
    def running(self):
        self._running_id = None

    def getPlayer(self, pid, /, balance=DEFAULT_STARTING_AMOUNT):
        player = self.players.setdefault(pid,
                Player(pid, balance))

        return player

    def getBet(self, betid):
        bet = self.bets.get(betid, self.running)
        if not bet:
            raise HouseException("please specify a valid id or start a new bet")

        return bet

    def endBet(self, betid, result):
        bet = self.getBet(betid)
        if not bet:
            return None

        deltas = bet.end(result)
        self.running = None
        return bet, deltas

    def newBet(self, gtnick, statement):
        bet = Bet.newBet(gtnick, statement)

        self.bets[bet.id] = bet
        self.running = bet
        return bet
