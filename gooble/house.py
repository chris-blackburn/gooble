from typing import Iterable, Tuple
import discord

from .player import LeaderboardTypes, Player
from .bet import Bet

DEFAULT_STARTING_AMOUNT = 1000

class HouseException(Exception):
    pass

class House:
    def __init__(self, guildid):
        self.id = guildid

        self.players = {}
        self.bets = {}

        self.community_pool = 0

        self.running: Bet = None

    @property
    def running(self) -> Bet:
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

    def cancelBet(self, betid):
        bet = self.bets.get(betid, self.running)
        if not bet:
            raise HouseException("please specify a valid id or start a new bet")
        
        deltas = bet.cancel()

        # If the bet is somewhere in the dictionary, remove it.
        if bet.id in self.bets:
            self.bets.pop(bet.id, None)
        # If the bet is the current running bet, clear the running bet.
        if bet is self.running:
            self.running = None

        return bet, deltas

    def endBet(self, betid, result):
        bet = self.getBet(betid)
        if not bet:
            return None

        deltas, house_take = bet.end(result)

        # If the house had any take, add it to the community pool.
        self.community_pool += house_take

        self.running = None
        return bet, deltas

    def newBet(self, gtnick, statement):
        bet = Bet.newBet(gtnick, statement)

        self.bets[bet.id] = bet
        self.running = bet
        return bet

    def transferFunds(self, sourcePlayer, amount, /, targetPlayer=None):
        # Ensure the player has enough funds for this donation.
        if sourcePlayer.balance < amount:
            raise HouseException("Player {} does not have enough funds " + 
                "for this transfer.".format(sourcePlayer.name))
        
        sourcePlayer.take(amount)

        # If the target player is NoneType, the donation is for the House ;)
        if targetPlayer is None:
            self.community_pool += amount
        else:
            targetPlayer.grant(amount)

    def getLeaderboard(self, type: LeaderboardTypes, limit: int = 10) -> Iterable[Tuple[Player, str]]:

        all_players = list(self.players.values())
        postfix = ''

        if type == LeaderboardTypes.WINS:
            ext_method = lambda x: x.wins
        elif type == LeaderboardTypes.WIN_RATE:
            ext_method = lambda x: x.win_rate
            postfix = '%'
        elif type == LeaderboardTypes.LOSSES:
            ext_method = lambda x: x.losses
        elif type == LeaderboardTypes.LOSS_RATE:
            ext_method = lambda x: x.loss_rate
            postfix = '%'
        elif type == LeaderboardTypes.MONEY:
            ext_method = lambda x: x.balance

        all_players.sort(key=ext_method, reverse=True)
        all_players = all_players[0:limit - 1]

        return [ (player, str(ext_method(player)) + postfix) for player in all_players ]

    @property
    def json(self):
        return {
            "id": self.id,
            "players": list(map(lambda k: k.json, self.players.values())),
            "community_pool": self.community_pool
        }

    @classmethod
    def fromJSON(cls, value):

        if "id" not in value:
            raise HouseException("The Player ID must be defined.")
        
        self = cls(value["id"])

        self.community_pool = value.get("community_pool", 0)

        if "players" in value:
            for playerJSON in value["players"]:
                newPlayer = Player.fromJSON(playerJSON)
                self.players[newPlayer.id] = newPlayer
    
        return self
            
