import osmnx as ox
import networkx as nx


def download_graph(location: str):
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


def save_graph(graph: nx.Graph, filepath: str):
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
        print(e)




