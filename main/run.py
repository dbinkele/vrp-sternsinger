"""Vehicles Routing Problem (VRP)."""

from __future__ import print_function

import sys

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import json
import os

from main.constants import DIST_MATRIX_FILE, INITIAL_SOLUTION
from main.csv_processing import make_formatted_routes
from main.template import render
from main.util import resolve_address_file, print_solution

# 7936/52697
MAX_TIME_DURATION = 60 * 60 * 360

TIME_OUT = 30  # 1220  # 7624/51012

DEPOT = 0

NUM_VEHICLES = 7

DWEL_DURATION = 500

TIME_WINDOWS = False

TOTAL_TIME_WINDOW = (0, 60 * 60 * 24)


def create_data_model(file_name, constraints_file):
    """Stores the data for the problem."""

    with open(constraints_file) as constraints_file_handle:
        constraints = json.load(constraints_file_handle)

        return {'time_matrix': time_matrix(file_name, constraints['fixed_arcs']),
                'num_vehicles': NUM_VEHICLES,
                'depot': DEPOT,
                'same_route': [[61, 77], [], [7, 16], [71], [39], [24, 34], []],
                'different_route': [],
                'dwell_duration': {
                    5: 820,
                    6: 150,
                    19: 150,
                    48: 150,
                    75: 900,
                    76: 150
                },
                'time_windows': {
                    0: (0, 500),
                    5: (3600, 3600 * 24),  #
                }
                }


def time_matrix(file_name, fixed_arcs):
    with open(file_name) as json_file:
        data = json.load(json_file)
        durations = data['durations']

        for fixed_arc in fixed_arcs:
            i = 0
            while i < len(fixed_arc) - 1:
                durations_to_nodes_for_i = durations[fixed_arc[i]]
                for to_node_idx in range(0, len(durations_to_nodes_for_i)):
                    if to_node_idx != fixed_arc[i + 1]:
                        durations_to_nodes_for_i[to_node_idx] = MAX_TIME_DURATION
                durations[fixed_arc[i]] = durations_to_nodes_for_i
                i += 1

        return durations


def dwell_duration_callback(manager, dwel_duration):
    def demand_callback_hlp(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return dwel_duration.get(from_node, DWEL_DURATION) if from_node != 0 else 0

    return demand_callback_hlp


def solve(dist_matrix_file_name, constraints_file):
    """Solve the CVRP problem."""
    # Instantiate the data problem.
    data = create_data_model(dist_matrix_file_name, constraints_file)
    no_visits = len(data['time_matrix'])

    greatest_dist = max([max(e) for e in data['time_matrix']])
    ub_tour = greatest_dist * no_visits + 1
    print("ubtour " + str(ub_tour))
    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(no_visits,
                                           data['num_vehicles'], data['depot'])

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    # Create and register a transit callback.
    def time_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)

        return data['time_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Distance constraint.
    dimension_name = 'Time'
    routing.AddDimension(
        transit_callback_index,
        60 * 60 if TIME_WINDOWS else 0,  # no slack
        # 1773,  # vehicle maximum travel distance
        10000,  # 1608
        not TIME_WINDOWS,  # start cumul to zero
        dimension_name)
    time_dimension = routing.GetDimensionOrDie(dimension_name)
    time_dimension.SetGlobalSpanCostCoefficient(100)

    if TIME_WINDOWS:
        add_time_windows(data, manager, routing, time_dimension)

    ####### Dwell-Duration
    dwell_duration_callback_index = routing.RegisterUnaryTransitCallback(
        dwell_duration_callback(manager, data['dwell_duration']))
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
    # for node in range(1, len(data['time_matrix'])):
    #   routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

    add_same_route_constraints(data, manager, routing)
    add_different_route_constraints(data, manager, routing)

    search_parameters = set_search_parameters()

    # Solve the problem.
    # initial_assignment = routing.ReadAssignmentFromRoutes(INITIAL_SOLUTION, True)
    # solution = routing.SolveFromAssignmentWithParameters(initial_assignment, search_parameters)
    solution = routing.SolveWithParameters(search_parameters)

    print("Solver status: ", routing.status())

    # Print solution on console.
    if solution:
        dwell_duration = dwell_duration_callback(manager, data['dwell_duration'])
        return print_solution(data, manager, routing, solution, dwell_duration)
    else:
        return []


def add_time_windows(data, manager, routing, time_dimension):
    ####Time-Windows
    # Add time window constraints for each location except depot.
    for location_idx in range(len(data['time_matrix'])):
        if location_idx == 0:
            continue
        time_window = data['time_windows'].get(location_idx, TOTAL_TIME_WINDOW)
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
    # Add time window constraints for each vehicle start node.
    for vehicle_id in range(NUM_VEHICLES):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(data['time_windows'][0][0],
                                                data['time_windows'][0][1])
    for i in range(NUM_VEHICLES):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i)))
    routing.AddVariableMinimizedByFinalizer(
        time_dimension.CumulVar(routing.End(i)))


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
    search_parameters.use_full_propagation = 3
    # search_parameters.use_cp_sat = 3
    # search_parameters.use_cp = 3
    # search_parameters.local_search_operators.use_tsp_opt = 3
    # search_parameters.local_search_operators.use_make_chain_inactive = 3
    # search_parameters.local_search_operators.use_extended_swap_active = 3
    search_parameters.local_search_operators.use_path_lns = 3
    search_parameters.local_search_operators.use_full_path_lns = 3
    # search_parameters.local_search_operators.use_tsp_lns = 3
    # search_parameters.local_search_operators.use_inactive_lns = 3
    search_parameters.local_search_operators.use_lin_kernighan = 3
    search_parameters.local_search_operators.use_relocate_and_make_active = 3
    # use_or_opt: BOOL_TRUE
    # : BOOL_TRUE
    # use_make_active: BOOL_TRUE
    # use_make_inactive: BOOL_TRUE
    # use_swap_active: BOOL_TRUE

    # : BOOL_FALSE
    # use_node_pair_swap_active: BOOL_TRUE
    # use_exchange_pair: BOOL_TRUE
    # use_relocate_expensive_chain: BOOL_TRUE
    # use_light_relocate_pair: BOOL_TRUE
    # use_relocate_subtrip: BOOL_TRUE
    # use_exchange_subtrip: BOOL_TRUE
    # search_parameters.guided_local_search_lambda_coefficient = 0.001

    return search_parameters


def main(matrix_file, constraints_file, csv=None, ):
    routes = solve(matrix_file, constraints_file)
    if csv:
        json_routes = make_formatted_routes(routes, csv)
        routes_html = [render(json_route) for json_route in json_routes]
        path = './routes'
        os.system('rm -rf %s/*' % path)
        for idx, route_html in enumerate(routes_html):
            with open('./routes/route_' + str(idx) + '.html', 'w') as file:
                file.write(route_html)


if __name__ == '__main__':
    main(DIST_MATRIX_FILE, str(sys.argv[2]), resolve_address_file())
    # main()
