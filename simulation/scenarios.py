import random
import networkx as nx
import pandas as pd

from simulation.traffic import Group, TrafficSimulation
from simulation.routing import route_cost, sink_tree


def generate_groups(graph, num_groups, seed, size_range=(1, 5), departure_window=10, origins=None, destinations=None):
    # same graph + same settings + same seed = same groups every time
    rng = random.Random(seed)

    # sort so the order doesn't depend on how the graph was built
    if origins is None:
        origins = sorted(graph.nodes)
    else:
        origins = sorted(origins)

    if destinations is None:
        destinations = sorted(graph.nodes)
    else:
        destinations = sorted(destinations)

    groups = []
    while len(groups) < num_groups:
        origin = rng.choice(origins)
        destination = rng.choice(destinations)

        if origin == destination:
            continue
        if not nx.has_path(graph, origin, destination):
            continue

        size = rng.randint(size_range[0], size_range[1])
        departure_tick = rng.randint(1, departure_window)

        groups.append(Group(len(groups), size, origin, destination, departure_tick))

    return groups


def pick_sinks(graph, num_sinks, seed):
    # random safe spots, but only from the biggest chunk of the map where every node can reach every other node
    # some road networks have little pieces cut off from the rest (valdosta has 32 of them)
    # and a sink stuck in one of those would be useless
    rng = random.Random(seed)

    biggest = max(nx.strongly_connected_components(graph), key=len)
    nodes = sorted(biggest)

    return sorted(rng.sample(nodes, num_sinks))


def generate_evacuation_groups(graph, num_groups, sinks, seed, size_range=(1, 5), departure_window=5):
    # groups start anywhere that can reach a sink and are happy getting to any of the sinks
    # same graph + same sinks + same seed = same groups every time
    rng = random.Random(seed)

    tree = sink_tree(graph, sinks)

    origins = []
    for node in sorted(tree):
        if node not in sinks:
            origins.append(node)

    groups = []
    for i in range(num_groups):
        origin = rng.choice(origins)
        size = rng.randint(size_range[0], size_range[1])
        departure_tick = rng.randint(1, departure_window)

        g = Group(i, size, origin, departure_tick=departure_tick, destinations=list(sinks))

        # best trip they could possibly have with empty roads, for working out delay later
        g.free_flow_time = route_cost(graph, tree[origin])

        groups.append(g)

    return groups


def generate_closures(graph, num_closures, tick_range, seed, sinks, groups=None, busiest=50):
    # picks some roads to close partway through the run
    # gives back a sorted list of (tick, u, v)
    # if groups are passed in, it picks from the busiest roads on everyone's starting routes
    # (on a real map a random road basically never hits anybody, and a road only one group
    # uses is usually already behind them by the time it closes)
    rng = random.Random(seed)

    if groups is None:
        roads_to_use = list(graph.edges())
    else:
        # the routes everyone would take at the start with empty roads
        tree = sink_tree(graph, sinks)
        roads_to_use = []
        for g in groups:
            route = tree[g.origin]
            for i in range(len(route) - 1):
                roads_to_use.append((route[i], route[i + 1]))

    # u -> v and v -> u are the same road, so store it as (smaller, bigger) to not count it twice
    # and count how many groups are planning to use each road
    candidates = {}
    for u, v in roads_to_use:
        if u in sinks or v in sinks:
            continue   # dont close roads right at a sink
        if u == v:
            continue
        # skip it if its already closed (every parallel road between u and v blocked)
        all_blocked = True
        for key in graph[u][v]:
            if graph[u][v][key].get("blocked", False) != True:
                all_blocked = False
        if all_blocked:
            continue

        road = (min(u, v), max(u, v))
        if road not in candidates:
            candidates[road] = 0
        candidates[road] += 1

    if groups is None:
        roads = sorted(candidates)
    else:
        # busiest roads first (ties go by road so its always the same order), then keep the top ones
        roads = sorted(candidates, key=lambda road: (-candidates[road], road))
        roads = sorted(roads[:busiest])

    num_closures = min(num_closures, len(roads))
    picked = rng.sample(roads, num_closures)

    closures = []
    for u, v in picked:
        tick = rng.randint(tick_range[0], tick_range[1])
        closures.append((tick, u, v))

    return sorted(closures)


def run_trials(graph_builder, routers, seeds, num_groups, max_ticks=1000, **group_kwargs):
    # runs every router on every seed and puts the summaries in a dataframe
    # graph_builder is a function that makes a new graph so every run starts clean
    rows = []

    for seed in seeds:
        for router_name in routers:
            router = routers[router_name]

            graph = graph_builder()
            groups = generate_groups(graph, num_groups, seed, **group_kwargs)

            sim = TrafficSimulation(graph, groups, router, max_ticks=max_ticks)
            sim.run()

            row = sim.summary()
            row["seed"] = seed
            row["router"] = router_name
            rows.append(row)

    df = pd.DataFrame(rows)

    # put seed and router first
    columns = ["seed", "router"]
    for c in df.columns:
        if c not in columns:
            columns.append(c)

    return df[columns]
