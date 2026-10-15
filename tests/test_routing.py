import networkx as nx
import pytest

from simulation.graphs import add_road, grid_graph, line_graph, two_route_graph
from simulation.routing import best_edge_key, bpr_travel_time, congestion_weight, dijkstra_route, route_cost


def brute_force_shortest_cost(graph, origin, destination):
    # try every path and keep the cheapest one
    best = None
    for path in nx.all_simple_paths(graph, origin, destination):
        cost = route_cost(graph, path)
        if best is None or cost < best:
            best = cost
    return best


def test_line_graph_route():
    graph = line_graph(num_nodes=4)
    assert dijkstra_route(graph, 0, 3) == [0, 1, 2, 3]


def test_picks_fast_route():
    graph = two_route_graph(fast_time=5, slow_time=8)
    route = dijkstra_route(graph, 0, 3)
    assert route == [0, 1, 3]
    assert route_cost(graph, route) == 10


def test_avoids_blocked_road():
    graph = two_route_graph()
    graph.edges[0, 1, 0]["blocked"] = True
    assert dijkstra_route(graph, 0, 3) == [0, 2, 3]


def test_no_route_when_all_blocked():
    graph = two_route_graph()
    graph.edges[0, 1, 0]["blocked"] = True
    graph.edges[0, 2, 0]["blocked"] = True
    assert dijkstra_route(graph, 0, 3) is None


def test_parallel_roads_use_fastest_open_one():
    graph = nx.MultiDiGraph()
    add_road(graph, 0, 1, travel_time=10, capacity=20, two_way=False)
    add_road(graph, 0, 1, travel_time=4, capacity=20, two_way=False)
    assert best_edge_key(graph, 0, 1) == 1

    # block the fast one, should use the slow one now
    graph.edges[0, 1, 1]["blocked"] = True
    assert best_edge_key(graph, 0, 1) == 0
    assert route_cost(graph, [0, 1]) == 10


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_dijkstra_matches_brute_force_on_grid(seed):
    graph = grid_graph(rows=3, cols=3, seed=seed)

    for origin in graph.nodes:
        for destination in graph.nodes:
            if origin == destination:
                continue
            route = dijkstra_route(graph, origin, destination)
            expected = brute_force_shortest_cost(graph, origin, destination)
            assert route_cost(graph, route) == pytest.approx(expected)


def test_bpr_travel_time():
    assert bpr_travel_time(10, 0, 20) == 10
    assert bpr_travel_time(10, 20, 20) == pytest.approx(11.5)


def test_congestion_weight_moves_route_off_busy_road():
    graph = two_route_graph(fast_time=5, slow_time=5.2)

    vehicles_on = {}
    for edge in graph.edges(keys=True):
        vehicles_on[edge] = 0

    assert dijkstra_route(graph, 0, 3, weight=congestion_weight(vehicles_on)) == [0, 1, 3]

    # put a bunch of cars on the fast road
    vehicles_on[(0, 1, 0)] = 9
    assert dijkstra_route(graph, 0, 3, weight=congestion_weight(vehicles_on)) == [0, 2, 3]
