import sys


def restrict_to_keys(dicto, keys):
    return dict(zip(keys, [dicto[k] for k in keys]))


def json_file_name_from_csv(file_name):
    return file_name.replace('csv', 'json')


def resolve_address_file(address_file):
    if len(sys.argv) > 1:
        address_file = str(sys.argv[1])
    return address_file


def print_solution(data, manager, routing, solution, time_dimesnion):
    """Prints solution on console."""
    max_route_distance = 0
    sum_routes_distances = 0
    routes = [[] for _ in range(data['num_vehicles'])]
    total_route_len = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        routes[vehicle_id].append(manager.IndexToNode(index))
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
        route_distance = 0
        route_len = 0
        while not routing.IsEnd(index):
            time_var = time_dimesnion.CumulVar(index)
            plan_output += ' {0} T({1},{2})-> '.format(manager.IndexToNode(index), solution.Min(time_var),
                                                       solution.Max(time_var))
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            routes[vehicle_id].append(manager.IndexToNode(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)
            route_len += 1

        total_route_len += route_len
        plan_output += '{}\n'.format(manager.IndexToNode(index))
        plan_output += 'Distance of the route: {}m\n'.format(route_distance)
        plan_output += 'Number Visits {}\n'.format(route_len)
        sum_routes_distances += route_distance
        print(plan_output)
        max_route_distance = max(route_distance, max_route_distance)
    print('Maximum of the route distances: {}m'.format(max_route_distance))
    print('Total distance of routes: {}m'.format(sum_routes_distances))
    print('Number of visits: {}m'.format(total_route_len))
    return routes


def check(json_constraints, json_addresses):
    no_locations = len(json_addresses) - 1
    for tag in ['fixed_arcs', 'assign_to_route', 'same_route', 'same_route_ordered', 'different_route']:
        bad_entries = check_index_between(json_constraints[tag], 0, no_locations)
        if bad_entries:
            raise ValueError(
                'Index not between 0 and ' + str(no_locations) + " for tag " + tag + ", but were " + str(bad_entries))

    idxs = [int(idx) for idx in json_constraints['time_windows'].keys()]
    bad_keys = check_index_between([idxs], 0, no_locations)
    if bad_keys:
        raise ValueError(
            "key-index for time-windows not between 0 and  " + str(no_locations) + ", but were " + str(bad_keys))


def check_index_between(nested_list, start, end):
    for inner_list in nested_list:
        bad_entries = [x for x in inner_list if not (start <= x <= end)]
        if len(bad_entries) > 0:
            return bad_entries
    return None
