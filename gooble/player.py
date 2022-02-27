from enum import Enum

class LeaderboardTypes(Enum):
    WINS = "WINS"
    WIN_RATE = "WIN RATE"
    LOSSES = "LOSSES"
    LOSS_RATE = "LOSS RATE"
    MONEY = "MONEY"

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
        

