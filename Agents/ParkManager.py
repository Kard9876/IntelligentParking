import spade

from Behaviours.ParkManagerBehaviour import ParkManagerBehaviour
from colorama import Fore, Style, init

class ParkManagerAgent(spade.agent.Agent):
    async def setup(self):
        print(Style.BRIGHT + Fore.YELLOW + f"ParkManagerAgent {self.get('jid')} started")

        b1 = ParkManagerBehaviour()
        self.add_behaviour(b1)
