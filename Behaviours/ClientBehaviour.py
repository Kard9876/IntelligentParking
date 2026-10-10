import math
import asyncio
import datetime

from spade.behaviour import OneShotBehaviour
import jsonpickle
from spade.message import Message
from utils.Info import Info
import time
import random
from utils.MessageTimeout import MessageTimeout
from colorama import Fore, Style

def give_preference (elems:list):
    total:float = 1.0

    probs = dict()
    for elem in elems:
        prob = round(random.uniform(0, min(total,0.5)), 2)
        probs[elem] = prob
        total -= prob

    retorno = {k: v for k, v in sorted(probs.items(), key=lambda item: item[1])}  # TODO verify
    return retorno

def calculate_cost(position, park_info, preferences, movement_importance, cost_importance, max_distance):
    distancia = math.sqrt(((position[0] - park_info["location"][0]) ** 2 + (position[1] - park_info["location"][1]) ** 2)) / max_distance

    lot = park_info["parking_lots"]
    custo = 0

    #for k, v in preferences.items():
    #    custo += next((lot['cost'] for lot in lot if lot['type'] == k), None) * v
    lots_cost = [lot['cost'] for lot in lot if lot['type'] == preferences]
    custo = math.inf

    if len(lots_cost) > 0:
        custo = min(lots_cost)

    # print(f"f: Distancia={distancia}")
    # print(f"f: Movement importance={movement_importance}")
    # print(f"f: Cost={custo}")
    # print(f"f: Cost importance={cost_importance}")
    return distancia * movement_importance + custo * cost_importance


def rank_parks(position, parks:dict, preferences, movement_importance, cost_importance, max_distance):
    custo = []

    for k, v in parks['parks'].items():
        custo_parque = calculate_cost(position, v['parking_lots'], preferences, movement_importance, cost_importance, max_distance)
        custo.append((k, custo_parque, v['status']))
        # print(f"Park Manager={k}, Park Rating={custo_parque}")
        # parks['parks'][k]['custo'] = calculate_cost(position, v, preferences,moviment_cost)

    """retorno = {
        k: v for k, v in sorted(parks['parks'].items(), key=lambda item: item[1]['custo'])
    }"""

    custo.sort(key=lambda item: item[1])

    return custo
    # expected values:
    # location=(x, y)
    # parking_lots = [{'type':  lot_type, 'cost':float}]


class ClientBehavior(OneShotBehaviour):
    async def on_end(self):
        await self.agent.stop()

    async def run(self):
        msg_timout = MessageTimeout()
        msg_timeout_val = msg_timout.get_timeout()

        max_attempts = self.agent.get('max_attempts')
        wait_new_parks = 10

        monthly_pass = self.agent.get('monthly_pass')

        success_value = False

        for attempt in range(max_attempts):
            general_manager = self.agent.get('general_manager_jid')
            request = Info("parks_request", {'nothing': 'nothing'})

            msg = Message(to=general_manager)
            msg.set_metadata("performative", "request")
            msg.body = jsonpickle.encode(request)

            await self.send(msg)

            msg = await self.receive(timeout=msg_timeout_val)

            if msg:
                performative = msg.get_metadata('performative')
                info = jsonpickle.decode(msg.body)

                info_type = info.get_info_type()
                info_data = info.get_data()

                if performative == 'inform' and info_type == 'parks_information':
                    if info_data['parks'] == {}:
                        print(Style.BRIGHT + Fore.RED + f"Agent {self.agent.jid} no available parks on attempt {attempt + 1}.")
                        # Wait to let parks become available again
                        await asyncio.sleep(self.agent.get('wait_between_attempts'))
                        continue

                    position = self.agent.get('location')
                    "Cada 1 tem uma probalidade que sumada da 1"
                    # preference = give_preference(["eletric", "gas", "woman", "disabled","common"])
                    preference = random.choice(["eletric", "gas", "woman", "disabled", "common", "scooter"])
                    bp = rank_parks(position, info_data, preference, self.agent.get("movement_importance"),
                                    self.agent.get("cost_importance"), self.agent.get("max_distance"))


                    if self.agent.get("select_best"):
                        jid, _, _ = bp[0]

                        body = Info("reserve_parking_lot", {"parking_lot_type": preference, 'reserve_list': True})

                        msg = Message(to=str(jid))
                        msg.set_metadata("performative", "propose")
                        msg.body = jsonpickle.encode(body)
                        await self.send(msg)

                        response = await self.receive(timeout=msg_timeout_val)

                        if not response:
                            print(Style.BRIGHT + Fore.LIGHTRED_EX + f"Eu {self.agent.jid} nao recebi resposta de {jid}")

                        else:
                            performative_response = response.get_metadata('performative')

                            if performative_response == 'accept_proposal':
                                info = jsonpickle.decode(response.body)
                                info_data = info.get_data()

                                if info_data["status"] == "ok":
                                    self.agent.parkChosenInfo = info_data
                                    print(Style.BRIGHT + Fore.BLUE + f"Eu {self.agent.jid} foi aceite {jid}")
                                else:
                                    #print(Style.BRIGHT + Fore.RED + f"Eu {self.agent.jid} não foi aceite {jid}")
                                    continue

                            elif performative_response == 'propose':
                                print(Style.BRIGHT + Fore.LIGHTGREEN_EX + f"Eu {self.agent.jid} estou na fila de espera de {jid}")

                                await asyncio.sleep(self.agent.get('waiting_list_wait_time'))

                                # Where everywhere else we assume assync comunication, here we need to check if message was received on time
                                # Sync communication
                                response_reserve = await self.receive(timeout=10)

                                if not response_reserve:
                                    print(Style.BRIGHT + Fore.LIGHTRED_EX + f"Eu {self.agent.jid} nao recebi resposta de {jid}")
                                    self.agent.parkChosenInfo = None

                                    cancel_park = Info("cancel_parking_lot", {'reserve_list': True})
                                    msg_cancel = Message(to=str(jid))
                                    msg_cancel.set_metadata("performative", "refuse_proposal")
                                    msg_cancel.body = jsonpickle.encode(cancel_park)

                                    await self.send(msg_cancel)

                                    continue

                                else:
                                    if response_reserve.get_metadata('performative') == 'accept_proposal':
                                        info = jsonpickle.decode(response_reserve.body)
                                        info_data = info.get_data()

                                        if info_data["status"] == "ok":
                                            self.agent.parkChosenInfo = info_data
                                            print(Style.BRIGHT + Fore.LIGHTYELLOW_EX + f"Eu {self.agent.jid} fui aceite por {jid} através da fila de espera")

                                        else:
                                            continue
                                    else:
                                        print(Style.BRIGHT + Fore.RED + f"ERROR: {performative}")
                    else:
                        self.agent.parkChosenInfo = None

                        for jid, _, status in bp:
                            if status == 'closed' and not monthly_pass:
                                continue

                            body = Info("reserve_parking_lot", {"parking_lot_type": preference, 'reserve_list': False})

                            msg = Message(to=str(jid))
                            msg.set_metadata("performative", "propose")
                            msg.body = jsonpickle.encode(body)
                            await self.send(msg)

                            response = await self.receive(timeout=msg_timeout_val)

                            if not response:
                                continue

                            performative_response = response.get_metadata('performative')

                            if performative_response == 'accept_proposal':
                                info = jsonpickle.decode(response.body)
                                info_data = info.get_data()

                                if info_data["status"] == "ok":
                                    self.agent.parkChosenInfo = info_data
                                    print(Style.BRIGHT + Fore.BLUE +f"Eu {self.agent.jid} foi aceite {jid}")
                                    break

                                else:
                                    continue

                            elif performative_response == 'refuse_proposal':
                                print(Style.BRIGHT + Fore.LIGHTRED_EX + f"Eu {self.agent.jid} nao foi aceite {jid}")

                            else:
                                print(Style.BRIGHT + Fore.RED + f"ERROR: {performative}")

                        if not self.agent.parkChosenInfo:
                            print(Style.BRIGHT + Fore.RED + f"Agent {self.agent.jid} can't find a place anywhere to park on attempt {attempt + 1}.")
                            await asyncio.sleep(self.agent.get('wait_between_attempts'))
                            continue

                    time_wait = random.uniform(5, 30)  # TODO alterar depois apenas teste
                    time_wait = round(time_wait, 2)
                    success_value = True
                    # Debug
                    # print(Style.BRIGHT + Fore.CYAN + f"Agente {self.agent.jid} vai ficar {time_wait} s no parque")

                    await asyncio.sleep(time_wait)

                    info = self.agent.parkChosenInfo

                    request = Info("free_parking_lot", {
                        "park_type": info["type"],
                        "park_number": info["number"]
                    })

                    msg = Message(to=str(info["agent"]))

                    msg.set_metadata("performative", "inform")
                    msg.body = jsonpickle.encode(request)

                    await self.send(msg)

                    preco = await self.receive(timeout=msg_timeout_val)

                    performative = preco.get_metadata('performative')
                    info_preco = jsonpickle.decode(preco.body)

                    info_type = info_preco.get_info_type()
                    info_data = info_preco.get_data()

                    if performative == "inform" and info_type == "park_payment":
                        print(Style.BRIGHT + Fore.CYAN + f"Agente {self.agent.jid} ficou no parque das {info_data['entry_time']} até " +
                                                         f"às {info_data['exit_time']}, pelo que pagou {info_data['cost']:.2f}€, dos quais " +
                                                         f"{info_data['fine_cost']:.2f}€ foram de multa")

                    else:
                        print(Style.BRIGHT + Fore.RED + f"ERROR: {performative}")

                    break
                else:
                    print(Style.BRIGHT + Fore.RED + f"ERROR: {performative}")

            else:
                print(Style.BRIGHT + Fore.RED + f"Nao recebi resposta do general manager na minha {attempt}ª tentativa")
                await asyncio.sleep(wait_new_parks)

        if success_value:
            print(Style.BRIGHT + Fore.LIGHTWHITE_EX + f"Cliente {self.agent.jid} terminou a sua execução com sucesso")
        else:
            print(Style.BRIGHT + Fore.LIGHTMAGENTA_EX + f"Cliente {self.agent.jid} terminou a sua execução com insucesso")
