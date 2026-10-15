import random
import networkx as nx
import pandas as pd

from simulation.traffic import Group, TrafficSimulation


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
