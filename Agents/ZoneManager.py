import spade

from Behaviours.ZoneManagerBehaviour import ZoneManagerBehaviour
from colorama import Fore, Style, init

class ZoneManagerAgent(spade.agent.Agent):
    async def setup(self):
        print(Style.BRIGHT + Fore.GREEN + f"ZoneManagerAgent {self.get('jid')} started")

        b1 = ZoneManagerBehaviour()
        self.add_behaviour(b1)
