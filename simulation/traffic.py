from simulation.routing import best_edge_key, bpr_travel_time
import time

CAPACITY_THRESHOLD = 0.95

# group statuses
PENDING = "pending"        # hasnt left yet
WAITING = "waiting"        # stuck at an intersection waiting to get on the next road
TRAVELING = "traveling"    # on a road
ARRIVED = "arrived"
TRAPPED = "trapped"        # no route at all


class Group:
    def __init__(self, id, size, origin, destination=None, departure_tick=0, destinations=None):
        self.id = id
        self.size = size
        self.origin = origin
        if destinations is None:
            destinations = [destination]
        self.destinations = destinations
        self.destination = destination
        self.departure_tick = departure_tick

        self.status = PENDING
        self.route = []
        self.route_index = 0        # which node in the route we're at
        self.current_edge = None    # (u, v, key) while on a road
        self.remaining_time = 0     # ticks left on the current road
        self.arrival_tick = None
        self.wait_ticks = 0

        self.route_changes = 0      # to count the number of times a group has been rerouted
        self.free_flow_time = None  # to compare against the algorithm's time

    def __repr__(self):
        return f"Group(id={self.id}, size={self.size}, {self.origin} -> {self.destination}, leaves at {self.departure_tick}, {self.status})"

    @property
    def current_node(self):
        if len(self.route) == 0:
            return self.origin
        return self.route[self.route_index]

    @property
    def next_node(self):
        if self.route_index + 1 < len(self.route):
            return self.route[self.route_index + 1]
        return None

    @property
    def travel_time(self):
        if self.arrival_tick is None:
            return None
        return self.arrival_tick - self.departure_tick

    def at_destination(self):
        return self.current_node in self.destinations


class RouterAlgorithm:

    def __init__(self, router, name=None):
        self.router = router
        self.name = name or router.__name__

    def plan_route(self, sim, group):
        return self.router(sim, group)

    def update(self, sim):
        pass

class TrafficSimulation:
    # every tick:
    #   1. groups on roads move forward, and get off the road if they're done
    #   2. groups that are supposed to leave this tick get a route
    #   3. groups at intersections try to get on their next road
    # travel time on a road gets locked in when the group gets on it
    # (BPR using how many cars are on it then, rounded to whole ticks)

    def __init__(self, graph, groups, algorithm, max_ticks=1000, closures=None):
        self.graph = graph
        self.groups = sorted(groups, key=lambda g: g.id)  # always go in the same order so runs match
        self.max_ticks = max_ticks

        if callable(algorithm) and not hasattr(algorithm, "plan_route"):
            algorithm = RouterAlgorithm(algorithm)
        self.algorithm = algorithm

        if closures is None:
            closures = []
        self.closures = sorted(closures)

        self.tick = 0
        self.history = []

        # statistics gathering variables
        self.plan_time = 0
        self.update_time = 0
        self.reroute_events = 0

        # how many vehicles are on each road right now
        self.vehicles_on = {}
        for edge in graph.edges(keys=True):
            self.vehicles_on[edge] = 0

    def has_room(self, edge, size):
        capacity = self.graph.edges[edge]["capacity"]
        return self.vehicles_on[edge] + size <= CAPACITY_THRESHOLD * capacity

    def is_finished(self):
        for g in self.groups:
            if g.status != ARRIVED and g.status != TRAPPED:
                return False
        return True

    def step(self):
        self.tick += 1

        self.apply_closures()

        for g in self.groups:
            if g.status == TRAVELING:
                self.move_group(g)

        for g in self.groups:
            if g.status == PENDING and g.departure_tick <= self.tick:
                self.depart_group(g)

        # calculate time while algorithm runs an update on the graph
        start = time.perf_counter()
        self.algorithm.update(self)
        self.update_time += time.perf_counter() - start

        for g in self.groups:
            if g.status == WAITING:
                self.try_enter_next_road(g)

        self.record_tick()

    def reroute(self, g, new_route):
        self.reroute_events += 1
        start = self.planning_node(g)

        if new_route is None or len(new_route) == 0 or new_route[0] != start:
            raise ValueError(f"Group {g.id}: new route has to start at node {start}")

        if g.status == TRAVELING:
            keep = g.route[:g.route_index + 2]
        else:
            keep = g.route[:g.route_index + 1]

        old_rest = g.route[len(keep) - 1:]
        if new_route == old_rest:
            return False  # same route, not a flip

        g.route = keep + new_route[1:]
        g.destination = new_route[-1]
        g.route_changes += 1
        return True

    def depart_group(self, g):
        start = time.perf_counter()
        route = self.algorithm.plan_route(self, g)
        self.plan_time += time.perf_counter() - start

        if route is None:
            g.status = TRAPPED
            return

        g.route = route
        g.route_index = 0
        g.destination = route[-1]

        if g.at_destination():
            g.status = ARRIVED
            g.arrival_tick = self.tick
        else:
            g.status = WAITING

    def planning_node(self, g):
        if g.status == TRAVELING:
            return g.route[g.route_index + 1]
        return g.current_node

    def move_group(self, g):
        g.remaining_time -= 1
        if g.remaining_time > 0:
            return

        # done with this road
        self.vehicles_on[g.current_edge] -= g.size
        g.current_edge = None
        g.route_index += 1

        if g.at_destination():
            g.status = ARRIVED
            g.arrival_tick = self.tick
        else:
            g.status = WAITING



    def try_enter_next_road(self, g):
        u = g.current_node
        v = g.next_node
        key = best_edge_key(self.graph, u, v)

        # road is blocked or full, wait here
        if key is None or not self.has_room((u, v, key), g.size):
            g.wait_ticks += 1
            return

        edge = (u, v, key)
        self.vehicles_on[edge] += g.size

        data = self.graph.edges[edge]
        time = bpr_travel_time(data["travel_time"], self.vehicles_on[edge], data["capacity"])

        g.current_edge = edge
        g.remaining_time = max(1, round(time))
        g.status = TRAVELING

    def record_tick(self):
        row = {"tick": self.tick, PENDING: 0, WAITING: 0, TRAVELING: 0, ARRIVED: 0, TRAPPED: 0}
        for g in self.groups:
            row[g.status] += 1

        row["vehicles_on_roads"] = sum(self.vehicles_on.values())
        self.history.append(row)

    def run(self):
        while not self.is_finished() and self.tick < self.max_ticks:
            self.step()
        return self

    def group_results(self):
        results = []
        for g in self.groups:
            results.append({
                "group_id": g.id,
                "size": g.size,
                "origin": g.origin,
                "destination": g.destination,
                "departure_tick": g.departure_tick,
                "status": g.status,
                "arrival_tick": g.arrival_tick,
                "travel_time": g.travel_time,
                "wait_ticks": g.wait_ticks,
                "route": g.route,
                "route_changes": g.route_changes,
                "free_flow_time": g.free_flow_time,
            })
        return results

    def summary(self):
        arrived = 0
        trapped = 0
        unfinished = 0
        total_wait = 0
        travel_times = []

        total_evacuees = 0
        arrived_evacuees = 0
        trapped_evacuees = 0
        stuck_evacuees = 0

        weighted_travel_time = 0
        weighted_delay = 0
        delay_evacuees = 0

        path_flips_total = 0
        weighted_flips = 0

        for g in self.groups:
            total_evacuees += g.size
            total_wait += g.wait_ticks
            path_flips_total += g.route_changes
            weighted_flips += g.route_changes * g.size

            if g.status == ARRIVED:
                arrived += 1
                arrived_evacuees += g.size
                travel_times.append(g.travel_time)
                weighted_travel_time += g.travel_time * g.size

                # delay = how much longer the trip took than it would have on empty roads
                if g.free_flow_time is not None:
                    weighted_delay += (g.travel_time - g.free_flow_time) * g.size
                    delay_evacuees += g.size

            elif g.status == TRAPPED:
                trapped += 1
                trapped_evacuees += g.size
            else:
                unfinished += 1
                stuck_evacuees += g.size

            # old stuff, still per group
        mean_travel_time = None
        max_travel_time = None
        if len(travel_times) > 0:
            mean_travel_time = sum(travel_times) / len(travel_times)
            max_travel_time = max(travel_times)

        completion_rate = 0
        if len(self.groups) > 0:
            completion_rate = arrived / len(self.groups)

        t_clear = None
        t_clear_90 = None

        arrived_groups = []
        for g in self.groups:
            if g.status == ARRIVED:
                arrived_groups.append(g)
        arrived_groups.sort(key=lambda g: (g.arrival_tick, g.id))

        if len(arrived_groups) > 0:
            t_clear = arrived_groups[-1].arrival_tick

        out_so_far = 0
        for g in arrived_groups:
            out_so_far += g.size
            if out_so_far >= 0.9 * total_evacuees:
                t_clear_90 = g.arrival_tick
                break

        # evacuation success rate - evacuees not groups
        success_rate = 0
        if total_evacuees > 0:
            success_rate = arrived_evacuees / total_evacuees

        # average travel time and delay per evacuee (only people who got out)
        avg_travel_time = None
        if arrived_evacuees > 0:
            avg_travel_time = weighted_travel_time / arrived_evacuees

        avg_delay = None
        if delay_evacuees > 0:
            avg_delay = weighted_delay / delay_evacuees

        # how many times routes got switched, per evacuee
        path_flips_per_vehicle = 0
        if total_evacuees > 0:
            path_flips_per_vehicle = weighted_flips / total_evacuees

        # total time the algorithm spent thinking, and average time per reroute
        algorithm_time = self.plan_time + self.update_time

        avg_reroute_latency_ms = None
        if self.reroute_events > 0:
            avg_reroute_latency_ms = self.update_time / self.reroute_events * 1000

        return {

            "ticks": self.tick,
            "groups": len(self.groups),
            "arrived": arrived,
            "trapped": trapped,
            "unfinished": unfinished,
            "completion_rate": completion_rate,
            "mean_travel_time": mean_travel_time,
            "max_travel_time": max_travel_time,
            "total_wait_ticks": total_wait,


            "t_clear": t_clear,
            "t_clear_90": t_clear_90,
            "total_evacuees": total_evacuees,
            "arrived_evacuees": arrived_evacuees,
            "trapped_evacuees": trapped_evacuees,
            "stuck_evacuees": stuck_evacuees,
            "success_rate": success_rate,
            "avg_travel_time": avg_travel_time,
            "avg_delay": avg_delay,
            "path_flips_total": path_flips_total,
            "path_flips_per_vehicle": path_flips_per_vehicle,
            "plan_time": self.plan_time,
            "update_time": self.update_time,
            "algorithm_time": algorithm_time,
            "reroute_events": self.reroute_events,
            "avg_reroute_latency_ms": avg_reroute_latency_ms,
        }

    def apply_closures(self):
        for tick, u, v in self.closures:
            if tick != self.tick:
                continue

            if self.graph.has_edge(u, v):
                for key in self.graph[u][v]:
                    self.graph[u][v][key]["blocked"] = True

            if self.graph.has_edge(v, u):
                for key in self.graph[v][u]:
                    self.graph[v][u][key]["blocked"] = True
