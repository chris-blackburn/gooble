class Player:
    def __init__(self, pid, name, balance):
        self.id = pid
        self.name = name
        self.balance = balance

    def grant(self, monies):
        self.balance += monies

    def take(self, monies):
        self.balance -= monies
