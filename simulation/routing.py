import networkx as nx

# BPR constants from the DCAS doc
BPR_ALPHA = 0.15
BPR_BETA = 4


def bpr_travel_time(free_flow_time, vehicles, capacity):
    return free_flow_time * (1 + BPR_ALPHA * (vehicles / capacity) ** BPR_BETA)


def best_edge_key(graph, u, v):
    # there can be more than one road between u and v, pick the fastest one that isnt blocked
    best_key = None
    best_time = None

    for key, data in graph[u][v].items():
        if data.get("blocked", False):
            continue
        if best_time is None or data["travel_time"] < best_time:
            best_key = key
            best_time = data["travel_time"]

    return best_key


def free_flow_weight(u, v, edges):
    # networkx gives us all the roads between u and v
    # returning None tells networkx the road doesnt exist (thats how blocked roads get skipped)
    best_time = None

    for key, data in edges.items():
        if data.get("blocked", False):
            continue
        if best_time is None or data["travel_time"] < best_time:
            best_time = data["travel_time"]

    return best_time


def congestion_weight(vehicles_on):
    # same as free_flow_weight but uses BPR with how many cars are on the road right now
    def weight(u, v, edges):
        best_time = None

        for key, data in edges.items():
            if data.get("blocked", False):
                continue

            vehicles = vehicles_on.get((u, v, key), 0)
            time = bpr_travel_time(data["travel_time"], vehicles, data["capacity"])

            if best_time is None or time < best_time:
                best_time = time

        return best_time

    return weight


def dijkstra_route(graph, origin, destination, weight=free_flow_weight):
    try:
        return nx.dijkstra_path(graph, origin, destination, weight=weight)
    except nx.NetworkXNoPath:
        return None


def route_cost(graph, route, weight=free_flow_weight):
    total = 0
    for i in range(len(route) - 1):
        u = route[i]
        v = route[i + 1]
        total += weight(u, v, graph[u][v])
    return total


def route_to_nearest_sink(graph, start, sinks, weight=free_flow_weight):
    # cheapest route from start to whichever sink is closest
    # a sink is a specific node or vertex in a directed graph that acts as the ultimate destination for data or traffic
    # one dijkstra from start gives the distance to every node, then just pick the best sink
    distances, paths = nx.single_source_dijkstra(graph, start, weight=weight)

    best_sink = None
    for sink in sorted(sinks):  # sorted so ties always pick the same sink
        if sink not in distances:
            continue
        if best_sink is None or distances[sink] < distances[best_sink]:
            best_sink = sink

    if best_sink is None:
        return None  # cant reach any sink
    return paths[best_sink]


def reverse_weight(weight):
    def flipped(u, v, edges):
        return weight(v, u, edges)

    return flipped


def sink_tree(graph, sinks, weight=free_flow_weight):
    # route from every node to its nearest sink, with only one dijkstra
    reversed_graph = graph.reverse(copy=False)
    distances, paths = nx.multi_source_dijkstra(reversed_graph, sorted(sinks), weight=reverse_weight(weight))

    tree = {}
    for node in paths:
        # paths come out as sink -> ... -> node, so flip them to node -> ... -> sink
        tree[node] = list(reversed(paths[node]))

    return tree


# routers - the simulation calls these as router(sim, group)
# they return a list of nodes, or None if theres no route

def static_dijkstra_router(sim, group):
    return dijkstra_route(sim.graph, group.current_node, group.destination)


def congestion_dijkstra_router(sim, group):
    weight = congestion_weight(sim.vehicles_on)
    return dijkstra_route(sim.graph, group.current_node, group.destination, weight=weight)
