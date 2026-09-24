import osmnx as ox
from pathlib import Path


# Create Valdosta Graph

valdosta_graph = ox.graph.graph_from_place(
    "Valdosta, Georgia, USA",
    network_type="drive",
    simplify=True
)

print("Network downloaded.")
print(f"Valdosta Nodes: {valdosta_graph.number_of_nodes():,}")
print(f"Valdosta Edges: {valdosta_graph.number_of_edges():,}")

ox.io.save_graphml(
    valdosta_graph,
    filepath="valdosta_road_network.graphml",
)

print(f"Saved network to: valdosta_road_network.graphml")

ox.plot.plot_graph(valdosta_graph)

# Create Kennesaw Graph

kennesaw_graph = ox.graph.graph_from_place(
    "Kennesaw, Georgia, USA",
    network_type="drive",
    simplify=True
)

print("Network downloaded.")
print(f"Kennesaw Nodes: {kennesaw_graph.number_of_nodes():,}")
print(f"Kennesaw Edges: {kennesaw_graph.number_of_edges():,}")

ox.io.save_graphml(
    kennesaw_graph,
    filepath="kennesaw_road_network.graphml",
)

print(f"Saved network to: kennesaw_road_network.graphml")

ox.plot.plot_graph(kennesaw_graph)