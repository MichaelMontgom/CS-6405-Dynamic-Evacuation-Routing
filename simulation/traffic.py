from simulation.routing import best_edge_key, bpr_travel_time

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

    @property
    def at_destination(self):
        return self.current_node in self.destinations




class TrafficSimulation:
    # every tick:
    #   1. groups on roads move forward, and get off the road if they're done
    #   2. groups that are supposed to leave this tick get a route
    #   3. groups at intersections try to get on their next road
    # travel time on a road gets locked in when the group gets on it
    # (BPR using how many cars are on it then, rounded to whole ticks)

    def __init__(self, graph, groups, router, max_ticks=1000):
        self.graph = graph
        self.groups = sorted(groups, key=lambda g: g.id)  # always go in the same order so runs match
        self.router = router
        self.max_ticks = max_ticks

        self.tick = 0
        self.history = []

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

        for g in self.groups:
            if g.status == TRAVELING:
                self.move_group(g)

        for g in self.groups:
            if g.status == PENDING and g.departure_tick <= self.tick:
                self.depart_group(g)

        for g in self.groups:
            if g.status == WAITING:
                self.try_enter_next_road(g)

        self.record_tick()

    def move_group(self, g):
        g.remaining_time -= 1
        if g.remaining_time > 0:
            return

        # done with this road
        self.vehicles_on[g.current_edge] -= g.size
        g.current_edge = None
        g.route_index += 1

        if g.current_node == g.destination:
            g.status = ARRIVED
            g.arrival_tick = self.tick
        else:
            g.status = WAITING

    def depart_group(self, g):
        route = self.router(self, g)

        if route is None:
            g.status = TRAPPED
            return

        g.route = route
        g.route_index = 0

        if g.origin == g.destination:
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
            })
        return results

    def summary(self):
        arrived = 0
        trapped = 0
        unfinished = 0
        total_wait = 0
        travel_times = []

        for g in self.groups:
            if g.status == ARRIVED:
                arrived += 1
                travel_times.append(g.travel_time)
            elif g.status == TRAPPED:
                trapped += 1
            else:
                unfinished += 1
            total_wait += g.wait_ticks

        mean_travel_time = None
        max_travel_time = None
        if len(travel_times) > 0:
            mean_travel_time = sum(travel_times) / len(travel_times)
            max_travel_time = max(travel_times)

        completion_rate = 0
        if len(self.groups) > 0:
            completion_rate = arrived / len(self.groups)

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
        }
