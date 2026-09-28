import osmnx as ox
import networkx as nx

valdosta = ox.load_graphml("valdosta_road_network.graphml")

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
