from data.road_networks.road_networks import *
from simulation.locations import *
from simulation.visualization import *
from simulation.graphs import *
from simulation.routing import *
from simulation.traffic import *
from simulation.scenarios import *
from algorithms.baselines import *
import time




if __name__ == '__main__':

    SEED = 1

    base_graph = load_graph("data/road_networks/valdosta_road_network.graphml")
    base_graph = add_simulation_attributes(base_graph)

    sinks = pick_sinks(base_graph, 3, seed=SEED)
    print("sinks:", sinks)

    first_groups = generate_evacuation_groups(base_graph, 2000, sinks, seed=SEED)

    # close 10 roads sometime between 30 seconds and 2 minutes in (everyone leaves in the first 5)
    closures = generate_closures(base_graph, 10, (30, 120), seed=SEED, sinks=sinks, groups=first_groups)
    print("closures:", closures)

    algorithms = [StaticShortestPath(), PeriodicDijkstra(interval=300), LocalGreedyRerouting()]

    for algorithm in algorithms:
        # fresh copy of the map and fresh groups every run so nothing carries over
        graph = base_graph.copy()
        groups = generate_evacuation_groups(graph, 2000, sinks, seed=SEED)

        start = time.time()
        sim = TrafficSimulation(graph, groups, algorithm, max_ticks=5000, closures=closures)
        sim.run()

        rerouted = 0
        for g in sim.groups:
            if g.route_changes > 0:
                rerouted += 1

        print()
        print(algorithm.name, f"took {round(time.time() - start, 1)} seconds")
        print(sim.summary())
        print("groups that rerouted:", rerouted)

        # just show a couple of the groups that didn't make it
        not_out = []
        for g in sim.groups:
            if g.status != ARRIVED:
                not_out.append(g)

        for g in not_out[:10]:
            print(f"    Group {g.id}: {g.origin}->{g.destination} - Status: {g.status} - Route_changes: {g.route_changes} - Stuck at: {g.current_node}")

    # plot a few groups that had to reroute in the last run (local greedy)
    routes = []
    labels = []
    for g in sim.groups:
        if g.route_changes > 0:
            routes.append(g.route)
            labels.append(f"group {g.id}")

    plot_routes(graph, routes[:5], labels=labels[:5], title="valdosta - local greedy reroutes")



    #
    # sinks = [0, 24]   # top left and bottom right corners
    #
    # # these close at tick 8, after everybody has left
    # closures = [
    #     (8, 6, 11),
    #     (8, 12, 13),
    #     (8, 18, 19),
    #     (8, 1, 2),
    # ]
    #
    # # periodic interval is 20 here instead of 300 since everything on this little grid is done in like 100 ticks
    # algorithms = [StaticShortestPath(), PeriodicDijkstra(interval=20), LocalGreedyRerouting()]
    #
    # for algorithm in algorithms:
    #     graph = grid_graph(rows=5, cols=5, capacity=15, seed=0)
    #     groups = generate_evacuation_groups(graph, 40, sinks, seed=1)
    #
    #     sim = TrafficSimulation(graph, groups, algorithm, max_ticks=300, closures=closures)
    #     sim.run()
    #
    #     print()
    #     print(algorithm.name)
    #     print(sim.summary())
    #
    #     for g in sim.groups:
    #         if g.route_changes > 0 or g.status != ARRIVED:
    #             print(f"    Group {g.id}: {g.origin}->{g.destination} - Status: {g.status} - Route_changes: {g.route_changes} - Route: {g.route}")
    #
    # # plot the groups that rerouted in the last run (local greedy)
    # routes = []
    # labels = []
    # for g in sim.groups:
    #     if g.route_changes > 0:
    #         routes.append(g.route)
    #         labels.append(f"group {g.id}")
    #
    # plot_routes(graph, routes[:5], labels=labels[:5], title="local greedy reroutes")

    #
    # graph = grid_graph(rows=5, cols=5, capacity=15, seed=0)
    # sinks = [0, 24]   # top left and bottom right corners
    #
    # # one node at a time
    # for node in [4, 12, 20]:
    #     route = route_to_nearest_sink(graph, node, sinks)
    #     print(node, "-> sink", route[-1], "route:", route, "cost:", round(route_cost(graph, route), 2))
    #
    # # every node at once
    # tree = sink_tree(graph, sinks)
    # print("nodes that can reach a sink:", len(tree), "out of", graph.number_of_nodes())
    #
    # routes = []
    # labels = []
    # for node in [4, 12, 20]:
    #     routes.append(tree[node])
    #     labels.append(f"{node} to sink {tree[node][-1]}")
    #
    # plot_routes(graph, routes, labels=labels, title="routes to nearest sink")
    #
    # # close the first road on node 12's route and see where it goes now
    # u = tree[12][0]
    # v = tree[12][1]
    # graph.edges[u, v, 0]["blocked"] = True
    # graph.edges[v, u, 0]["blocked"] = True
    #
    # new_route = route_to_nearest_sink(graph, 12, sinks)
    # print()
    # print("closed", u, "<->", v)
    # print("12 new route:", new_route, "cost:", round(route_cost(graph, new_route), 2))
    #
    # # speed test on a bigger grid - one dijkstra per node vs one sink tree
    # big_graph = grid_graph(rows=30, cols=30, seed=0)
    # big_sinks = [0, 899]
    #
    # start = time.time()
    # for node in big_graph.nodes:
    #     route_to_nearest_sink(big_graph, node, big_sinks)
    # print()
    # print("one at a time:", round(time.time() - start, 3), "seconds")
    #
    # start = time.time()
    # big_tree = sink_tree(big_graph, big_sinks)
    # print("sink tree:", round(time.time() - start, 3), "seconds")



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

