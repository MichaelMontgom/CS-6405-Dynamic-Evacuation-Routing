# settings for main.py
GRAPH_FILE = "data/road_networks/kennesaw_road_network.graphml"
SEEDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
NUM_GROUPS = 2000
GROUP_SIZE_RANGE = (1, 5)
DEPARTURE_WINDOW = 5
MAX_TICKS = 5000

# None picks random sinks, or use a list of node ids from the selected map
SINKS = None
NUM_SINKS = 3
SINK_SEED = None   # None uses the trial seed; set 1 to keep sinks fixed across trials

# None picks roads to close, [] means no closures
# manual closures are (tick, u, v) and close both directions
CLOSURES = None
NUM_CLOSURES = 10
CLOSURE_TICK_RANGE = (30, 120)
CLOSURE_SEED = None   # None uses the trial seed
BUSIEST_ROADS = 50

ALGORITHMS = ["static", "periodic_dijkstra", "local_greedy", "dcas"]
PERIODIC_INTERVAL = 300
DCAS_OPTIONS = {
    "k": 3,
    "cooldown": 3,
    "cost_threshold": 1.30,
    "improvement_threshold": 0.80,
    "event_driven": True,
    "forecast_weight": 0.25,
}

PLOT_ROUTES = True   # plots a few reroutes from the last simulation
