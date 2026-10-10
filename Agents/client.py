import spade
from spade.agent import Agent
from Behaviours.ClientBehaviour import ClientBehavior
from colorama import Fore, Style, init

class ClientAgent(Agent):
    async def setup(self):
        print(Style.BRIGHT + Fore.BLUE + f"Client {self.jid}")
        self.add_behaviour(ClientBehavior())
