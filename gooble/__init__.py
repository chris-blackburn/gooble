DEFAULT_PREFIX = "$"
DEFAULT_COLOR = 0xffd700

from .gooble import Gooble

# TODO:
# 1. Add a --games flag to bet to list all game types and descriptions
# 2. Add command to get the status of a bet (and to list active bets)
# 3. Add ability to get a set of all the bets a players is involved in (probably
#    just extend the stat command)
# 4. Add command to reset/cancel a player, house, or bet
# 5. Make a pot of money in a house such that if there are no winners in a bet,
#    the lost money has somwhere to go (instead of the void)
# 6. Automated testing cause we saucy like that
# 7. General help command for bot usage
