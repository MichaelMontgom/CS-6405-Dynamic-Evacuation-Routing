from simulation.graphs import grid_graph, line_graph, two_route_graph
from simulation.routing import congestion_dijkstra_router, static_dijkstra_router
from simulation.scenarios import generate_groups, run_trials
from simulation.traffic import ARRIVED, TRAPPED, WAITING, Group, TrafficSimulation, TRAVELING
from simulation.routing import dijkstra_route


def test_single_group_free_flow():
    graph = line_graph(num_nodes=4, travel_time=5)
    group = Group(id=0, size=1, origin=0, destination=3, departure_tick=1)

    sim = TrafficSimulation(graph, [group], static_dijkstra_router)
    sim.run()

    assert group.status == ARRIVED
    assert group.route == [0, 1, 2, 3]
    assert group.travel_time == 15  # 3 roads * 5 ticks
    assert sum(sim.vehicles_on.values()) == 0


def test_group_waits_when_road_is_full():
    # fast road fits 9.5 cars, so the second group of 5 has to wait for the first one to get off
    graph = two_route_graph(fast_time=5, fast_capacity=10)
    g0 = Group(id=0, size=5, origin=0, destination=3, departure_tick=1)
    g1 = Group(id=1, size=5, origin=0, destination=3, departure_tick=1)

    sim = TrafficSimulation(graph, [g0, g1], static_dijkstra_router)
    sim.run()

    assert g0.wait_ticks == 0
    assert g1.wait_ticks == 5
    assert g1.arrival_tick == g0.arrival_tick + 5


def test_group_trapped_without_route():
    graph = two_route_graph()
    graph.edges[0, 1, 0]["blocked"] = True
    graph.edges[0, 2, 0]["blocked"] = True
    group = Group(id=0, size=1, origin=0, destination=3, departure_tick=1)

    sim = TrafficSimulation(graph, [group], static_dijkstra_router)
    sim.run()

    assert group.status == TRAPPED


def test_static_route_gets_stuck_when_road_ahead_is_blocked():
    graph = two_route_graph(fast_time=5)
    group = Group(id=0, size=1, origin=0, destination=3, departure_tick=1)
    sim = TrafficSimulation(graph, [group], static_dijkstra_router, max_ticks=50)

    # leave, then block the second road on the route
    sim.step()
    graph.edges[1, 3, 0]["blocked"] = True
    sim.run()

    assert group.status == WAITING
    assert group.current_node == 1
    assert sim.tick == 50
    assert sim.summary()["unfinished"] == 1


def run_grid(seed, router=static_dijkstra_router):
    graph = grid_graph(rows=5, cols=5, capacity=15, seed=seed)
    groups = generate_groups(graph, num_groups=40, seed=seed, departure_window=5)
    sim = TrafficSimulation(graph, groups, router)
    sim.run()
    return sim


def test_same_seed_gives_same_results():
    first = run_grid(seed=7)
    second = run_grid(seed=7)

    assert first.group_results() == second.group_results()
    assert first.history == second.history


def test_different_seed_gives_different_groups():
    assert run_grid(seed=1).group_results() != run_grid(seed=2).group_results()


def test_all_groups_finish_on_open_grid():
    for router in [static_dijkstra_router, congestion_dijkstra_router]:
        summary = run_grid(seed=3, router=router).summary()
        assert summary["completion_rate"] == 1


def make_test_grid():
    return grid_graph(rows=4, cols=4, capacity=10, seed=0)


def test_run_trials_is_reproducible():
    routers = {"static": static_dijkstra_router, "congestion": congestion_dijkstra_router}

    first = run_trials(make_test_grid, routers, seeds=[0, 1, 2], num_groups=30)
    second = run_trials(make_test_grid, routers, seeds=[0, 1, 2], num_groups=30)

    assert len(first) == 6

    # cpu times are a little different every run, so leave them out
    timing_columns = ["plan_time", "update_time"]
    assert first.drop(columns=timing_columns).equals(second.drop(columns=timing_columns))




class SwitchAtTick:
    # fake algorithm for testing - plans the fast route, then at switch_tick
    # sends everyone down whatever dijkstra says from where they are
    def __init__(self, switch_tick):
        self.switch_tick = switch_tick
        self.name = "switch"

    def plan_route(self, sim, group):
        return dijkstra_route(sim.graph, group.current_node, group.destination)

    def update(self, sim):
        if sim.tick != self.switch_tick:
            return
        for g in sim.groups:
            if g.status == WAITING or g.status == TRAVELING:
                new_route = dijkstra_route(sim.graph, sim.planning_node(g), g.destinations[0])
                if new_route is not None:
                    sim.reroute(g, new_route)


def test_closure_blocks_both_directions():
    graph = two_route_graph()
    sim = TrafficSimulation(graph, [], static_dijkstra_router, closures=[(1, 1, 3)])
    sim.step()
    assert graph.edges[1, 3, 0]["blocked"]
    assert graph.edges[3, 1, 0]["blocked"]


def test_reroute_keeps_traveling_group_on_its_road():
    # close 1->3 at tick 2 while the group is on 0->1, then reroute at tick 2
    graph = two_route_graph(fast_time=5)
    g = Group(id=0, size=1, origin=0, destination=3, departure_tick=1)
    sim = TrafficSimulation(graph, [g], SwitchAtTick(switch_tick=2), closures=[(2, 1, 3)])
    sim.run()

    assert g.route == [0, 1, 0, 2, 3]   # finished 0->1, then had to turn around
    assert g.route_changes == 1
    assert g.status == ARRIVED


def test_same_route_is_not_a_flip():
    graph = two_route_graph()
    g = Group(id=0, size=1, origin=0, destination=3, departure_tick=1)
    sim = TrafficSimulation(graph, [g], SwitchAtTick(switch_tick=3))
    sim.run()

    assert g.route_changes == 0
    assert sim.reroute_events == 1


def test_any_sink_counts_as_arriving():
    graph = line_graph(num_nodes=4, travel_time=5)
    g = Group(id=0, size=1, origin=0, destination=3, departure_tick=1, destinations=[2, 3])
    sim = TrafficSimulation(graph, [g], static_dijkstra_router)
    sim.run()

    assert g.status == ARRIVED
    assert g.travel_time == 10   # stopped at node 2, not 3