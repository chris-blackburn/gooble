# Gooble

A discord betting bot for the bois

* `pip install -r requirements.txt`
* `make run`

## TODO:
* Add a --games flag to bet to list all game types and descriptions
* Add command to get the status of a bet (and to list active bets)
* Add ability to get a set of all the bets a players is involved in (probably
  just extend the stat command)
* Add command to reset/cancel a player, house, or bet
* Make a pot of money in a house such that if there are no winners in a bet,
  the lost money has somwhere to go (instead of the void)
* Automated testing cause we saucy like that
* General help command for bot usage (probably should move away from argparse
  and just use the default arg parsing discord py has)
