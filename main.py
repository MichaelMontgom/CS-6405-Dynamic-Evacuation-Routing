from data.road_networks.road_networks import *
from simulation.locations import *





if __name__ == '__main__':

    graph = load_graph("data/road_networks/valdosta_road_network.graphml")

    origin_node = get_nearest_node(graph, lat=30.82, lon=-83.30)
    destination_node = get_nearest_node(graph, lat=30.87, lon=-83.29)

    route = get_shortest_route(graph, origin_node, destination_node)

    print(f"Origin: {origin_node} {get_node_coordinates(graph, origin_node)}")
    print(f"Destination: {destination_node} {get_node_coordinates(graph, destination_node)}")
    print(f"Route nodes: {len(route)}")
    print(f"Route length: {get_route_length(graph, route):,.0f} m")
    print(f"Route travel time: {get_route_travel_time(graph, route):,.0f} s")

    rng = random.Random(42)
    print(f"Random origin/destination: {get_random_origin_destination(graph, rng)}")

