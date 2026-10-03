from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
from matplotlib.axes import Axes
from matplotlib.figure import Figure

ROUTE_COLORS = ["red", "dodgerblue", "limegreen", "orange", "magenta", "yellow", "cyan"]


def plot_base_graph(graph: nx.MultiDiGraph) -> tuple[Figure, Axes]:
    return ox.plot.plot_graph(
        graph,
        node_size=0,
        edge_color="#999999",
        edge_linewidth=0.5,
        bgcolor="white",
        show=False,
        close=False,
    )


def plot_origin_destination(
    graph: nx.MultiDiGraph,
    ax: Axes,
    origin_node: int,
    destination_node: int,
    label: bool = True,
):
    origin = graph.nodes[origin_node]
    destination = graph.nodes[destination_node]

    ax.scatter(origin["x"], origin["y"], c="green", s=80, zorder=5, edgecolors="black",
               label="Origin" if label else None)
    ax.scatter(destination["x"], destination["y"], c="black", s=80, zorder=5, marker="X",
               label="Destination" if label else None)


def plot_route(
    graph: nx.MultiDiGraph,
    route: list[int],
    color: str = "red",
    title: str | None = None,
    filepath: str | Path | None = None,
    show: bool = True,
) -> tuple[Figure, Axes]:
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
    ax.legend(loc="upper right")

    return finish_figure(fig, ax, title, filepath, show)


def plot_routes(
    graph: nx.MultiDiGraph,
    routes: list[list[int]],
    labels: list[str] | None = None,
    colors: list[str] | None = None,
    title: str | None = None,
    filepath: str | Path | None = None,
    show: bool = True,
) -> tuple[Figure, Axes]:
    fig, ax = plot_base_graph(graph)
    colors = colors or ROUTE_COLORS

    for i, route in enumerate(routes):
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

        if labels:
            ax.plot([], [], color=color, linewidth=3, label=labels[i])

    if labels:
        ax.legend(loc="upper right")

    return finish_figure(fig, ax, title, filepath, show)


def finish_figure(
    fig: Figure,
    ax: Axes,
    title: str | None,
    filepath: str | Path | None,
    show: bool,
) -> tuple[Figure, Axes]:
    if title:
        ax.set_title(title)

    if filepath:
        save_figure(fig, filepath)

    if show:
        plt.show()

    return fig, ax


def save_figure(fig: Figure, filepath: str | Path):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.savefig(filepath, dpi=300, bbox_inches="tight")
        print(f"Figure saved: {filepath}")
    except Exception as e:
        print(f"Error saving figure: {filepath}")
        print(e)
