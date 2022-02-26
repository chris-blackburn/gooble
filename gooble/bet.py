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
    YES_NO          = auto()

_BETS_BY_TYPE = {}
def bind_game(name, gt: GameTypes, *nicks):
    def decorator(cls):
        setattr(cls, "GAME_TYPE", gt)
        setattr(cls, "FRIENDLY_NAME", name)

        _BETS_BY_TYPE[gt.value] = (cls, nicks)
        return cls
    return decorator

class BetException(Exception):
    pass

# TODO: Metaclass
class Bet:
    def __init__(self, stmt):
        self.id = uuid.uuid4()
        self.statement = stmt

    def addPlayer(self, player, wager, stake):
        raise BetException("Not implemented")

    def end(self, result):
        raise BetException("Not implemented")

    @staticmethod
    def sortDeltas(deltas):
        # Sort by winnings
        deltas.sort(key=lambda delta: delta[1])

    @staticmethod
    def choices():
        # Convert list of lists of nicknames to a flat list of valid game
        # nicknames
        choices = sum([list(*nicks) for _, *nicks in _BETS_BY_TYPE.values()], [])
        logger.debug(choices)
        return choices

    @staticmethod
    def newBet(gtnick, *args, **kwargs):
        logger.debug("Finding sublcass for {}".format(gtnick))

        for subcls, nicks in _BETS_BY_TYPE.values():
            if gtnick.lower() in [n.lower() for n in nicks]:
                return subcls(*args, **kwargs)

        raise BetException(
                "Invalid game type specified '{}'".format(gtnick))

class BinaryBet(Bet):
    TRUTHY_KEYWORDS = []
    FALSEY_KEYWORDS = []

    @classmethod
    def _cast_keyword(cls, _kw: str) -> bool:
        kw = _kw.lower()
        VALID_KEYWORDS = cls.TRUTHY_KEYWORDS + cls.FALSEY_KEYWORDS

        if kw not in VALID_KEYWORDS:
            raise BetException(
                    "'{}' is not a valid wager for {}; try {}".format(
                        _kw, cls.FRIENDLY_NAME, VALID_KEYWORDS))

        return kw in cls.TRUTHY_KEYWORDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.truthy = {}
        self.falsey = {}

    def addPlayer(self, player, stake, wager):
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

        self.sortDeltas(deltas)
        return deltas

@bind_game("Over/Under", GameTypes.OVER_UNDER, "ou", "overunder")
class OverUnderBet(BinaryBet):
    TRUTHY_KEYWORDS = ["o", "over"]
    FALSEY_KEYWORDS = ["u", "under"]

@bind_game("Win/Lose", GameTypes.WIN_LOSE, "wl", "winlose")
class WinLoseBet(BinaryBet):
    TRUTHY_KEYWORDS = ["w", "win"]
    FALSEY_KEYWORDS = ["l", "lose"]

@bind_game("Yes/No", GameTypes.YES_NO, "yn", "yesno")
class WinLoseBet(BinaryBet):
    TRUTHY_KEYWORDS = ["y", "yes"]
    FALSEY_KEYWORDS = ["n", "no"]

@bind_game("Closest Wins", GameTypes.CLOSEST_WINS, "cw", "closestwins")
class ClosestWinsBet(Bet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.betters = {}

    @classmethod
    def _validate_input(cls, value: str) -> int:
        try:
            return int(value)
        except ValueError:
            raise BetException(
                    "'{}' is not a valid wager for {}; use an integer".format(
                        value, cls.FRIENDLY_NAME))

    def addPlayer(self, player, stake, wager: str):
        wager = self._validate_input(wager)
        return self._addPlayer(player, stake, wager)

    def _addPlayer(self, player, stake, wager: int):
        record = self.betters.pop(player.name, None)
        if record is not None:
            _, original_stake, *_ = record
            player.grant(original_stake)

        if player.balance < stake:
            raise BetException("Balance too low; funds returned")

        player.take(stake)
        self.betters[player.name] = (player, stake, wager)

    def end(self, result: str):
        result = self._validate_input(result)
        return self._end(result)

    def _end(self, result: int):
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

        self.sortDeltas(deltas)
        return deltas

