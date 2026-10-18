from pathlib import Path
import matplotlib.pyplot as plt
import osmnx as ox

ROUTE_COLORS = ["red", "dodgerblue", "limegreen", "orange", "magenta", "yellow", "cyan"]


def plot_base_graph(graph):
    # small test graphs are hard to see with the road network settings,
    # so draw them bigger and put the node numbers on them
    small_graph = graph.number_of_nodes() < 100

    if small_graph:
        node_size = 40
        edge_width = 1.5
    else:
        node_size = 0
        edge_width = 0.5

    fig, ax = ox.plot.plot_graph(
        graph,
        node_size=node_size,
        node_color="#555555",
        edge_color="#999999",
        edge_linewidth=edge_width,
        bgcolor="white",
        show=False,
        close=False,
    )

    if small_graph:
        for node, data in graph.nodes(data=True):
            ax.annotate(str(node), (data["x"], data["y"]), xytext=(6, 6), textcoords="offset points")

    return fig, ax


def plot_origin_destination(graph, ax, origin_node, destination_node, label=True):
    origin = graph.nodes[origin_node]
    destination = graph.nodes[destination_node]

    # only label the first one so the legend doesnt repeat
    origin_label = None
    destination_label = None
    if label:
        origin_label = "Origin"
        destination_label = "Destination"

    ax.scatter(origin["x"], origin["y"], c="green", s=80, zorder=5, edgecolors="black", label=origin_label)
    ax.scatter(destination["x"], destination["y"], c="black", s=80, zorder=5, marker="X", label=destination_label)


def plot_route(graph, route, color="red", title=None, filepath=None, show=True):
    fig, ax = plot_base_graph(graph)

    ox.plot.plot_graph_route(
        graph,
        route,
        ax=ax,
        route_color=color,
        route_linewidth=3,
        orig_dest_size=0,
        show=False,
        close=False,
    )
    plot_origin_destination(graph, ax, route[0], route[-1])
    ax.legend(loc="upper left", bbox_to_anchor=(1, 1))

    return finish_figure(fig, ax, title, filepath, show)


def plot_routes(graph, routes, labels=None, colors=None, title=None, filepath=None, show=True):
    fig, ax = plot_base_graph(graph)

    if colors is None:
        colors = ROUTE_COLORS

    for i in range(len(routes)):
        route = routes[i]
        color = colors[i % len(colors)]

        ox.plot.plot_graph_route(
            graph,
            route,
            ax=ax,
            route_color=color,
            route_linewidth=3,
            route_alpha=0.7,
            orig_dest_size=0,
            show=False,
            close=False,
        )
        plot_origin_destination(graph, ax, route[0], route[-1], label=(i == 0))

        # empty line just so the route shows up in the legend
        if labels:
            ax.plot([], [], color=color, linewidth=3, label=labels[i])

    if labels:
        ax.legend(loc="upper left", bbox_to_anchor=(1, 1))

    return finish_figure(fig, ax, title, filepath, show)


def finish_figure(fig, ax, title, filepath, show):
    if title:
        ax.set_title(title)

    if filepath:
        save_figure(fig, filepath)

    if show:
        plt.show()

    return fig, ax


def save_figure(fig, filepath):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    try:
        fig.savefig(filepath, dpi=300, bbox_inches="tight")
        print(f"Figure saved: {filepath}")
    except Exception as e:
        print(f"Error saving figure: {filepath}")
        print(e)
