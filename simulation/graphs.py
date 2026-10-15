import random
import networkx as nx


def add_road(graph, u, v, travel_time, capacity, two_way=True):
    # osmnx needs a length on every road to plot, so just use the travel time for it
    graph.add_edge(u, v, travel_time=travel_time, length=travel_time, capacity=capacity, blocked=False)

    if two_way:
        graph.add_edge(v, u, travel_time=travel_time, length=travel_time, capacity=capacity, blocked=False)


def line_graph(num_nodes=4, travel_time=5, capacity=20):
    # 0 - 1 - 2 - 3 ...
    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "epsg:4326"  # osmnx needs this to plot

    for i in range(num_nodes):
        graph.add_node(i, x=i, y=0)

    for i in range(num_nodes - 1):
        add_road(graph, i, i + 1, travel_time, capacity)

    return graph


def two_route_graph(fast_time=5, fast_capacity=10, slow_time=8, slow_capacity=40):
    # 0 to 3 has a fast skinny route through 1 and a slow wide route through 2
    #
    #       1
    #     /   \
    #   0       3
    #     \   /
    #       2
    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "epsg:4326"

    graph.add_node(0, x=0, y=0)
    graph.add_node(1, x=1, y=1)
    graph.add_node(2, x=1, y=-1)
    graph.add_node(3, x=2, y=0)

    add_road(graph, 0, 1, fast_time, fast_capacity)
    add_road(graph, 1, 3, fast_time, fast_capacity)
    add_road(graph, 0, 2, slow_time, slow_capacity)
    add_road(graph, 2, 3, slow_time, slow_capacity)

    return graph


def grid_graph(rows=5, cols=5, travel_time=10, capacity=20, seed=None, time_jitter=0.5):
    # node number = row * cols + col
    # if there's a seed, every road gets a random travel time between
    # travel_time * (1 - jitter) and travel_time * (1 + jitter)
    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "epsg:4326"

    rng = None
    if seed is not None:
        rng = random.Random(seed)

    for row in range(rows):
        for col in range(cols):
            graph.add_node(row * cols + col, x=col, y=-row)

    for row in range(rows):
        for col in range(cols):
            node = row * cols + col

            # connect to the node on the right and the node below
            neighbors = []
            if col + 1 < cols:
                neighbors.append(node + 1)
            if row + 1 < rows:
                neighbors.append(node + cols)

            for neighbor in neighbors:
                time = travel_time
                if rng is not None:
                    time = round(travel_time * rng.uniform(1 - time_jitter, 1 + time_jitter), 2)

                add_road(graph, node, neighbor, time, capacity)

    return graph
