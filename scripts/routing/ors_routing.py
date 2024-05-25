from pandas import Timedelta
from openrouteservice import Client, exceptions
from openrouteservice.directions import directions

local_client = Client(base_url='http://localhost:8082/ors')


# request route, get duration of car/walking trip
# {args} start_point: Point, end_point: Point, profile: string, is_point_obj: boolean
# {returns} Timedelta
def get_ors_duration(start_point, end_point, profile, is_point_obj=True):
    if is_point_obj:
        start = (start_point.x, start_point.y)
        end = (end_point.x, end_point.y)
    else:
        start = start_point
        end = end_point
    coords = (start, end)

    try:
        query = directions(local_client, coords, profile)
        dur = query["routes"][0]["summary"]["duration"]  # in seconds
        return Timedelta(dur, 's')
    except exceptions.ApiError as err:
        print(f'no ors duration routable: {err}')
        return None


# get time it takes to walk from start point to departure station and from arrival station to cinema
# {args} route_df: df, start_point: Point, cinema_location: Point, gtfs_df: df
# {returns} list of Timedeltas
def get_walk_to_station(route_df, start_point, cinema_location, gtfs_df):
    if route_df is None:
        return None

    stops = gtfs_df['stops']

    dep_name = route_df['stop_name'].iloc[0]
    arr_name = route_df['stop_name'].iloc[len(route_df) - 1]
    dep_stop = stops[stops['stop_name'] == dep_name].iloc[0]
    arr_stop = stops[stops['stop_name'] == arr_name].iloc[0]
    dep_point = (dep_stop.stop_lon, dep_stop.stop_lat)
    arr_point = (arr_stop.stop_lon, arr_stop.stop_lat)

    dep_dur = get_ors_duration((start_point.x, start_point.y), dep_point, 'foot-walking', False)
    arr_dur = get_ors_duration(arr_point, (cinema_location.x, cinema_location.y), 'foot-walking', False)

    return [dep_dur, arr_dur]


# {args} start: Point, destinations: dataframe, profile: string
# {returns} list of Timedeltas
def get_all_ors_durations(start, destinations, profile):
    durations = []
    for pid, poi in destinations.iterrows():
        durations.append(get_ors_duration(start, poi['geometry'], profile))

    return durations
