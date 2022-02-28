import unittest

from gooble import House
from gooble.bet import BetException

class TestClosestWins(unittest.TestCase):

    def setUp(self):
		# Create a House and some players.
        self.house = House("123")

        # Create some players using the factory method.
        self.house.getPlayer("Player1", 100)
        self.house.getPlayer("Player2", 500)
        self.house.getPlayer("Player3", 250)

        # Create a Closest Wins bet. This bet will become the
        # 'running' bet.
        self.house.newBet("cw", "This is a test bet!")

    def test_invalid_bet(self):

        # Get the Player with 100 points.
        player = self.house.players["Player1"]

        # Use the player to place a bet of 150.
        with self.assertRaises(BetException):
            self.house.running.addPlayer(player, 150, 20)

    def test_payout(self):

        # Add some stakes.
        players = self.house.players
        self.house.running.addPlayer(players["Player1"], 50, 20)
        self.house.running.addPlayer(players["Player2"], 150, 85)
        self.house.running.addPlayer(players["Player3"], 200, 37)

        # Conclude the bet and collect the deltas.
        _, deltas = self.house.endBet(self.house.running.id, 50)

        # Find each Player in the deltas and confirm that they lost
        # or won the correct amount.
        player1Tuple = self._find_tuple_for_player_in_deltas(deltas, "Player1")
        player2Tuple = self._find_tuple_for_player_in_deltas(deltas, "Player2")
        player3Tuple = self._find_tuple_for_player_in_deltas(deltas, "Player3")

        self.assertEqual(player1Tuple[1], -50)
        self.assertEqual(player2Tuple[1], -150)
        self.assertEqual(player3Tuple[1], 200)

    def _find_tuple_for_player_in_deltas(self, deltas, playerId):
        return next((x for x in deltas if x[0].id == playerId), None)


if __name__ == '__main__':
    unittest.main()