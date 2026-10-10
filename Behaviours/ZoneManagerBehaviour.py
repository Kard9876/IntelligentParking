import jsonpickle
from colorama import Style, Fore

from spade.behaviour import CyclicBehaviour
from spade.message import Message

from utils.Info import Info
from utils.MessageTimeout import MessageTimeout


class ZoneManagerBehaviour(CyclicBehaviour):
    async def _subscribe(self):
        park_manager = self.agent.get('park_manager_jid')
        parking_lots = self.agent.get('parking_lots')
        zone_additional_cost = self.agent.get('zone_additional_cost')
        zone = self.agent.get('zone')

        mr = Info("zone_subscribe", {'zone': zone, 'parking_lots': parking_lots, 'zone_additional_cost': zone_additional_cost})

        msg = Message(to=park_manager)
        msg.set_metadata("performative", "subscribe")
        msg.body = jsonpickle.encode(mr)
        await self.send(msg)

        msg_timout = MessageTimeout()
        msg_timeout_val = msg_timout.get_timeout()
        msg = await self.receive(timeout=msg_timeout_val)

        if not msg:
            print(f"{self.agent.jid} didn't receive any message in an util timeout")

        performative = msg.get_metadata("performative")
        if performative != "confirm":
            print(Style.BRIGHT + Fore.RED + f"{self.agent.jid} received wrong performative: {performative}")

    async def _manage_parking_lots(self, data, status):
        # expected parking_lots data:
        # [{'type': ,'number': ,'status': }]
        park_type = data['park_type']
        park_number = data['park_number']

        parking_lots = self.agent.get('parking_lots')

        for lot in parking_lots:
            if lot['type'] == park_type and lot['number'] == park_number:
                lot['status'] = status
                break

        self.agent.set('parking_lots', parking_lots)

    async def _reserve_parking_lot(self, data):
        await self._manage_parking_lots(data, 'occupied')

        request = Info("reserve_parking_lot", data)

        park_manager = self.agent.get('park_manager_jid')

        msg = Message(to=park_manager)
        msg.set_metadata("performative", "confirm")
        msg.body = jsonpickle.encode(request)
        await self.send(msg)

    async def _free_parking_lot(self, data):
        await self._manage_parking_lots(data, 'available')

        zone = self.agent.get('zone')
        request = Info("free_parking_lot", {'zone': zone} | data)

        park_manager = self.agent.get('park_manager_jid')

        msg = Message(to=park_manager)
        msg.set_metadata("performative", "inform")
        msg.body = jsonpickle.encode(request)
        await self.send(msg)

    async def on_start(self):
        await self._subscribe()

    async def run(self):
        msg_timout = MessageTimeout()
        msg_timeout_val = msg_timout.get_timeout()

        msg = await self.receive(timeout=msg_timeout_val)

        if msg:
            performative = msg.get_metadata("performative")
            info = jsonpickle.decode(msg.body)

            info_type = info.get_info_type()
            info_data = info.get_data()

            match performative:
                case 'request':
                    if info_type == "reserve_parking_lot":
                        await self._reserve_parking_lot(info_data)
                    else:
                        print(
                            Style.BRIGHT + Fore.RED + f'Unknown message type received by {self.agent.jid} from {msg.sender}: {info_type}')
                case 'inform':
                    if info_type == "free_parking_lot":
                        await self._free_parking_lot(info_data)
                    else:
                        print(
                            Style.BRIGHT + Fore.RED + f'Unknown message type received by {self.agent.jid} from {msg.sender}: {info_type}')
                case _:
                    print(
                        Style.BRIGHT + Fore.RED + f'Unknown performative received by {self.agent.jid} from {msg.sender}: {performative}')

        else:
            print(Style.BRIGHT + Fore.RED + f"{self.agent.jid} didn't receive any message in an util timeout")
            self.kill()
            return
