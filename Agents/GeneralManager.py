from spade.agent import Agent

from Behaviours.GeneralManagerBehaviour import AvailablesParksBehaviour
from colorama import Fore, Style, init

class GeneralManagerAgent(Agent):
    async def setup(self):
        print(Style.BRIGHT + Fore.MAGENTA+f"General Manager {self.get('jid')} started")

        self.add_behaviour(AvailablesParksBehaviour())

