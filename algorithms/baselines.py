from simulation.routing import best_edge_key, congestion_weight, route_to_nearest_sink, sink_tree
from simulation.traffic import WAITING, TRAVELING, TRAPPED

class StaticShortestPath:
    # baseline 1 - dijkstra once at the start with empty road times, never changes its mind
    # if a road on the route closes the group just sits there

    def __init__(self):
        self.name = "static"

    def plan_route(self, sim, group):
        return route_to_nearest_sink(sim.graph, group.current_node, group.destinations)

    def update(self, sim):
        pass


class PeriodicDijkstra:
    # baseline 2 - every interval ticks, reroute everybody whos still driving
    # uses current traffic (BPR) for road costs so it reacts to congestion and closures
    # 300 ticks = 5 min since 1 tick = 1 second

    def __init__(self, interval=300):
        self.name = "periodic_dijkstra"
        self.interval = interval

    def plan_route(self, sim, group):
        return route_to_nearest_sink(sim.graph, group.current_node, group.destinations)

    def update(self, sim):
        if sim.tick % self.interval != 0:
            return

        weight = congestion_weight(sim.vehicles_on)

        # one sink tree per set of sinks, usually theres only one set so its just one dijkstra
        trees = {}

        for g in sim.groups:
            if g.status != WAITING and g.status != TRAVELING:
                continue

            sinks = tuple(sorted(g.destinations))
            if sinks not in trees:
                trees[sinks] = sink_tree(sim.graph, sinks, weight=weight)
            tree = trees[sinks]

            start = sim.planning_node(g)
            if start in tree:
                sim.reroute(g, tree[start])
            elif g.status == WAITING:
                g.status = TRAPPED   # no way out from here
            # if its traveling just let it finish the road and try again next time


class LocalGreedyRerouting:
    # baseline 3 - only reroutes when the next road is closed right in front of it
    # only knows about closures, doesn't look at traffic or capacity at all

    def __init__(self):
        self.name = "local_greedy"

    def plan_route(self, sim, group):
        return route_to_nearest_sink(sim.graph, group.current_node, group.destinations)

    def update(self, sim):
        for g in sim.groups:
            if g.status != WAITING:
                continue

            # best_edge_key gives None when every road from here to the next node is blocked
            if best_edge_key(sim.graph, g.current_node, g.next_node) is not None:
                continue

            new_route = route_to_nearest_sink(sim.graph, g.current_node, g.destinations)
            if new_route is None:
                g.status = TRAPPED
            else:
                sim.reroute(g, new_route)
