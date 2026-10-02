import random
from pathlib import Path

import geopandas as gpd
import networkx as nx
import osmnx as ox

from data.road_networks.road_networks import load_graph

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def geocode_location(query: str) -> tuple[float, float]:
    return ox.geocoder.geocode(query)


def get_nearest_node(graph: nx.MultiDiGraph, lat: float, lon: float) -> int:
    return ox.distance.nearest_nodes(graph, X=lon, Y=lat)


def get_node_coordinates(graph: nx.MultiDiGraph, node: int) -> tuple[float, float]:
    data = graph.nodes[node]
    return data["y"], data["x"]


def get_random_node(graph: nx.MultiDiGraph, rng: random.Random | None = None) -> int:
    rng = rng or random
    return rng.choice(list(graph.nodes))


def get_random_origin_destination(
    graph: nx.MultiDiGraph,
    rng: random.Random | None = None,
    max_attempts: int = 100,
) -> tuple[int, int]:
    # drive networks are directed, so not every pair of nodes is reachable
    rng = rng or random
    nodes = list(graph.nodes)

    for _ in range(max_attempts):
        origin, destination = rng.sample(nodes, 2)
        if nx.has_path(graph, origin, destination):
            return origin, destination

    raise RuntimeError(f"No reachable origin/destination pair found in {max_attempts} attempts")


def get_shortest_route(
    graph: nx.MultiDiGraph,
    origin_node: int,
    destination_node: int,
    weight: str = "travel_time",
) -> list[int] | None:
    return ox.routing.shortest_path(graph, origin_node, destination_node, weight=weight)


def get_route_edges(graph: nx.MultiDiGraph, route: list[int], weight: str = "travel_time") -> gpd.GeoDataFrame:
    return ox.routing.route_to_gdf(graph, route, weight=weight)


def get_route_length(graph: nx.MultiDiGraph, route: list[int]) -> float:
    return get_route_edges(graph, route, weight="length")["length"].sum()


def get_route_travel_time(graph: nx.MultiDiGraph, route: list[int]) -> float:
    return get_route_edges(graph, route, weight="travel_time")["travel_time"].sum()



