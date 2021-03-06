"""Vehicles Routing Problem (VRP)."""

from __future__ import print_function

import json
import os
import sys

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

from main.constants import DIST_MATRIX_FILE, ADDRESS_CSV
from main.cmd.csv_processing import make_formatted_routes
from main.template import render
from main.util import resolve_address_file, print_solution, json_file_name_from_csv, check

MAX_TIME_DURATION = 60 * 60 * 360 * 1000


def create_data_model(dist_matrix, json_constraints):
    """Stores the data for the problem."""
    time = time_matrix(dist_matrix, json_constraints['fixed_arcs'])
    depot_idx = json_constraints['depot']
    default_dwell_duration = json_constraints['dwell_duration'][-1]
    for i in range(0, len(time)):
        for j in range(0, len(time[i])):
            time[i][j] += default_dwell_duration if i != depot_idx and j != depot_idx else 0

    dwell_duration = json_constraints['dwell_duration']
    for idx, duration in dwell_duration.items():
        for idx2, item in enumerate(time[idx]):
            time[idx][idx2] += (duration - default_dwell_duration) if idx != -1 else 0
    result = {'time_matrix': time}
    result.update(json_constraints)
    return result


def time_matrix(dist_matrix, fixed_arcs):
    durations = dist_matrix['durations']

    for fixed_arc in fixed_arcs:
        for i in range(0, len(fixed_arc) - 1):
            durations_to_nodes_for_i = durations[fixed_arc[i]]
            for to_node_idx in range(0, len(durations_to_nodes_for_i)):
                if to_node_idx != fixed_arc[i + 1]:
                    durations_to_nodes_for_i[to_node_idx] = MAX_TIME_DURATION
            durations[fixed_arc[i]] = durations_to_nodes_for_i

    return durations


def solve(dist_matrix, json_constraints):
    print("---->Solve")
    depot_idx = json_constraints['depot']

    """Solve the CVRP problem."""
    # Instantiate the data problem.
    data = create_data_model(dist_matrix, json_constraints)
    no_visits = len(data['time_matrix'])

    greatest_dist = max([max(e) for e in data['time_matrix']])
    greatest_dwell_time = max(data['dwell_duration'].values())
    ub_tour = int((greatest_dist + greatest_dwell_time) * no_visits + 1) + 1
    mult_num_visits, mult_max_tour_len = data['num_visits_to_max_tour_len_ration']
    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(no_visits,
                                           data['num_vehicles'], depot_idx)

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

    time_windows_exist = len(data['time_windows']) > 0
    # Add Distance constraint.
    dimension_name = 'Time'
    routing.AddDimension(
        transit_callback_index,
        60 * 60 if time_windows_exist else 0,  # no slack
        ub_tour,  # 1608
        not time_windows_exist,  # start cumul to zero
        dimension_name)
    time_dimension = routing.GetDimensionOrDie(dimension_name)
    time_dimension.SetGlobalSpanCostCoefficient(100 * mult_max_tour_len)

    if time_windows_exist:
        add_time_windows(data, manager, routing, time_dimension)

    ####### Dwell-Duration
    dimension_num_visits = 'NUM_VISITS'
    routing.AddDimension(
        routing.RegisterUnaryTransitCallback(lambda from_node: 1),
        0,  # null capacity slack
        (no_visits + 1),  # vehicle maximum capacities
        True,  # start cumul to zero
        dimension_num_visits)

    capacity_dimension = routing.GetDimensionOrDie(dimension_num_visits)
    capacity_dimension.SetGlobalSpanCostCoefficient(100 * mult_num_visits)

    # Allow to drop nodes.
    # penalty = ub_tour
    # for node in range(1, len(data['time_matrix'])):
    #   routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

    add_assign_to_route_constraints(data['assign_to_route'], manager, routing)
    add_same_route_constraints(data['same_route'], manager, routing)
    add_same_route_constraints(data['same_route_ordered'], manager, routing, time_dimension)
    add_different_route_constraints(data, manager, routing)

    search_parameters = set_search_parameters(data['timeout'])

    # Solve the problem.
    # initial_assignment = routing.ReadAssignmentFromRoutes(INITIAL_SOLUTION, True)
    # solution = routing.SolveFromAssignmentWithParameters(initial_assignment, search_parameters)
    print("Start Solving")
    solution = routing.SolveWithParameters(search_parameters)

    print("Solver status: ", routing.status())

    # Print solution on console.
    if solution:
        return print_solution(data, manager, routing, solution, routing.GetDimensionOrDie(dimension_name))
    else:
        return []


def add_time_windows(data, manager, routing, time_dimension):
    # Add time window constraints for each location except depot.
    for location_idx in range(len(data['time_matrix'])):
        if location_idx == 0:
            continue
        time_window = data['time_windows'].get(str(location_idx), None)
        if time_window:
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
    # Add time window constraints for each vehicle start node.
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(data['time_windows'][0][0],
                                                data['time_windows'][0][1])
    for i in range(data['num_vehicles']):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i)))
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.End(i)))


def add_assign_to_route_constraints(route_assignments, manager, routing):
    n2x = manager.NodeToIndex
    cpsolver = routing.solver()

    for route_idx, route_assignment in enumerate(route_assignments):
        for stop in route_assignment:
            vehicle_var = routing.VehicleVar(n2x(stop))
            values = [-1, route_idx]
            cpsolver.Add(cpsolver.MemberCt(vehicle_var, values))


def add_same_route_constraints(same_routes, manager, routing, time_dimension=None):
    for same_route_constraint in same_routes:
        n2x = manager.NodeToIndex
        cpsolver = routing.solver()

        for stop1, stop2 in zip(same_route_constraint, same_route_constraint[1:]):
            routing.AddPickupAndDelivery(n2x(stop1), n2x(stop2))
            cpsolver.Add(routing.VehicleVar(n2x(stop1)) == routing.VehicleVar(n2x(stop2)))
            if time_dimension:
                cpsolver.Add(
                    time_dimension.CumulVar(n2x(stop1)) <=
                    time_dimension.CumulVar(n2x(stop2)))


def add_different_route_constraints(data, manager, routing):
    for node1, node2 in data['different_route']:
        n2x = manager.NodeToIndex
        cpsolver = routing.solver()
        vehicle_var_1 = routing.VehicleVar(n2x(node1))
        vehicle_var_2 = routing.VehicleVar(n2x(node2))
        cpsolver.Add(cpsolver.AllDifferent([vehicle_var_1, vehicle_var_2]))


def set_search_parameters(time_out):
    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    # PATH_CHEAPEST_ARC 7640 PATH_CHEAPEST_ARC 7533  LOCAL_CHEAPEST_INSERTION 7613
    # GLOBAL_CHEAPEST_ARC 7591 LOCAL_CHEAPEST_ARC 7587
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.seconds = time_out
    search_parameters.log_search = True
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
    search_parameters.guided_local_search_lambda_coefficient = 0.25
    # search_parameters.lns_time_limit.seconds = 100
    return search_parameters


def mainrunner(matrix_file, json_constraints, json_addresses):
    routes = solve(matrix_file, json_constraints)
    return make_formatted_routes(routes, json_addresses)


def main():
    csv = resolve_address_file(ADDRESS_CSV)
    constraints_file = str(sys.argv[2])
    with open(json_file_name_from_csv(csv), 'rb') as adress_file:
        json_addresses = json.load(adress_file)
    with open(constraints_file) as constraints_file_handle:
        json_constraints = json.load(constraints_file_handle)
    dist_matrix_file = str(sys.argv[3])
    with open(dist_matrix_file) as dist_matrix_file:
        dist_matrix = json.load(dist_matrix_file)

    check(json_constraints, json_addresses)

    json_routes = mainrunner(dist_matrix, json_constraints, json_addresses)
    routes_html = [render(json_route, 'templates/template.html', 'foot') for json_route in json_routes]

    path = './routes'
    os.system('rm -rf %s/*' % path)
    for idx, route_html in enumerate(routes_html):
        with open(path + '/route_' + str(idx) + '.html', 'w') as outfile:
            outfile.write(route_html)


if __name__ == '__main__':
    main()
