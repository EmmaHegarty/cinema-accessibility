from os import path
from numpy import load, save
from numpy import append as np_append
from rpy2 import robjects as ro
from rpy2.robjects import pandas2ri
from pandas import DataFrame, Timedelta, read_csv, isnull

from scripts.utils import gtfs_time_to_pandas_datetime
from scripts.constants import RESULTS_PATH
from scripts.routing.ors_routing import get_walk_to_station

# R functions
r_library = ro.r['library']
r_parse = ro.r['parse']
r_eval = ro.r['eval']
r_datetime = ro.r['as.POSIXct']
r_difftime = ro.r['difftime']

# get R libraries
r_library('gtfsrouter')

# gtfsrouter functions
r_extract_gtfs = ro.r['extract_gtfs']
r_gtfs_transfer_table = ro.r['gtfs_transfer_table']
r_gtfs_timetable = ro.r['gtfs_timetable']
r_gtfs_route = ro.r['gtfs_route']


# get duration of fastest route, return list of datetime durations
# {args} routes: [df], date: str, only_fastest: boolean, only_one: boolean
# {returns} dataframe or dict
def get_route_duration(routes, date='20240106', only_fastest=True, only_one=False):
    def calc_dur(route):
        if isinstance(route, DataFrame):
            start_t = gtfs_time_to_pandas_datetime(date, route['departure_time'].iloc[0])
            end_t = gtfs_time_to_pandas_datetime(date, route['arrival_time'].iloc[len(route) - 1])
            diff = end_t - start_t

            return diff

    if only_one:
        return calc_dur(routes)

    # go over all routes and calculate duration
    dur_opt = [calc_dur(route) for route in routes]
    route_id = range(len(dur_opt))

    # return error if no duration could be calculated
    if dur_opt == [] or all([not isinstance(route, Timedelta) for route in dur_opt]):
        raise Exception('duration can be calculated for no route')
    # return duration for all routes
    elif not only_fastest:
        df = DataFrame({'duration': dur_opt, 'route_id': route_id})
        return df.sort_values('duration')
    # return duration and id of the fastest route in list
    else:
        durations = list(filter(lambda item: isinstance(item, Timedelta), dur_opt))
        min_route = min(durations)
        min_route_id = route_id[dur_opt.index(min_route)]
        fastest_out_of = len(durations)

        return {'duration': min_route, 'route_id': min_route_id, 'out_of': fastest_out_of}


# {args} duration: Timedelta, walk: [Timedelta]
# {returns} Timedelta
def timedelta_addition(duration, walk):
    if walk is None or walk[0] is None or walk[1] is None or isnull(duration):
        return None
    else:
        return duration + walk[0] + walk[1]


# get GTFS files and format them
# {args} filename: str, weekday: str
# {returns} gtfs feed to be processed by R gtfsrouter
def format_gtfs(filename, weekday):
    zip_file = path.join('gtfs_files/', f'{filename}.zip')
    gtfs = r_extract_gtfs(zip_file)

    # create transfer table
    gtfs = r_gtfs_transfer_table(
        gtfs,
        d_limit=200,
        min_transfer_time=300)
    # convert gtfs data in routable format
    gtfs = r_gtfs_timetable(gtfs, day=weekday)

    return gtfs


# insert arguments and convert to R request format, return args as list
# {args} start: str, end: str, time: int
# {returns} list of args to be processed by R gtfsrouter
def format_args(start, end, time):
    args = ['start', 'end', 'time']

    def args_parse(string):
        arg = r_eval(r_parse(text=string))
        return arg

    args[0] = args_parse(f'from="{start}"')
    args[1] = args_parse(f'to="{end}"')
    args[2] = args_parse(f'start_time={time * 3600}')

    return args


# convert R DataFrames to pandas DataFrames
# {args} r_dataframe: R dataframe
# {returns} (pandas) dataframe
def r_to_pandas_df(r_dataframe):
    with (ro.default_converter + pandas2ri.converter).context():
        return ro.conversion.get_conversion().rpy2py(r_dataframe)


# get train routes from one point to another, return list of pandas dataframes
# {args} gtfs_data: str or gtfs feed, start_df: df of stations, end: [df of stations], time: int, weekday: str
# {returns} list of df of routes
def train_route(gtfs_data, start, end_df, time, weekday=None):
    if isinstance(gtfs_data, str):
        if weekday is None:
            raise Exception('Give weekday for gtfs formatting')
        gtfs = format_gtfs(gtfs_data, weekday)
    else:
        gtfs = gtfs_data
    stops = end_df['stop_name']  # stops: pandas series

    # calculate routes from each close station, if no route possible write None
    def get_route(row):
        args = format_args(start, row, time)
        try:
            route = r_gtfs_route(
                gtfs,
                args[0],
                args[1],
                args[2]
            )
            if isinstance(route, ro.DataFrame) or isinstance(route, ro.vectors.DataFrame):
                return r_to_pandas_df(route)
            else:
                return None
        except:
            return None

    return [get_route(stop) for stop in stops]


# get number of mode changes during route
# {args} route_df: df
# {returns} int
def get_change_count(route_df):
    # compare route_name values to the previous value, count changes
    # subtract one, since the initial entry is counted as a change
    return (route_df['route_name'] != route_df['route_name'].shift()).sum() - 1


# get fastest route from one start point to one cinema
# {args} gtfs_zip: str, gtfs_df: df, start: df, start_point: Point, start_name: str, poi_list: [df], time: int,
# weekday: str, date: str
# {returns} dataframe
def get_fastest_route(gtfs_zip, gtfs_df, start, start_point, start_name, poi_list, time, weekday, date):
    gtfs = None
    route_files_path = path.join(RESULTS_PATH, 'routes', gtfs_zip.rsplit('_')[0])
    not_possible = load(path.join(RESULTS_PATH, 'routes_not_possible.npy'))
    if path.isfile(path.join(RESULTS_PATH, 'routes_not_fast.npy')):
        not_fastest = load(path.join(RESULTS_PATH, 'routes_not_fast.npy'))
    else:
        not_fastest = []
    start_stops = start['stop_name']

    total_routes = []
    total_durations = []
    walks_to = []
    walks_from = []
    total_changes = []
    names = []
    # loop over each poi
    for pid, poi in enumerate(poi_list['stations']):
        cinema_name = poi_list['cinema_name'][pid]
        cinema_location = poi_list['cinema_location'][pid]
        print(f'cinema: {cinema_name}')

        chosen_route = DataFrame()
        dur_default = Timedelta('1 day')
        fastest_dur = dur_default
        walk_to = None
        walk_from = None
        start_stop = ''
        write_to_file = True
        # loop over closest stations of poi, return only the fastest
        for rid, row in enumerate(start_stops):
            invalid = '<>:"/\|?* '
            stop_name = ''.join(char for char in row if char not in invalid)

            query_params = f'{cinema_name}_{start_name}_{stop_name}_{time}'
            route_params = f'{cinema_name}_{stop_name}_{time}'
            route_filename = path.join(route_files_path, f'{route_params}.csv')
            # check if same start (row) has been calculated to cinema before and continue if it has
            if path.isfile(route_filename):
                chosen_route = read_csv(route_filename)
                dur = get_route_duration(chosen_route, only_one=True)
                walk = get_walk_to_station(chosen_route, start_point, cinema_location, gtfs_df)
                fastest_dur = timedelta_addition(dur, walk)
                walk_to = walk[0]
                walk_from = walk[1]
                start_stop = stop_name
                write_to_file = False
                print(f'read route from {row} from file')
                continue
            elif route_params in not_possible or query_params in not_fastest:
                continue
            else:
                if gtfs is None:
                    gtfs = format_gtfs(gtfs_zip, weekday)
                route_opt = train_route(gtfs, row, poi, time)

                # if all routes to this POI's stop failed go to next stop
                if all([route is None for route in route_opt]):
                    print(f'no route possible from {row}')
                    not_possible = np_append(not_possible, [route_params])
                    continue
                print(f'got routes from {row}')

                dur_df = get_route_duration(route_opt, date, False)
                dur_df['walk'] = [get_walk_to_station(route, start_point, cinema_location, gtfs_df) for route in route_opt]
                dur_df['total_duration'] = dur_df.apply(
                    lambda dur_row: timedelta_addition(dur_row['duration'], dur_row['walk']), axis=1)

            total = list(filter(lambda item: isinstance(item, Timedelta), dur_df['total_duration']))

            if all([t is None for t in total]):
                print(f'no route possible to {row}')
                continue
            else:
                min_total = min(total)

                if fastest_dur > min_total:
                    chosen_route = route_opt[dur_df[dur_df['total_duration'] == min_total]['route_id'].values[0]]
                    fastest_dur = min_total
                    fastest_walk = dur_df[dur_df['total_duration'] == min_total]['walk'].values[0]
                    walk_to = fastest_walk[0]
                    walk_from = fastest_walk[1]
                    start_stop = stop_name
                else:
                    not_fastest = np_append(not_fastest, [query_params])
                    continue

        if fastest_dur == dur_default:
            total_routes.append('no routes possible to this cinema')
            total_durations.append(None)
            walks_to.append(None)
            walks_from.append(None)
            total_changes.append(None)
        else:
            chosen_route_filename = f'{route_params}.csv'
            total_routes.append(chosen_route_filename)
            total_durations.append(fastest_dur)
            walks_to.append(walk_to)
            walks_from.append(walk_from)
            total_changes.append(get_change_count(chosen_route))

            if write_to_file:
                chosen_route.to_csv(path.join(route_files_path, chosen_route_filename))
                print('route written!')

        names.append(cinema_name)

    if len(not_possible) != 0:
        save(path.join(RESULTS_PATH, 'routes_not_possible'), not_possible, False)
    if len(not_fastest) != 0:
        save(path.join(RESULTS_PATH, 'routes_not_fast'), not_fastest, False)

    return DataFrame(
        {'cinema_name': names, f'{time}_total_route': total_routes, f'{time}_total_duration': total_durations,
         f'{time}_walk_to': walks_to, f'{time}_walk_from': walks_from, f'{time}_total_changes': total_changes})