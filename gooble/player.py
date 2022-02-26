class Player:
    def __init__(self, pid, name, starting=1000):
        self.id = pid
        self.name = name
        self.balance = starting

    def grant(self, monies):
        self.balance += monies

    def take(self, monies):
        self.balance -= monies
