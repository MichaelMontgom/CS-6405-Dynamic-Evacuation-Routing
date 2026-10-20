from data.road_networks.road_networks import *
from simulation.locations import *
from simulation.visualization import *
from simulation.graphs import *
from simulation.routing import *
from simulation.traffic import *
from simulation.scenarios import *




if __name__ == '__main__':



    closures = [
        (3,10,5),
        (3,6,11),
    ]

    for name, closure_list in [("no closures", []), ("with closures", closures)]:
        graph = grid_graph(rows=5, cols=5, capacity=15, seed=0)
        groups = generate_groups(graph, num_groups=10, seed=1, departure_window=5)

        # max_ticks lower so stuck groups dont make it run to 1000
        sim = TrafficSimulation(graph, groups, static_dijkstra_router, max_ticks=300, closures=closure_list)
        sim.run()

        print()
        print(name)
        print(sim.summary())

        for g in sim.groups:
            print(g.id, g.origin, "->", g.destination, g.status, "travel time:", g.travel_time, "waited:", g.wait_ticks,
                  "reroutes:", g.route_changes)

    routes = []
    labels = []
    for g in sim.groups:
        if g.status != ARRIVED:
            routes.append(g.route)
            labels.append(f"group {g.id} stuck at {g.current_node}")

    if len(routes) > 0:
        plot_routes(graph, routes, labels=labels, title="stuck groups")
    else:
        print("nobody got stuck")



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

