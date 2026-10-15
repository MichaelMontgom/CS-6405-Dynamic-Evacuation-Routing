from simulation.graphs import grid_graph, line_graph, two_route_graph
from simulation.routing import congestion_dijkstra_router, static_dijkstra_router
from simulation.scenarios import generate_groups, run_trials
from simulation.traffic import ARRIVED, TRAPPED, WAITING, Group, TrafficSimulation


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
    assert first.equals(second)
