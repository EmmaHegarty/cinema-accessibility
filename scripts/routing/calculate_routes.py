from os import path
from pandas import concat, Timedelta
from geopandas import GeoSeries, GeoDataFrame, read_file

from scripts.utils import germany_admin, centroid_from_name, zip_to_df, calc_distance
from scripts.constants import RESULTS_PATH, EXTRACTED_CHANGED, EXTRACTED_NAME
from scripts.get_osm_data import get_cinema, get_all_stations, get_stations
from scripts.routing.gtfs_routing import get_fastest_route
from scripts.routing.ors_routing import get_all_ors_durations


# get routes for all start points in one area for given start times
# {args} area_name: str, filtered_filename: str, cinemas: df, times: [int], centres: df, start_count: int,
# weekday: str, date: str
# {returns} dataframe
def route_in_area(area_name, filtered_filename, cinemas, times, start_points, start_count, weekday='Sat', date='20240309'):
    # get centroid of area as proxy to calculate distance of start points to centre
    centroid = centroid_from_name(area_name)
    gtfs_df = zip_to_df(path.join('gtfs_files', f'{filtered_filename}.zip'))

    # get list of DataFrames of closest stations (one per POI)
    print(f'getting end stations...')
    end = get_all_stations(gtfs_df, cinemas, 10)

    def get_df(cid, c):
        print(f'start: {cid}')
        start_point = c['geometry']
        start_name = c['name']

        # get DataFrame of closest stations to centre, columns: 'stop_name', ..., 'distance'
        print(f'getting start stations...')
        start = get_stations(gtfs_df, start_point, 10)

        # calculate route for first start time and then add route for other start times
        print(f'getting train routes for {area_name}...')
        df = get_fastest_route(filtered_filename, gtfs_df, start, start_point, start_name, end, times[0], weekday, date)

        for tid, t in enumerate(times):
            if tid == 0:
                continue
            else:
                new_df = get_fastest_route(filtered_filename, gtfs_df, start, start_point, start_name, end, t, weekday, date)
                df = df.merge(new_df, how='left', on='cinema_name')

        print(f'getting car durations for {area_name}...')
        df['car_duration'] = get_all_ors_durations(start_point, cinemas, 'driving-car')
        df['foot_duration'] = get_all_ors_durations(start_point, cinemas, 'foot-walking')
        df['example_for'] = area_name
        df['start_location'] = start_point
        df['start_location'] = GeoSeries(df['start_location'])
        df['distance_start_centroid'] = calc_distance(start_point, centroid, True)
        cartesian_dist = calc_distance(start_point, cinemas)
        df['distance_start_cinema'] = df.apply(lambda row: cartesian_dist[1][cartesian_dist[0].index(row['cinema_name'])], axis=1)

        return df

    dfs = [get_df(cid, c) for cid, c in start_points.iterrows()]

    if isinstance(start_count, int) and start_count == 1:
        print('done!')
        return dfs[0]
    else:
        print('done!')
        return concat(dfs)


# check all necessary data is available for routing, get routes, format and save resulting dataframe
# {args} area_name: string, full_gtfs: string, times: [int], start_count: int, weekday: str, date: str, batch: int/str
# {returns} saves dfs to csv and gpkg
def get_routes(area_name, full_gtfs, times, start_count, weekday, batch, date='20240309'):
    areas = germany_admin('GEM')
    in_area = areas[areas['GEN'] == area_name]

    # check if gtfs subset for area exists
    if in_area['GEN'].values[0] not in EXTRACTED_NAME and in_area['GEN'].values[0] not in EXTRACTED_CHANGED:
        raise Exception(f'there is no extracted GTFS feed for {in_area["GEN"].values[0]}')
    elif in_area['GEN'].values[0] in EXTRACTED_CHANGED:
        extracted_name = EXTRACTED_NAME[EXTRACTED_CHANGED[in_area['GEN'].values[0]]]
    else:
        extracted_name = in_area['GEN'].values[0]
    gtfs_filename = f'{extracted_name}_{full_gtfs}_filtered'

    # if cinemas have already been formatted and saved then read from file, if not get them here
    cinemas_path = path.join(RESULTS_PATH, 'geo_data', 'cinemas', f'{area_name}_cinemas.gpkg')
    if not path.isfile(cinemas_path):
        print('getting cinemas for areas...')
        cinemas = get_cinema(in_area)[0]
        cinemas.to_file(cinemas_path)
    else:
        cinemas = read_file(cinemas_path)

    # check if request came from batch routing function or edges routing function
    if isinstance(batch, int):
        centres = start_count
        start_count = len(centres)
        print(f'batch {batch}')
    elif batch == 'bbox':
        centres = start_count
        start_count = 4
        print('routing bbox corners')

    # get routing results
    routes = route_in_area(in_area['GEN'].values[0], gtfs_filename, cinemas, times, centres, start_count, weekday, date)

    # convert timedelta objects in dataframe to seconds
    for column in [col for col in routes.columns if 'duration' in col or 'walk' in col]:
        routes[column] = routes[column].apply(
            lambda row: row.total_seconds() if isinstance(row, Timedelta) else row)

    gdf = GeoDataFrame(routes, geometry='start_location')

    # save dataframe to batch folder or directly to results folder
    time_str = '-'.join([str(t) for t in times])
    if isinstance(batch, int):
        folder = path.join(RESULTS_PATH, f'{area_name}_batch')
        gdf.to_file(path.join(folder, f'{area_name}_{time_str}_{weekday}_{batch}.gpkg'))
        routes.to_csv(path.join(folder, f'{area_name}_{time_str}_{weekday}_{batch}.csv'))
        return f'{area_name}_{time_str}_{weekday}_{batch}'
    else:
        gdf.to_file(path.join(RESULTS_PATH, 'geo_data', f'{area_name}_{time_str}_{weekday}_{start_count}.gpkg'))
        routes.to_csv(path.join(RESULTS_PATH, f'{area_name}_{time_str}_{weekday}_{start_count}.csv'))
