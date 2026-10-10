import asyncio

import jsonpickle
import datetime
import random
from colorama import Style, Fore

from spade.behaviour import CyclicBehaviour
from spade.message import Message

from utils.Info import Info
from utils.MessageTimeout import MessageTimeout


class ParkManagerBehaviour(CyclicBehaviour):
    async def on_start(self):
        self._wait_list = dict()
        self._lot_types_wait_list = dict()
        self._active = True
        self._open = True
        self._closed_time = []
        self._message_lock = asyncio.Lock()

        await self._update_park_open_status('open')

        asyncio.create_task(self._open_close_park())

    async def _update_park_open_status(self, status):
        general_manager = self.agent.get('general_manager_jid')

        inform_status = Info("park_open_status", {'status': status})

        msg = Message(to=general_manager)
        msg.set_metadata("performative", "inform")
        msg.body = jsonpickle.encode(inform_status)

        async with self._message_lock:
            await self.send(msg)


    async def _open_close_park(self):
        open_hours = self.agent.get('open_hours')
        close_hours = self.agent.get('close_hours')

        if close_hours != 0:
            while True:
                await asyncio.sleep(open_hours)
                self._open = False
                self._closed_time = [datetime.datetime.now(datetime.timezone.utc)] + self._closed_time

                await self._update_park_open_status('closed')
                print(Style.BRIGHT + Fore.RED + f"Park {self.agent.jid} will be closed for {close_hours} seconds.")

                await asyncio.sleep(close_hours)

                self._open = True

                await self._update_park_open_status('open')
                print(Style.BRIGHT + Fore.GREEN + f"Park {self.agent.jid} will be open for {open_hours} seconds.")

    async def _update_general_manager(self):
        general_manager = self.agent.get('general_manager_jid')
        parking_lots = self.agent.get('parking_lots')

        # expected value:
        # location=(x, y)
        location = self.agent.get('location')

        # Expected value:
        # parking_prices = {lot_type: cost}
        parking_prices = self.agent.get('parking_prices')

        # Expected value:
        # parking_lots_info = [{'type':  lot_type, 'cost':float}]
        parking_lots_info = []
        seen_types = []

        for k, v in parking_lots.items():
            lots = v['lots']
            zone_additional_cost = v['zone_additional_cost']

            # expected parking_lots data:
            # ['type':, 'number':, 'status':]
            for lot in lots:
                lot_type = lot['type']
                if lot_type not in seen_types:
                    seen_types.append(lot_type)

                    parking_lots_info.append({'type': lot_type, 'cost': parking_prices[lot_type] + zone_additional_cost})

        data = {
            'location': location,
            'parking_lots': parking_lots_info
        }

        mr = Info("info_parking_lots", data)

        msg = Message(to=general_manager)
        msg.set_metadata("performative", "subscribe")
        msg.body = jsonpickle.encode(mr)

        async with self._message_lock:
            await self.send(msg)

    async def _zone_subscribe(self, sender, data):
        parking_lots = self.agent.get('parking_lots')
        zone = data['zone']
        zone_parking_lots = data['parking_lots']
        zone_additional_cost = data['zone_additional_cost']

        parking_lots[zone] = {'agent': sender, 'lots': zone_parking_lots, 'zone_additional_cost': zone_additional_cost}

        self.agent.set('parking_lots', parking_lots)

        mr = Info("zone_subscribe", {'status': 'ok'})

        msg = Message(to=sender)
        msg.set_metadata("performative", "confirm")
        msg.body = jsonpickle.encode(mr)

        async with self._message_lock:
            await self.send(msg)

        await self._update_general_manager()

    async def _finish_reserve_parking_lot(self, data):
        client = data['client']
        monthly_pass = self.agent.get('monthly_pass_dict').get(client, False)
        selected_parking_lot = data['selected_parking_lot']
        zone = selected_parking_lot['zone']
        park_type = selected_parking_lot['type']
        park_number = selected_parking_lot['number']

        parking_lots = self.agent.get('parking_lots')

        v = parking_lots.get(zone)
        _ = v['agent']
        lots = v['lots']

        success = False

        if lots is not None:
            # expected parking_lots data:
            # ['type':, 'number':, 'status':]
            for lot in lots:
                if lot['type'] == park_type and lot['number'] == park_number and lot['status'] == 'waiting_reserve':
                    success = True
                    # Update parking lot status
                    lot['status'] = 'occupied'

                    lot['reserve_info'] = {
                        'client': client,
                        'time': datetime.datetime.now(datetime.timezone.utc),
                        'monthly_pass': monthly_pass
                    }

                    # Update parking lot status
                    self.agent.set('parking_lots', parking_lots)
                    break

        # I can't send a fail message because client already cancelled reserve, so sending messa would not only be useless as well as it would cause problems
        # with client's code
        if success:
            # dict1 | dict2 merges the two dictionaries
            inform_successful_reserve = Info("reserve_parking_lot", {'status': 'ok'} | selected_parking_lot)

            msg = Message(to=client)
            msg.set_metadata("performative", "accept_proposal")
            msg.body = jsonpickle.encode(inform_successful_reserve)

            async with self._message_lock:
                await self.send(msg)

    async def _reserve_parking_lot(self, sender, data):
        lot_type = data['parking_lot_type']
        wait_list = data['reserve_list']
        monthly_pass = self.agent.get('monthly_pass_dict').get(sender, False)

        parking_lots = self.agent.get('parking_lots')
        selected_parking_lot = None

        if self._active and (self._open or monthly_pass):
            for k, v in parking_lots.items():
                agent = v['agent']
                lots = v['lots']

                # expected parking_lots data:
                # ['type':, 'number':, 'status':]
                for lot in lots:
                    if lot['type'] == lot_type and lot['status'] == 'available':
                        # To make sure we don't accept two requests for the same parking lot
                        lot['status'] = 'waiting_reserve'
                        lot['client'] = sender

                        selected_parking_lot = {
                            'agent': agent,
                            'type': lot_type,
                            'number': lot['number'],
                            'zone': k
                        }

                        # Inform agent that the parking lot is being reserved
                        park_data = {
                            'park_type': lot_type,
                            'park_number': lot['number'],
                            'client': sender,
                            'selected_parking_lot': selected_parking_lot,
                            'monthly_pass': monthly_pass
                        }

                        request_parking_lot = Info("reserve_parking_lot", park_data)

                        msg_zone_agent = Message(to=agent)
                        msg_zone_agent.set_metadata("performative", "request")
                        msg_zone_agent.body = jsonpickle.encode(request_parking_lot)
                        await self.send(msg_zone_agent)

                        break

                if selected_parking_lot is not None:
                    break

        if selected_parking_lot is None:
            if wait_list:
                self._wait_list[sender] = data
                lot_type_wait_list = self._lot_types_wait_list.get(lot_type, [])
                lot_type_wait_list.append(sender)
                self._lot_types_wait_list[lot_type] = lot_type_wait_list

                inform_reserve = Info("reserve_parking_lot", {'status': 'reserve'})

                msg = Message(to=sender)
                msg.set_metadata("performative", "propose")
                msg.body = jsonpickle.encode(inform_reserve)

                async with self._message_lock:
                    await self.send(msg)

            else:
                inform_failed_reserve = Info("reserve_parking_lot", {'status': 'fail'})

                msg = Message(to=sender)
                msg.set_metadata("performative", "refuse_proposal")
                msg.body = jsonpickle.encode(inform_failed_reserve)

                async with self._message_lock:
                    await self.send(msg)

    async def _free_parking_lot(self, data):
        zone = data['zone']
        park_type = data['park_type']
        park_number = data['park_number']

        parking_lots = self.agent.get('parking_lots')

        v = parking_lots.get(zone)
        _ = v['agent']
        lots = v['lots']
        zone_additional_cost = v['zone_additional_cost']
        parking_prices = self.agent.get('parking_prices')

        cost_per_second = parking_prices[park_type] + zone_additional_cost

        if lots is not None:
            # expected parking_lots data:
            # ['type':, 'number':, 'status':]
            for lot in lots:
                if lot['type'] == park_type and lot['number'] == park_number:
                    lot['status'] = 'available'
                    del lot['client']

                    reserve_info = lot.pop('reserve_info')
                    client = reserve_info['client']
                    monthly_pass = self.agent.get('monthly_pass_dict').get(client, False)
                    entry_time = reserve_info['time']
                    cur_time = datetime.datetime.now(datetime.timezone.utc)

                    # Estamos a tratar os segundos como horas apenas para não obter valores de custo muito pequenos
                    total_time = (cur_time - entry_time).total_seconds()
                    total_cost = round(cost_per_second * total_time, 2)

                    fine_cost = 0.00

                    if not monthly_pass:
                        total_nights = len(list(filter(lambda x: x > entry_time, self._closed_time)))
                        fine_cost = round(total_nights * self.agent.get('fine_cost'), 2)
                        total_cost = round(total_cost + fine_cost, 2)

                    inform_reserve = Info("park_payment", {'cost': total_cost, 'entry_time': entry_time.isoformat(), 'exit_time': cur_time.isoformat(), 'fine_cost': fine_cost})

                    msg = Message(to=client)
                    msg.set_metadata("performative", "inform")
                    msg.body = jsonpickle.encode(inform_reserve)

                    async with self._message_lock:
                        await self.send(msg)

                    self.agent.set('parking_lots', parking_lots)
                    break

    async def _cancel_reserve_parking_lot(self, sender):
        print(Style.BRIGHT + Fore.RED + f"Canceling reserve from {sender}")
        try:
            reserve_data = self._wait_list.pop(sender)
            self._lot_types_wait_list[reserve_data['parking_lot_type']].remove(sender)
        except Exception as e:
            print(e)
            pass
        finally:
            parking_lots = self.agent.get('parking_lots')

            found = False

            for k, v in parking_lots.items():
                lots = v['lots']

                # expected parking_lots data:
                # ['type':, 'number':, 'status':]
                for lot in lots:
                    if lot['status'] != 'waiting_reserve' and lot.get('client', None) == sender:
                        lot['status'] = 'available'
                        del lot['client']

                        found = True
                        break

                if found:
                    break

    async def _update_park_status(self, status):
        general_manager = self.agent.get('general_manager_jid')

        inform_status = Info("park_status", {'status': status})

        msg = Message(to=general_manager)
        msg.set_metadata("performative", "inform")
        msg.body = jsonpickle.encode(inform_status)

        async with self._message_lock:
            await self.send(msg)

    async def _park_availability(self):
        min_timeout = self.agent.get('park_min_timeout')
        max_timeout = self.agent.get('park_max_timeout')

        timeout = random.randint(min_timeout, max_timeout)

        print(Style.BRIGHT + Fore.RED + f"Park {self.agent.jid} found a problem and will be unavailable for {timeout} seconds.")
        await asyncio.sleep(timeout)

        self._active = True
        print(Style.BRIGHT + Fore.GREEN + f"Park {self.agent.jid} fixed its problem.")
        await self._update_park_status('available')

    async def _manage_wait_list(self):
        parking_lots = self.agent.get('parking_lots')

        for k, v in parking_lots.items():
            _ = v['agent']
            lots = v['lots']

            # expected parking_lots data:
            # ['type':, 'number':, 'status':]
            for lot in lots:
                if lot['status'] == 'available':
                    waiting_list = self._lot_types_wait_list.get(lot['type'], [])

                    for i in range(len(waiting_list)):
                        client = waiting_list[i]
                        if self._open or self.agent.get('monthly_pass_dict').get(client, False):
                            client = waiting_list.pop(i)

                            self._lot_types_wait_list[lot['type']] = waiting_list

                            reserve_data = self._wait_list.pop(client)

                            await self._reserve_parking_lot(client, reserve_data)

                            break

    async def run(self):
        unavailable_chance = self.agent.get('unavailable_chance')

        if self._active:
            if random.random() < unavailable_chance:
                self._active = False
                await self._update_park_status('unavailable')

                asyncio.create_task(self._park_availability())

        if self._active:
            await self._manage_wait_list()

        msg_timout = MessageTimeout()
        msg_timeout_val = msg_timout.get_timeout()

        msg = await self.receive(timeout=msg_timeout_val)

        if msg:
            performative = msg.get_metadata("performative")
            info = jsonpickle.decode(msg.body)

            info_type = info.get_info_type()
            info_data = info.get_data()

            match performative:
                case 'subscribe':
                    if info_type == "zone_subscribe":
                        await self._zone_subscribe(str(msg.sender), info_data)
                    else:
                        print(Style.BRIGHT+Fore.RED+f'Unknown message type received by {self.agent.jid} from {str(msg.sender)}: {info_type}')

                case 'propose':
                    if info_type == "reserve_parking_lot":
                        await self._reserve_parking_lot(str(msg.sender), info_data)
                    else:
                        print(Style.BRIGHT+Fore.RED+f'Unknown message type received by {self.agent.jid} from {str(msg.sender)}: {info_type}')

                case 'inform':
                    if info_type == "free_parking_lot":
                        await self._free_parking_lot(info_data)
                    else:
                        print(Style.BRIGHT+Fore.RED+f'Unknown message type received by {self.agent.jid} from {str(msg.sender)}: {info_type}')

                case 'confirm':
                    if info_type == "reserve_parking_lot":
                        await self._finish_reserve_parking_lot(info_data)
                    else:
                        print(Style.BRIGHT+Fore.RED+f'Unknown message type received by {self.agent.jid} from {str(msg.sender)}: {info_type}')

                case 'refuse_proposal':
                    if info_type == "cancel_parking_lot":
                        await self._cancel_reserve_parking_lot(str(msg.sender))
                    else:
                        print(Style.BRIGHT + Fore.RED + f'Unknown message type received by {self.agent.jid} from {str(msg.sender)}: {info_type}')

                case _:
                    print(Style.BRIGHT+Fore.RED+f'Unknown performative received by {self.agent.jid} from {str(msg.sender)}: {performative}')

        else:
            print(Style.BRIGHT+Fore.RED+f"{self.agent.jid} didn't receive any message in an util timeout")
            self.kill()
            return
