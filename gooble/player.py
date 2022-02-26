class Player:
    def __init__(self, pid, balance):
        self.id = pid
        self.balance = balance

    def grant(self, monies):
        self.balance += monies

    def take(self, monies):
        self.balance -= monies
