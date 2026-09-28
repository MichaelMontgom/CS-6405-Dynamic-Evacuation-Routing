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

# add the max speeds for edges that are missing speeds
valdosta_graph = ox.add_edge_speeds(valdosta_graph)

# add the estimated travel times for edges - time is measured in seconds
valdosta_graph = ox.add_edge_travel_times(valdosta_graph)

for u, v, key, data in list(valdosta_graph.edges(keys=True, data=True))[:100]:
    data["vehicle_count"] = 0
    data["blocked"] = False

    print(f"{u} -> {v} [{key}]")
    print(data)
    print()

ox.io.save_graphml(
    valdosta_graph,
    filepath="valdosta_road_network.graphml",
)

print(f"Saved network to: valdosta_road_network.graphml")

# ox.plot.plot_graph(valdosta_graph, save=True, filepath="valdosta_road_network.graphml")

fig, ax = ox.plot.plot_graph(valdosta_graph, save=True, filepath="valdosta_road_network.png")
print(f"Saved network to: valdosta_road_network.png")
# Create Kennesaw Graph

kennesaw_graph = ox.graph.graph_from_place(
    "Kennesaw, Georgia, USA",
    network_type="drive",
    simplify=True
)

print("Network downloaded.")
print(f"Kennesaw Nodes: {kennesaw_graph.number_of_nodes():,}")
print(f"Kennesaw Edges: {kennesaw_graph.number_of_edges():,}")

# add the max speeds for edges that are missing speeds
kennesaw_graph = ox.add_edge_speeds(kennesaw_graph)

# add the estimated travel times for edges - time is measured in seconds
kennesaw_graph = ox.add_edge_travel_times(kennesaw_graph)

for u, v, key, data in list(kennesaw_graph.edges(keys=True, data=True))[:100]:
    data["vehicle_count"] = 0
    data["blocked"] = False

    print(f"{u} -> {v} [{key}]")
    print(data)
    print()

ox.io.save_graphml(
    kennesaw_graph,
    filepath="kennesaw_road_network.graphml",
)

print(f"Saved network to: kennesaw_road_network.graphml")

# ox.plot.plot_graph(kennesaw_graph)
fig2, ax2 = ox.plot.plot_graph(kennesaw_graph, save=True, filepath="kennesaw_road_network.png")
