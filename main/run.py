"""Vehicles Routing Problem (VRP)."""

from __future__ import print_function

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import json
import os

from main.constants import DIST_MATRIX_FILE
from main.csv_processing import make_formatted_routes
from main.template import render
from main.util import dummy_dist_matrix, resolve_address_file, print_solution

TIME_OUT = 320

DEPOT = 0

NUM_VEHICLES = 7

DWEL_DURATION = 500


def create_data_model(file_name=None):
    """Stores the data for the problem."""
    data = {'distance_matrix': dist_matrix(file_name) if file_name else dummy_dist_matrix(),
            'num_vehicles': NUM_VEHICLES,
            'depot': DEPOT,
            'same_route': [[61, 68], [12, 32, 30]],
            'different_route': [[39, 65], [72, 71]]}

    return data


def dist_matrix(file_name):
    with open(file_name) as json_file:
        data = json.load(json_file)
        return data['durations']


def dwell_duration_callback(manager):
    def demand_callback_hlp(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return DWEL_DURATION if from_node != 0 else 0

    return demand_callback_hlp


def solve(dist_matrix_file_name=None):
    """Solve the CVRP problem."""
    # Instantiate the data problem.
    data = create_data_model(dist_matrix_file_name)
    no_visits = len(data['distance_matrix'])

    greatest_dist = max([max(e) for e in data['distance_matrix']])
    ub_tour = greatest_dist * no_visits + 1
    print("ubtour " + str(ub_tour))
    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(no_visits,
                                           data['num_vehicles'], data['depot'])

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    # Create and register a transit callback.
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Distance constraint.
    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        # 1773,  # vehicle maximum travel distance
        100841,  # 1608
        True,  # start cumul to zero
        dimension_name)
    distance_dimension = routing.GetDimensionOrDie(dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(100)

    dwell_duration_callback_index = routing.RegisterUnaryTransitCallback(dwell_duration_callback(manager))
    routing.AddDimension(
        dwell_duration_callback_index,
        0,  # null capacity slack
        (no_visits + 1) * DWEL_DURATION,  # vehicle maximum capacities
        True,  # start cumul to zero
        'DWEL_DURATION')

    capacity_dimension = routing.GetDimensionOrDie('DWEL_DURATION')
    capacity_dimension.SetGlobalSpanCostCoefficient(100)

    # Allow to drop nodes.
    # penalty = ub_tour
    # for node in range(1, len(data['distance_matrix'])):
    #   routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

    add_same_route_constraints(data, manager, routing)
    add_different_route_constraints(data, manager, routing)

    search_parameters = set_search_parameters()

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    print("Solver status: ", routing.status())

    # Print solution on console.
    if solution:
        dwell_duration = dwell_duration_callback(manager)
        return print_solution(data, manager, routing, solution, dwell_duration)
    else:
        return []


def add_same_route_constraints(data, manager, routing):
    for vehicle_idx, route_constraint in enumerate(data['same_route']):
        n2x = manager.NodeToIndex
        cpsolver = routing.solver()

        for stop in route_constraint:
            vehicle_var = routing.VehicleVar(n2x(stop))
            values = [-1, vehicle_idx]
            cpsolver.Add(cpsolver.MemberCt(vehicle_var, values))


def add_different_route_constraints(data, manager, routing):
    for node1, node2 in data['different_route']:
        n2x = manager.NodeToIndex
        cpsolver = routing.solver()
        vehicle_var_1 = routing.VehicleVar(n2x(node1))
        vehicle_var_2 = routing.VehicleVar(n2x(node2))
        cpsolver.Add(cpsolver.AllDifferent([vehicle_var_1, vehicle_var_2]))
    # cpsolver.Add((vehicle_var_1 != vehicle_var_2) or (vehicle_var_1 == -1 and vehicle_var_2 == -1))
    # cpsolver.Add(vehicle_var_2 == 2)
    # cpsolver.Add(vehicle_var_1 == 3)


def set_search_parameters():
    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)  # PATH_CHEAPEST_ARC 6990
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.seconds = TIME_OUT
    # search_parameters.log_search = True
    # search_parameters.use_depth_first_search = True
    # search_parameters.use_full_propagation = True
    #search_parameters.use_cp_sat = 3
    # search_parameters.use_cp = 3
    # search_parameters.local_search_operators.use_tsp_opt = 3
    # search_parameters.local_search_operators.use_make_chain_inactive = 3
    # search_parameters.local_search_operators.use_extended_swap_active = 3
    search_parameters.local_search_operators.use_path_lns = 3
    search_parameters.local_search_operators.use_full_path_lns = 3
    #search_parameters.local_search_operators.use_tsp_lns = 3
    search_parameters.local_search_operators.use_inactive_lns = 3

    # use_or_opt: BOOL_TRUE
    # use_lin_kernighan: BOOL_TRUE
    # use_make_active: BOOL_TRUE
    # use_make_inactive: BOOL_TRUE
    # use_swap_active: BOOL_TRUE

    # : BOOL_FALSE
    # use_node_pair_swap_active: BOOL_TRUE
    # use_relocate_and_make_active: BOOL_FALSE
    # use_exchange_pair: BOOL_TRUE
    # use_relocate_expensive_chain: BOOL_TRUE
    # use_light_relocate_pair: BOOL_TRUE
    # use_relocate_subtrip: BOOL_TRUE
    # use_exchange_subtrip: BOOL_TRUE
    #search_parameters.guided_local_search_lambda_coefficient = 0.001
    return search_parameters


def main(matrix_file=None, csv=None):
    routes = solve(matrix_file)
    if csv:
        json_routes = make_formatted_routes(routes, csv)
        routes_html = [render(json_route) for json_route in json_routes]
        path = './routes'
        os.system('rm -rf %s/*' % path)
        for idx, route_html in enumerate(routes_html):
            with open('./routes/route_' + str(idx) + '.html', 'w') as file:
                file.write(route_html)


if __name__ == '__main__':
    main(DIST_MATRIX_FILE, resolve_address_file())
    # main()
