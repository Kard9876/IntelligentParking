from colorama import Style, Fore
from spade.behaviour import CyclicBehaviour
import jsonpickle
from spade.message import Message
from utils.Info import Info

class AvailablesParksBehaviour(CyclicBehaviour):
    async def on_start(self):
        self.available_parks = dict()
        self.unavailable_parks = dict()
        self.unavailable_parks_name = list()

    async def run(self):
        msg = await self.receive(timeout=10)
        if msg:
            p = msg.get_metadata('performative')
            request = jsonpickle.decode(msg.body)
            info_type = request.get_info_type()

            if p == 'subscribe':
                if msg.sender not in self.unavailable_parks_name:
                    val = self.available_parks.get(msg.sender, {'status': 'open', 'parking_lots': []})
                    val['parking_lots'] = request.get_data()
                    self.available_parks[msg.sender] = val

                else:
                    val = self.unavailable_parks.get(msg.sender, {'status': 'open', 'parking_lots': []})
                    val['parking_lots'] = request.get_data()
                    self.unavailable_parks[msg.sender] = val

                # expected values:
                # location=(x, y)
                # parking_lots = [{'type':  lot_type, 'cost':float}]

            elif p == 'request':
                parks = {}

                for k, v in self.available_parks.items():
                    if v['parking_lots'] != []:
                        parks[k] = v

                response = Message(to=str(msg.sender))
                response.set_metadata("performative", "inform")
                mr = Info("parks_information", {"parks": parks})
                response.body = jsonpickle.encode(mr)

                await self.send(response)

            elif p == 'inform':
                if info_type == "park_status":
                    info_data = request.get_data()

                    if info_data["status"] == "unavailable":
                        if msg.sender not in self.unavailable_parks_name:
                            self.unavailable_parks_name.append(msg.sender)

                        park_info = self.available_parks.pop(msg.sender, None)

                        if park_info is not None:
                            self.unavailable_parks[msg.sender] = park_info

                    elif info_data["status"] == "available":
                        if msg.sender in self.unavailable_parks_name:
                            self.unavailable_parks_name.remove(msg.sender)

                        park_info = self.unavailable_parks.pop(msg.sender, None)

                        if park_info is not None:
                            self.available_parks[msg.sender] = park_info

                elif info_type == 'park_open_status':
                    info_data = request.get_data()
                    status = info_data["status"]

                    if msg.sender not in self.unavailable_parks_name:
                        val = self.available_parks.get(msg.sender, {'status': 'open', 'parking_lots': []})
                        val['status'] = status
                        self.available_parks[msg.sender] = val

                    else:
                        val = self.unavailable_parks.get(msg.sender, {'status': 'open', 'parking_lots': []})
                        val['status'] = status
                        self.unavailable_parks[msg.sender] = val

            else:
                print(Style.BRIGHT+Fore.RED+"Agent {}:".format(str(self.agent.jid)) + " Message not understood!")

    async def on_end(self):
        pass
