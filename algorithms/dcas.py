from heapq import heappush, heappop
from itertools import count, islice
import networkx as nx

from simulation.routing import bpr_travel_time
from simulation.traffic import CAPACITY_THRESHOLD, WAITING, TRAVELING, ARRIVED, TRAPPED


class DCAS:
    # physical space only gets held for entry this tick
    # downstream plans are a soft forecast, so cars can share a road at different times

    def __init__(self, k=3, cooldown=3, cost_threshold=1.30, improvement_threshold=0.80,
                 event_driven=True, forecast_weight=0.25):
        if not isinstance(k, int) or k < 1:
            raise ValueError("k has to be a positive integer")
        if cooldown < 0 or cost_threshold < 1 or not 0 < improvement_threshold < 1:
            raise ValueError("invalid cooldown or rerouting thresholds")
        if not 0 <= forecast_weight <= 1:
            raise ValueError("forecast_weight has to be between 0 and 1")
        self.name = "dcas"
        self.k = k
        self.cooldown = cooldown
        self.cost_threshold = cost_threshold
        self.improvement_threshold = improvement_threshold
        self.event_driven = event_driven
        self.forecast_weight = forecast_weight

    def initialize(self, sim):
        # includes cars already on a road and groups planning to use it later
        self.planned_on = {}
        for edge in sim.graph.edges(keys=True):
            self.planned_on[edge] = 0
        self.route_edges = {}
        self.assigned_costs = {}
        self.assigned_groups = set()
        self.last_reroute_tick = {}
        self.last_failed_version = {}
        self.needs_route = set()
        self.entry_claims = {}
        self.group_claims = {}
        self.state_version = 0
        self.last_prepared_tick = None
        self.road_data = {}
        for u, v, key, data in sim.graph.edges(keys=True, data=True):
            self.road_data[(u, v, key)] = data
        self.road_state = {}
        self.lower_bounds = {}
        self.price_bounds = {}
        self.open_reachable = {}

        # keep parallel roads separate when searching a simple graph
        self.search_graph = nx.DiGraph()
        self.search_graph.add_nodes_from(sim.graph.nodes)
        self.middle_ends = {}
        for u in sim.graph:
            for v, roads in sim.graph[u].items():
                if u == v:
                    continue
                for key in roads:
                    edge = (u, v, key)
                    if len(roads) == 1:
                        self.search_graph.add_edge(u, v, road=edge)
                    else:
                        middle = object()
                        self.middle_ends[middle] = v
                        self.search_graph.add_edge(u, middle, road=edge)
                        self.search_graph.add_edge(middle, v)
        self.target = object()
        self.search_graph.add_node(self.target)
        self.sinks = set()

    def prepare_tick(self, sim):
        if self.last_prepared_tick == sim.tick:
            return
        self.last_prepared_tick = sim.tick
        if self.group_claims:
            self.state_version += 1
        self.entry_claims.clear()
        self.group_claims.clear()
        for edge, data in self.road_data.items():
            state = (data["travel_time"], data["capacity"], data.get("blocked", False))
            if state != self.road_state.get(edge):
                self.state_version += 1
                self.lower_bounds.clear()
                self.price_bounds.clear()
                self.open_reachable.clear()
                self.road_state[edge] = state

    def edge_cost(self, sim, edge, extra_vehicles=0):
        data = self.road_data[edge]
        if data.get("blocked", False):
            return float("inf")
        physical = sim.vehicles_on[edge]
        future = max(0, self.planned_on[edge] + extra_vehicles - physical)
        # future cars affect prices but never consume physical space ahead of time
        demand = physical + self.forecast_weight * future
        return bpr_travel_time(data["travel_time"], demand, data["capacity"])

    def has_entry_room(self, sim, group, edge):
        if self.road_data[edge].get("blocked", False):
            return False
        own_claim = 0
        if self.group_claims.get(group.id) == edge:
            own_claim = group.size
        used = sim.vehicles_on[edge] + self.entry_claims.get(edge, 0) - own_claim
        return used + group.size <= CAPACITY_THRESHOLD * self.road_data[edge]["capacity"]

    def claim_entry(self, sim, group, edge):
        if not self.has_entry_room(sim, group, edge):
            return False
        if self.group_claims.get(group.id) != edge:
            self.release_claim(group)
            self.entry_claims[edge] = self.entry_claims.get(edge, 0) + group.size
            self.group_claims[group.id] = edge
            self.state_version += 1
        return True

    def release_claim(self, group):
        edge = self.group_claims.pop(group.id, None)
        if edge is not None:
            self.entry_claims[edge] -= group.size
            self.state_version += 1

    def reachable_nodes(self, sim, sinks):
        reachable = set(sinks)
        pending = list(sorted(sinks))
        while pending:
            v = pending.pop()
            for u, roads in sim.graph.pred[v].items():
                if u in reachable:
                    continue
                for data in roads.values():
                    if not data.get("blocked", False):
                        reachable.add(u)
                        pending.append(u)
                        break
        return reachable

    def demand_distances(self, sim, sinks):
        # cheapest possible trip from each node, before adding any new plans
        def reverse_cost(u, v, roads):
            best_cost = None
            for key, data in roads.items():
                if data.get("blocked", False):
                    continue
                cost = self.edge_cost(sim, (v, u, key))
                if best_cost is None or cost < best_cost:
                    best_cost = cost
            return best_cost

        return nx.multi_source_dijkstra_path_length(sim.graph.reverse(copy=False), sorted(sinks), weight=reverse_cost)

    def spur_path(self, root, blocked_edges, weight, heuristic):
        blocked_nodes = set(root[:-1])

        def spur_weight(u, v, data):
            if v in blocked_nodes or (u, v) in blocked_edges:
                return None
            return weight(u, v, data)

        try:
            return nx.astar_path(self.search_graph, root[-1], self.target,
                                 heuristic=heuristic, weight=spur_weight)
        except nx.NetworkXNoPath:
            return None

    def shortest_paths(self, start, weight, heuristic):
        # Yen's loopless paths, generated only as needed; A* handles each spur search
        path = self.spur_path([start], set(), weight, heuristic)
        if path is None:
            raise nx.NetworkXNoPath
        accepted = [path]
        seen = {tuple(path)}
        candidates = []
        order = count()
        yield path
        while True:
            for i in range(len(path) - 1):
                root = path[:i + 1]
                blocked = set()
                for previous in accepted:
                    if len(previous) > i + 1 and previous[:i + 1] == root:
                        blocked.add((previous[i], previous[i + 1]))
                spur = self.spur_path(root, blocked, weight, heuristic)
                if spur is None:
                    continue
                candidate = root[:-1] + spur
                if tuple(candidate) in seen:
                    continue
                seen.add(tuple(candidate))
                costs = []
                for j in range(len(candidate) - 1):
                    u = candidate[j]
                    v = candidate[j + 1]
                    costs.append(weight(u, v, self.search_graph[u][v]))
                cost = sum(costs)
                heappush(candidates, (cost, next(order), candidate))
            if not candidates:
                return
            cost, tie, path = heappop(candidates)
            accepted.append(path)
            yield path

    def choose_route(self, sim, group, allow_wait=False):
        self.prepare_tick(sim)
        sinks = set(group.destinations)
        start = sim.planning_node(group)
        sink_key = tuple(sorted(sinks))
        if not sinks:
            return None, None
        if sink_key not in self.open_reachable:
            self.open_reachable[sink_key] = self.reachable_nodes(sim, sinks)
        if start not in self.open_reachable[sink_key]:
            return None, None
        if sinks != self.sinks:
            for sink in self.sinks:
                self.search_graph.remove_edge(sink, self.target)
            for sink in sorted(sinks):
                self.search_graph.add_edge(sink, self.target)
            self.sinks = sinks
        if sink_key not in self.lower_bounds:
            def reverse_free_flow(u, v, roads):
                best_time = None
                for data in roads.values():
                    if data.get("blocked", False):
                        continue
                    if best_time is None or data["travel_time"] < best_time:
                        best_time = data["travel_time"]
                return best_time

            # free-flow bounds stay valid as demand and entry claims change
            self.lower_bounds[sink_key] = nx.multi_source_dijkstra_path_length(
                sim.graph.reverse(copy=False), sorted(sinks), weight=reverse_free_flow)
        bounds = self.price_bounds.get(sink_key, self.lower_bounds[sink_key])
        keep = 1 if group.status == TRAVELING else 0
        old_edges = set(self.route_edges.get(group.id, [])[keep:])

        def heuristic(node, target):
            return bounds.get(self.middle_ends.get(node, node), 0)

        def find_route(require_room):
            def weight(u, v, data):
                if v == self.target:
                    return 0
                if u in sinks:
                    return None
                if "road" not in data:
                    return 0
                edge = data["road"]
                road = self.road_data[edge]
                if road.get("blocked", False) or group.size > CAPACITY_THRESHOLD * road["capacity"]:
                    return None
                # filter full first roads before generating k paths; downstream traffic can clear
                if require_room and u == start and not self.has_entry_room(sim, group, edge):
                    return None
                extra = 0 if edge in old_edges else group.size
                return self.edge_cost(sim, edge, extra)

            try:
                for path in islice(self.shortest_paths(start, weight, heuristic), self.k):
                    edges = []
                    route = [start]
                    for i in range(len(path) - 1):
                        u = path[i]
                        v = path[i + 1]
                        data = self.search_graph[u][v]
                        if "road" in data:
                            edge = data["road"]
                            edges.append(edge)
                            route.append(edge[1])
                    return route, edges
            except nx.NetworkXNoPath:
                pass
            return None

        require_room = group.status != TRAVELING
        result = find_route(require_room)
        if result is not None:
            return result
        if require_room and allow_wait:
            # queued groups still get a real route and destination
            result = find_route(False)
            if result is not None:
                return result
            return None, None
        if require_room:
            return [], []
        return None, None

    def add_plan(self, sim, group, edges):
        self.price_bounds.clear()
        for edge in edges:
            self.planned_on[edge] += group.size
        if group.id not in self.route_edges:
            self.route_edges[group.id] = []
        if group.id not in self.assigned_costs:
            self.assigned_costs[group.id] = []
        self.route_edges[group.id].extend(edges)
        for edge in edges:
            self.assigned_costs[group.id].append(self.edge_cost(sim, edge))
        self.state_version += 1

    def release_future(self, group):
        self.release_claim(group)
        keep = 1 if group.status == TRAVELING else 0
        edges = self.route_edges.get(group.id, [])
        if edges[keep:]:
            self.price_bounds.clear()
        for edge in edges[keep:]:
            self.planned_on[edge] -= group.size
        self.route_edges[group.id] = edges[:keep]
        self.assigned_costs[group.id] = self.assigned_costs.get(group.id, [])[:keep]
        self.state_version += 1

    def finish_road(self, sim, group):
        self.prepare_tick(sim)
        self.price_bounds.clear()
        edge = self.route_edges[group.id].pop(0)
        self.planned_on[edge] -= group.size
        self.assigned_costs[group.id].pop(0)
        self.state_version += 1

    def enter_road(self, sim, group):
        self.price_bounds.clear()
        self.release_claim(group)
        self.state_version += 1   # physical occupancy changed, so prices changed too

    def next_edge_key(self, sim, group):
        edges = self.route_edges.get(group.id, [])
        if not edges or self.group_claims.get(group.id) != edges[0]:
            return None
        if self.road_data[edges[0]].get("blocked", False):
            return None
        return edges[0][2]

    def plan_route(self, sim, group):
        route, edges = self.choose_route(sim, group, allow_wait=True)
        if route:
            self.add_plan(sim, group, edges)
            self.assigned_groups.add(group.id)
            self.last_reroute_tick[group.id] = sim.tick
            if edges:
                self.claim_entry(sim, group, edges[0])
        return route

    def assign(self, sim, group, route, edges):
        keep = 1 if group.status == TRAVELING else 0
        old_edges = self.route_edges.get(group.id, [])[keep:]
        if old_edges != edges or group.id not in self.assigned_groups:
            self.release_future(group)
            if group.id in self.assigned_groups:
                changed = sim.reroute(group, route)
                if not changed and old_edges != edges:
                    group.route_changes += 1
            else:
                prefix = group.route[:group.route_index + 1]
                group.route = prefix + route[1:]
                group.destination = route[-1]
                self.assigned_groups.add(group.id)
            self.add_plan(sim, group, edges)
            self.last_reroute_tick[group.id] = sim.tick
        self.needs_route.discard(group.id)
        if group.status == WAITING:
            if group.at_destination():
                group.status = ARRIVED
                group.arrival_tick = sim.tick
            elif edges:
                self.claim_entry(sim, group, edges[0])

    def replan(self, sim, group, allow_wait=False):
        route, edges = sim.search_route(self.choose_route, sim, group, allow_wait=allow_wait, replan=True)
        if route:
            self.assign(sim, group, route, edges)
        elif route is None:
            self.release_future(group)
            keep = group.route_index + (2 if group.status == TRAVELING else 1)
            group.route = group.route[:keep]
            self.needs_route.add(group.id)
            if group.status == WAITING:
                group.status = TRAPPED
                self.needs_route.discard(group.id)
        else:
            self.last_failed_version[group.id] = self.state_version

    def soft_replan(self, sim, group):
        if sim.tick - self.last_reroute_tick[group.id] < self.cooldown:
            return
        if self.event_driven and self.last_failed_version.get(group.id) == self.state_version:
            return
        edges = self.route_edges[group.id][1:]
        baseline = sum(self.assigned_costs[group.id][1:])
        costs = []
        for edge in edges:
            costs.append(self.edge_cost(sim, edge))
        current = sum(costs)
        if current <= self.cost_threshold * baseline:
            return
        sinks = tuple(sorted(group.destinations))
        if sinks not in self.price_bounds:
            self.price_bounds[sinks] = sim.search_route(self.demand_distances, sim, sinks, replan=True)
        # skip the search if this lower bound is already too expensive
        cheapest_possible = self.price_bounds[sinks].get(sim.planning_node(group), float("inf"))
        if cheapest_possible >= self.improvement_threshold * current:
            self.last_failed_version[group.id] = self.state_version
            return
        route, new_edges = sim.search_route(self.choose_route, sim, group, replan=True)
        old_edges = set(edges)
        alternative = float("inf")
        if route:
            costs = []
            for edge in new_edges:
                extra = 0
                if edge not in old_edges:
                    extra = group.size
                costs.append(self.edge_cost(sim, edge, extra))
            alternative = sum(costs)
        if route and alternative < self.improvement_threshold * current:
            self.assign(sim, group, route, new_edges)
        else:
            self.last_failed_version[group.id] = self.state_version

    def update(self, sim):
        self.prepare_tick(sim)
        for group in sim.groups:
            if group.status != WAITING and group.status != TRAVELING:
                continue
            keep = 1 if group.status == TRAVELING else 0
            edges = self.route_edges.get(group.id, [])[keep:]
            blocked = False
            for edge in edges:
                if self.road_data[edge].get("blocked", False):
                    blocked = True
                    break
            if group.id in self.needs_route or blocked:
                self.replan(sim, group, allow_wait=True)   # safety ignores cooldown
            elif group.status == WAITING and edges:
                if self.claim_entry(sim, group, edges[0]):
                    continue
                if self.event_driven and self.last_failed_version.get(group.id) == self.state_version:
                    continue
                has_room = False
                for u, v, key in sim.graph.out_edges(group.current_node, keys=True):
                    if u != v and self.has_entry_room(sim, group, (u, v, key)):
                        has_room = True
                        break
                if has_room:
                    self.replan(sim, group)
            elif group.status == TRAVELING and edges:
                self.soft_replan(sim, group)
