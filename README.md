# Gooble

A discord betting bot for the bois

* `pip install -r requirements.txt`
* `make run`

## TODO:
* Add a command to list all open bets/games for the current House.
* Add ability to get a set of all the bets a players is involved in (probably just extend the stat command)
* Add command to reset/cancel a player, house, or bet
* Automated testing cause we saucy like that
* General help command for bot usage (probably should move away from argparse
  and just use the default arg parsing discord py has)

* Add more details to the Player class.
  * Total winnings
  * Total losses
  * Total bets won/lost, percentages
  * Report these on the `$stat --player` embed.

* Leaderboards
  * Most money
  * Most wins
  * Most losses

* Allow random wagers (leave it to chance).

* 

* Add role-based protections for certain commands.
  * `$giftall` should be restricted to House staff.
  * Add middleware to validate permissions before handling the command.

* Allow users to enter a (fixed stake) binary bet using reaction emojis.