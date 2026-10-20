import osmnx as ox

def download_graph(location: str) -> ox.Graph:
    graph = ox.graph.graph_from_place(
        location,
        network_type="drive",
        simplify=True
    )

    print("Network downloaded.")
    print(f"{location} Nodes: {graph.number_of_nodes():,}")
    print(f"{location} Edges: {graph.number_of_edges():,}")

    # add the max speeds for edges that are missing speeds
    graph = ox.add_edge_speeds(graph)

    # add the estimated travel times for edges - time is measured in seconds
    graph = ox.add_edge_travel_times(graph)

    return graph


def plot_graph(graph):
    fig2, ax2 = ox.plot.plot_graph(graph)


def save_graph(graph: ox.Graph, filepath: str):
    try:
        ox.io.save_graphml(
            graph,
            filepath=filepath,
        )
    except Exception as e:
        print(f"Error saving graph: {filepath}")
        print(e)

def load_graph(filepath: str):
    print("Loading graph...")
    print(f"{filepath}")
    try:
        return ox.load_graphml(filepath=filepath)
    except Exception as e:
        print(f"Error loading graph: {filepath}")
        raise


def get_lanes(data):
    # lanes can be missing, a string like "2", or a list like ['2', '3']
    lanes = data.get("lanes")

    if lanes is None:
        return 1

    if isinstance(lanes, list):
        lanes = lanes[0]

    try:
        return max(1, int(lanes))
    except ValueError:
        return 1   # sometimes its junk like "2;3", just call it 1


def add_simulation_attributes(graph, car_length=7.5, min_capacity=10):
    # the saved graphml files need some fixing before we can run the sim on them
    # blocked got saved as the string "False" which python counts as True, so turn it back into a real bool
    # capacity = how many cars fit on the road = lanes * length / how much road one car takes up
    # really short roads get bumped up to min_capacity so groups can still fit on them
    for u, v, key, data in graph.edges(keys=True, data=True):
        data["blocked"] = data.get("blocked") == True or data.get("blocked") == "True"

        capacity = get_lanes(data) * data["length"] / car_length
        data["capacity"] = max(min_capacity, round(capacity))

    return graph




