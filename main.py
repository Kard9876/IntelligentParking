import asyncio
import sys
import random
import time
import spade
import math

from Agents.ParkManager import ParkManagerAgent
from Agents.ZoneManager import ZoneManagerAgent
from Agents.client import ClientAgent
from Agents.GeneralManager import GeneralManagerAgent

def set_seeds(seed):
    random.seed(seed)

async def main(args):
    set_seeds(777)

    general_manager_jid = "general_mananger@localhost"

    n_parks = 10

    min_parking_zones = 3
    max_parking_zones = 7

    min_parking_lots = 5
    max_parking_lots = 10

    min_x_location = 0
    max_x_location = 1000
    min_y_location = 0
    max_y_location = 1000

    max_distance = math.sqrt(((max_x_location - min_x_location) ** 2 + (max_y_location - min_y_location) ** 2))

    min_parking_lot_cost = 0.1
    max_parking_lot_cost = 0.8

    min_additional_zone_cost = 0.1
    max_additional_zone_cost = 0.2

    park_min_timeout = 5
    park_max_timeout = 15

    min_unavailable_chance = 0.001
    max_unavailable_chance = 0.05

    zone_manager_agents = []
    park_manager_agents = []

    day_time = 24
    min_open_hours = 16
    max_open_hours = 24

    min_fine_cost = 10.0
    max_fine_cost = 30.0

    parking_types = ['eletric', 'gas', 'disabled', 'woman', 'common', "scooter"]

    num_clients = 2000

    monthly_pass_dict = {}
    monthly_pass_probability = 0.1

    for i in range(num_clients):
        client_jid = f"client{i}@localhost"
        monthly_pass_dict[client_jid] = random.random() < monthly_pass_probability

    for i in range(n_parks):
        park_manager_jid = f"park_manager_{i}@localhost"

        x = random.randint(min_x_location, max_x_location)
        y = random.randint(min_y_location, max_y_location)
        location = (x, y)

        open_hours = random.randint(min_open_hours, max_open_hours)
        close_hours = day_time - open_hours

        fine_cost = random.uniform(min_fine_cost, max_fine_cost)

        # Expected value:
        # parking_prices = {lot_type: cost}
        parking_prices = {}

        for parking_type in parking_types:
            parking_prices[parking_type] = random.uniform(min_parking_lot_cost, max_parking_lot_cost)

        n_zones = random.randint(min_parking_zones, max_parking_zones)
        for j in range(n_zones):
            zone_manager_jid = f"zone_manager_{i}_{j}@localhost"
            zone_additional_cost = random.uniform(min_additional_zone_cost, max_additional_zone_cost)

            zone = f"zone_{i}_{j}"

            # expected parking_lots data:
            # [{'type': ,'number': ,'status': }]
            n_parking_lots = random.randint(min_parking_lots, max_parking_lots)
            parking_lots = []

            for k in range(n_parking_lots):
                parking_type = random.choice(parking_types)
                parking_lots.append({
                    'type': parking_type,
                    'number': k,
                    'status': 'available'
                })

            zone_manager_agent = ZoneManagerAgent(zone_manager_jid, "NO_PASSWORD")
            zone_manager_agent.set('jid', zone_manager_jid)
            zone_manager_agent.set('park_manager_jid', park_manager_jid)
            zone_manager_agent.set('parking_lots', parking_lots)
            zone_manager_agent.set('zone_additional_cost', zone_additional_cost)
            zone_manager_agent.set('zone', zone)

            zone_manager_agents.append(zone_manager_agent)

        unavailable_chance = random.uniform(min_unavailable_chance, max_unavailable_chance)

        park_manager_agent = ParkManagerAgent(park_manager_jid, "NO_PASSWORD")
        park_manager_agent.set('jid', park_manager_jid)
        park_manager_agent.set('general_manager_jid', general_manager_jid)
        park_manager_agent.set('parking_lots', {})
        park_manager_agent.set('location', location)
        park_manager_agent.set('parking_prices', parking_prices)
        park_manager_agent.set('unavailable_chance', unavailable_chance)
        park_manager_agent.set('park_min_timeout', park_min_timeout)
        park_manager_agent.set('park_max_timeout', park_max_timeout)
        park_manager_agent.set('open_hours', open_hours)
        park_manager_agent.set('close_hours', close_hours)
        park_manager_agent.set('fine_cost', fine_cost)
        park_manager_agent.set('monthly_pass_dict', monthly_pass_dict)

        park_manager_agents.append(park_manager_agent)

    # Uncomment line when general_manager_agent is available
    general_manager_agent = GeneralManagerAgent(general_manager_jid, "NO_PASSWORD")
    general_manager_agent.set('jid', general_manager_jid)

    await general_manager_agent.start()

    # Start all park agents
    for park_manager in park_manager_agents:
        await park_manager.start()

    # Start all zone manager agents
    for zone_manager in zone_manager_agents:
        await zone_manager.start()


    clients_agents = []

    min_movement_importance = 0.1
    max_movement_importance = 1.0

    min_cost_importance = 0.1
    max_cost_importance = 1.0

    min_max_attemps = 1
    max_max_attemps = 5

    min_wait_between_attempts = 5
    max_wait_between_attempts = 15

    min_waiting_list_wait_time = 5
    max_waiting_list_wait_time = 10

    #time.sleep(10)

    # Means that 20% of all clients will like to reserve a lot only for the best park
    select_best_probability = 0.2

    for i in range(num_clients):
        client_jid = f"client{i}@localhost"
        client_agent = ClientAgent(client_jid, "NO_PASSWORD")

        x = random.randint(min_x_location, max_x_location)
        y = random.randint(min_y_location, max_y_location)
        max_attempts = random.randint(min_max_attemps, max_max_attemps)

        location = (x, y)

        movement_importance = random.uniform(min_movement_importance, max_movement_importance)
        cost_importance = random.uniform(min_cost_importance, max_cost_importance)

        select_best = random.random() < select_best_probability

        wait_between_attempts = random.randint(min_wait_between_attempts, max_wait_between_attempts)
        waiting_list_wait_time = random.randint(min_waiting_list_wait_time, max_waiting_list_wait_time)

        client_agent.set('jid', client_jid)
        client_agent.set('general_manager_jid', general_manager_jid)
        client_agent.set('location', location)
        client_agent.set('movement_importance', movement_importance)
        client_agent.set('cost_importance', cost_importance)
        client_agent.set('max_distance', max_distance)
        client_agent.set('select_best', select_best)
        client_agent.set('max_attempts', max_attempts)
        client_agent.set('monthly_pass', monthly_pass_dict[client_jid])
        client_agent.set('wait_between_attempts', wait_between_attempts)
        client_agent.set('waiting_list_wait_time', waiting_list_wait_time)

        clients_agents.append(client_agent)

    for i, client_agent in enumerate(clients_agents):
        # if i != 0 and i % client_batch_size == 0:
        #     await asyncio.sleep(10)

        await client_agent.start()

    await spade.wait_until_finished(general_manager_agent)

    for park_manager in park_manager_agents:
        await park_manager.stop()

    for zone_manager in zone_manager_agents:
        await zone_manager.stop()

    for client_agent in clients_agents:
        await client_agent.stop()

if __name__ == "__main__":
    spade.run(main(sys.argv))
