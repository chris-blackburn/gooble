from enum import Enum, auto

class PlayerException(Exception):
    pass

class LeaderboardTypes(Enum):
    WINS = 0
    WIN_RATE = auto()
    LOSSES = auto()
    LOSS_RATE = auto()
    MONEY = auto()

class Player:
    '''
    The number of bets that the player has won.
    '''
    wins = 0

    '''
    The number of bets that the player has lost.
    '''
    losses = 0

    def __init__(self, pid, balance):
        self.id = pid
        self.balance = balance

    def grant(self, monies):
        self.balance += monies

    def take(self, monies):
        self.balance -= monies

    def add_win(self) -> None:
        self.wins = self.wins + 1

    def add_loss(self) -> None:
        self.losses = self.losses + 1

    @property
    def win_rate(self) -> float:
        # Avoid division by zero.
        if self.wins + self.losses == 0:
            return 0

        return (self.wins / (self.wins + self.losses)) * 100

    @property
    def loss_rate(self) -> float:
        # Avoid division by zero.
        if self.wins + self.losses == 0:
            return 0

        return (self.losses / (self.wins + self.losses)) * 100

    @property
    def json(self):
        return {
            "id": self.id,
            "balance": self.balance,
            "wins": self.wins,
            "losses": self.losses
        }

    @classmethod
    def fromJSON(cls, value):

        if "id" not in value:
            raise PlayerException("The Player ID must be defined.")
        if "balance" not in value:
            raise PlayerException("A balance for the Player must be defined.")
        
        self = cls(value["id"], value["balance"])

        self.wins = value.get("wins", 0)
        self.losses = value.get("losses", 0)
    
        return self
        

