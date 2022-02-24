class Player:
    def __init__(self, name, starting=50):
        self.name = name
        self.balance = starting

    def grant(self, monies):
        self.balance += monies

    def take(self, monies):
        self.balance -= monies
