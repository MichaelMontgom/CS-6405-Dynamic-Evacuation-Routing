from data.road_networks.road_networks import *


if __name__ == '__main__':

    graph = load_graph(filepath="data/road_networks/kennesaw_road_network.graphml")

    print(graph)


