import uuid
from enum import Enum, auto

from .player import Player
from .util import partition

from .logs import getLogger
logger = getLogger()

class GameTypes(Enum):
    OVER_UNDER      = 0
    WIN_LOSE        = auto()
    CLOSEST_WINS    = auto()

_BETS_BY_TYPE = {}
def bind_game(gt: GameTypes, *nicks):
    def decorator(cls):
        setattr(cls, "GAME_TYPE", gt)

        _BETS_BY_TYPE[gt.value] = (cls, nicks)
        return cls
    return decorator

class BetException(Exception):
    pass

# TODO: Metaclass
class Bet:
    def __init__(self, stmt, /):
        self.id = uuid.uuid4()
        self.statement = stmt

        self.locked = False

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def addPlayer(self, player, wager, stake):
        pass

    def next(self, information):
        pass

    @staticmethod
    def choices():
        # Convert list of lists of nicknames to a flat list of valid game
        # nicknames
        choices = sum([list(*nicks) for _, *nicks in _BETS_BY_TYPE.values()], [])
        logger.debug(choices)
        return choices

    @classmethod
    def newBet(cls, gtnick, *args, **kwargs):
        logger.debug("Finding sublcass for {}".format(gtnick))

        subcls = None
        for _subcls, nicks in _BETS_BY_TYPE.values():
            if gtnick in nicks:
                subcls = _subcls
                break

        if subcls is None:
            raise BetException("Invalid game type specified '{}'".format(gtnick))
        return subcls(*args, **kwargs)

class BinaryBet(Bet):
    TRUTHY_KEYWORDS = []
    FALSEY_KEYWORDS = []

    @staticmethod
    def _cast_keyword(_kw):
        kw = _kw.lower()
        VALID_KEYWORDS = TRUTHY_KEYWORDS + FALSEY_KEYWORDS

        if kw not in VALID_KEYWORDS:
            raise BetException("'{}' is not a valid keyword for {}".format(
                _kw, self.__class__.__name__))

        return kw in TRUTHY_KEYWORDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.truthy = {}
        self.falsey = {}

    def addPlayer(self, player, stake, wager):
        super().addPlayer()
        wager = self._cast_keyword(wager)
        self._addPlayer(player, stake, wager)

    def _addPlayer(self, player, stake, wager: bool):

        # Avoid duplication
        record = self.truthy.pop(player.name, None)
        record = self.falsey.pop(player.name, record)
        if record is not None:
            _, original_stake = record
            player.grant(original_stake)

        # The player should resubmit the bet now that they have their wager
        # returned
        if player.balance < stake:
            raise BetException("Balance too low; funds returned")

        player.take(stake)

        pool = self.truthy if wager else self.falsey
        pool[player.name] = (player, stake)

    def end(self, result):
        super().end()
        result = self._cast_keyword(result)
        return self._end(result)

    def _end(self, result: bool):
        deltas = []

        winners = self.truthy if result else self.falsey
        losers = self.falsey if result else self.truthy

        # Take from losers and add up
        lsum = 0
        for (player, stake) in losers.values():
            lsum += stake
            deltas.append((player, -stake))

        # Distribute to winners
        wsum = sum(map(lambda v: v[1], winners.values()))
        for (player, stake) in winners.values():
            player.grant(stake)
            winnings = int(lsum * (stake / wsum))
            player.grant(winnings)

            deltas.append((player, winnings))

        # TODO: shuffle order
        return deltas

@bind_game(GameTypes.OVER_UNDER, "OU", "overunder")
class OverUnderBet(BinaryBet):
    TRUTHY_KEYWORDS = ["o", "over"]
    FALSEY_KEYWORDS = ["u", "under"]

@bind_game(GameTypes.WIN_LOSE, "WL", "winlose")
class WinLoseBet(BinaryBet):
    TRUTHY_KEYWORDS = ["w", "win"]
    FALSEY_KEYWORDS = ["l", "lose"]

@bind_game(GameTypes.CLOSEST_WINS, "CW", "closestwins")
class ClosestWinsBet(Bet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.betters = {}

    def addPlayer(self, player, stake, wager: int):
        record = self.betters.pop(player.name, None)
        if record is not None:
            _, original_stake, *_ = record
            player.grant(original_stake)

        if player.balance < stake:
            raise BetException("Balance too low; funds returned")

        player.take(stake)
        self.betters[player.name] = (player, stake, target)

    def end(self, result: int):
        deltas = []

        # map betters to a list of offsets from result
        min_ofs = min(map(lambda record: abs(result - record[2]),
                self.betters.values()))

        # Get winners and filters
        winners, losers = partition(
                lambda record: min_ofs == abs(result - record[2]),
                self.betters.values())

        # Get sums
        lsum = 0
        for player, stake, _ in losers:
            lsum += stake
            deltas.append((player, -stake))

        # restore winners funds and distribute
        wsum = sum(map(lambda record: record[2], winners))
        for player, stake, _ in winners:
            player.grant(stake)
            winnings = int(lsum * (stake / wsum))
            player.grant(winnings)
            deltas.append((player, winnings))

        # TODO: shuffle order
        return deltas

