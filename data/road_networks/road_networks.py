import osmnx as ox
import networkx as nx

valdosta = ox.load_graphml("valdosta_road_network.graphml")

# add the max speeds for edges that are missing speeds
valdosta = ox.add_edge_speeds(valdosta)

# add the estimated travel times for edges - time is measured in seconds
valdosta = ox.add_edge_travel_times(valdosta)

# for node_id, data in list(valdosta.nodes(data=True))[:5]:
#     print(node_id, data)
#
for u, v, key, data in list(valdosta.edges(keys=True, data=True))[:100]:
    print(f"{u} -> {v} [{key}]")
    print(data)
    print()

print(f"Directed: {valdosta.is_directed()}")
print(f"Multigraph: {valdosta.is_multigraph()}")

print(
    "Weakly connected components:",
    nx.number_weakly_connected_components(valdosta),
)