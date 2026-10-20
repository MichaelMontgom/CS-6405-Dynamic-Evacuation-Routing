from data.road_networks.road_networks import *
from simulation.locations import *
from simulation.visualization import *
from simulation.graphs import *
from simulation.routing import *
from simulation.traffic import *
from simulation.scenarios import *
import time




if __name__ == '__main__':

    # step 2 test - routing to the nearest sink

    graph = grid_graph(rows=5, cols=5, capacity=15, seed=0)
    sinks = [0, 24]   # top left and bottom right corners

    # one node at a time
    for node in [4, 12, 20]:
        route = route_to_nearest_sink(graph, node, sinks)
        print(node, "-> sink", route[-1], "route:", route, "cost:", round(route_cost(graph, route), 2))

    # every node at once
    tree = sink_tree(graph, sinks)
    print("nodes that can reach a sink:", len(tree), "out of", graph.number_of_nodes())

    routes = []
    labels = []
    for node in [4, 12, 20]:
        routes.append(tree[node])
        labels.append(f"{node} to sink {tree[node][-1]}")

    plot_routes(graph, routes, labels=labels, title="routes to nearest sink")

    # close the first road on node 12's route and see where it goes now
    u = tree[12][0]
    v = tree[12][1]
    graph.edges[u, v, 0]["blocked"] = True
    graph.edges[v, u, 0]["blocked"] = True

    new_route = route_to_nearest_sink(graph, 12, sinks)
    print()
    print("closed", u, "<->", v)
    print("12 new route:", new_route, "cost:", round(route_cost(graph, new_route), 2))

    # speed test on a bigger grid - one dijkstra per node vs one sink tree
    big_graph = grid_graph(rows=30, cols=30, seed=0)
    big_sinks = [0, 899]

    start = time.time()
    for node in big_graph.nodes:
        route_to_nearest_sink(big_graph, node, big_sinks)
    print()
    print("one at a time:", round(time.time() - start, 3), "seconds")

    start = time.time()
    big_tree = sink_tree(big_graph, big_sinks)
    print("sink tree:", round(time.time() - start, 3), "seconds")



    # closures test from step 1
    # closures = [
    #     (3,10,5),
    #     (3,6,11),
    # ]
    #
    # for name, closure_list in [("no closures", []), ("with closures", closures)]:
    #     graph = grid_graph(rows=5, cols=5, capacity=15, seed=0)
    #     groups = generate_groups(graph, num_groups=10, seed=1, departure_window=5)
    #
    #     # max_ticks lower so stuck groups dont make it run to 1000
    #     sim = TrafficSimulation(graph, groups, static_dijkstra_router, max_ticks=300, closures=closure_list)
    #     sim.run()
    #
    #     print()
    #     print(name)
    #     print(sim.summary())
    #
    #     for g in sim.groups:
    #         print(g.id, g.origin, "->", g.destination, g.status, "travel time:", g.travel_time, "waited:", g.wait_ticks,
    #               "reroutes:", g.route_changes)
    #
    # routes = []
    # labels = []
    # for g in sim.groups:
    #     if g.status != ARRIVED:
    #         routes.append(g.route)
    #         labels.append(f"group {g.id} stuck at {g.current_node}")
    #
    # if len(routes) > 0:
    #     plot_routes(graph, routes, labels=labels, title="stuck groups")
    # else:
    #     print("nobody got stuck")



    # small test on a grid
    # graph = grid_graph(rows=5, cols=5, capacity=15, seed=0)
    #
    # groups = generate_groups(graph, num_groups=10, seed=1, departure_window=5)
    #
    # sim = TrafficSimulation(graph, groups, static_dijkstra_router)
    # sim.run()
    #
    # print(sim.summary())
    #
    # for g in sim.groups:
    #     print(g.id, g.origin, "->", g.destination, g.status, "travel time:", g.travel_time, "waited:", g.wait_ticks)
    #
    # routes = []
    # labels = []
    # for g in sim.groups[:4]:
    #     routes.append(g.route)
    #     labels.append(f"group {g.id}")
    #
    # plot_routes(graph, routes, labels=labels, title="test grid routes")


    # graph = load_graph("data/road_networks/valdosta_road_network.graphml")
    #
    # origin_node = get_nearest_node(graph, lat=30.82, lon=-83.30)
    # destination_node = get_nearest_node(graph, lat=30.87, lon=-83.29)
    #
    # route = get_shortest_route(graph, origin_node, destination_node)
    #
    # print(f"Origin: {origin_node} {get_node_coordinates(graph, origin_node)}")
    # print(f"Destination: {destination_node} {get_node_coordinates(graph, destination_node)}")
    # print(f"Route nodes: {len(route)}")
    # print(f"Route length: {get_route_length(graph, route):,.0f} m")
    # print(f"Route travel time: {get_route_travel_time(graph, route):,.0f} s")
    #
    # plot_route(graph, route)
    #
    # rng = random.Random(42)
    # print(f"Random origin/destination: {get_random_origin_destination(graph, rng)}")

