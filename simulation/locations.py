import random
from pathlib import Path
import networkx as nx
import osmnx as ox

from data.road_networks.road_networks import load_graph

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def geocode_location(query):
    # gives back (lat, lon)
    return ox.geocoder.geocode(query)


def get_nearest_node(graph, lat, lon):
    # osmnx wants X = lon and Y = lat
    return ox.distance.nearest_nodes(graph, X=lon, Y=lat)


def get_node_coordinates(graph, node):
    data = graph.nodes[node]
    return data["y"], data["x"]


def get_random_node(graph, rng=None):
    if rng is None:
        rng = random
    return rng.choice(list(graph.nodes))


def get_random_origin_destination(graph, rng=None, max_attempts=100):
    # roads are one way sometimes so not every pair of nodes can reach each other
    if rng is None:
        rng = random

    nodes = list(graph.nodes)

    for i in range(max_attempts):
        origin, destination = rng.sample(nodes, 2)
        if nx.has_path(graph, origin, destination):
            return origin, destination

    raise RuntimeError(f"couldnt find a reachable origin/destination in {max_attempts} tries")


def get_shortest_route(graph, origin_node, destination_node, weight="travel_time"):
    # weight is "travel_time" (seconds) or "length" (meters)
    return ox.routing.shortest_path(graph, origin_node, destination_node, weight=weight)


def get_route_edges(graph, route, weight="travel_time"):
    return ox.routing.route_to_gdf(graph, route, weight=weight)


def get_route_length(graph, route):
    edges = get_route_edges(graph, route, weight="length")
    return edges["length"].sum()


def get_route_travel_time(graph, route):
    edges = get_route_edges(graph, route, weight="travel_time")
    return edges["travel_time"].sum()
