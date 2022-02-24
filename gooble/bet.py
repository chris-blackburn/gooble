import uuid

from .player import Player

class BetException(Exception):
    pass

class Bet:
    def __init__(self, stmt=""):
        self.id = uuid.uuid4()
        self.statement = stmt

        self.yay = {}
        self.nay = {}

    def addPlayer(self, player, amount, isyay):

        # Avoid duplication
        record = self.yay.pop(player.name, None)
        record = self.nay.pop(player.name, record)
        if record is not None:
            _, amount_bet = record
            player.grant(amount_bet)

        if player.balance < amount:
            # TODO: put player back in original bet
            raise BetException("Get mo money")

        player.take(amount)
        if isyay:
            self.yay[player.name] = (player, amount)
            return

        self.nay[player.name] = (player, amount)

    def end(self, isyay):
        deltas = []

        winners = self.yay if result else self.nay
        losers = self.nay if result else self.yay

        # Take from losers and add up
        lsum = 0
        for (player, amount) in losers.values():
            lsum += amount
            deltas.append((player, -amount))

        # Distribute to winners
        wsum = sum(map(lambda v: v[1], winners.values()))
        for (player, amount) in winners.values():
            player.grant(amount)

            winnings = int(lsum * (amount / wsum))
            player.grant(winnings)

            deltas.append((player, winnings))

        # TODO: change order
        return deltas
