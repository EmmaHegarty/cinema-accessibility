from os import path, makedirs
from pandas import concat, read_csv
from geopandas import read_file

from scripts.utils import remove_dir
from scripts.constants import RESULTS_PATH, SELECTED
from scripts.get_osm_data import get_random_start, bbox_edge_coords
from scripts.routing.calculate_routes import get_routes


# calculate routes for all start points in an area in batches
# {args} area_name: str, full_gtfs: str, times: [int], batch_count: int, weekday: str, date: str
# {returns} None, writes gpkg and csv file
def batch_route_for_times(area_name, full_gtfs, times, batch_count, weekday, date='20240309'):
    folder = path.join(RESULTS_PATH, f'{area_name}_batch')
    makedirs(folder, exist_ok=True)
    makedirs(path.join(RESULTS_PATH, 'routes', area_name), exist_ok=True)

    start_count = batch_count*10

    # if start points have already been selected read them from file, if not then make selection here
    expected_starts = path.join(RESULTS_PATH, 'geo_data', 'start_points', f'{start_count}_{area_name}.gpkg')
    if path.isfile(expected_starts):
        print(f'reading {start_count} random starts...')
        all_centres = read_file(expected_starts)
    else:
        print(f'getting {start_count} random starts...')
        all_centres = get_random_start(area_name, start_count)
        all_centres.to_file(expected_starts)

    # slice centres into batches of 10 start points
    def slice_start(i):
        from_point = i*10
        return all_centres[from_point:from_point+10]
    centres = [slice_start(i) for i in range(batch_count)]

    # calculate routes for a batch of 10 start points at a time and write filename of batch results to this list
    files = [get_routes(area_name, full_gtfs, times, centres[i], weekday, i, '20240309') for i in range(batch_count)]

    # read each batch results into a list of (geo)dataframes
    gdfs = [read_file(path.join(RESULTS_PATH, f'{area_name}_batch', f'{file}.gpkg')) for file in files]
    dfs = [read_csv(path.join(RESULTS_PATH, f'{area_name}_batch', f'{file}.csv')) for file in files]

    # concatenate the batch results into one file containing all results for the area
    time_str = '-'.join([str(t) for t in times])
    concat(gdfs).to_file(path.join(RESULTS_PATH, 'geo_data', f'{area_name}_{time_str}_{weekday}_{batch_count*10}.gpkg'))
    concat(dfs).to_csv(path.join(RESULTS_PATH, f'{area_name}_{time_str}_{weekday}_{batch_count*10}.csv'))

    # remove batch files once they have been concatenated
    remove_dir(folder)


# concatenate results for randomly selected start points and edge start points
# {args} level: str, timesdate: str
# {returns} None, writes gpkg and csv file
def concat_corners(level, timesdate):
    for area in SELECTED[level]:
        df = read_file(path.join(RESULTS_PATH, f'{area}_{timesdate}_100.csv'))
        df2 = read_file(path.join(RESULTS_PATH, f'{area}_{timesdate}_4.csv'))
        gdf = read_file(path.join(RESULTS_PATH, 'geo_data', f'{area}_{timesdate}_100.gpkg'))
        gdf2 = read_file(path.join(RESULTS_PATH, 'geo_data', f'{area}_{timesdate}_4.gpkg'))

        new_df = concat([df, df2])
        new_gdf = concat([gdf, gdf2])

        new_df.to_csv(path.join(RESULTS_PATH, f'{area}_{timesdate}_104.csv'))
        new_gdf.to_file(path.join(RESULTS_PATH, 'geo_data', f'{area}_{timesdate}_104.gpkg'))

        print(f'{area} concatenated!')


# calculate routes for start points closest to bbox boundaries
# {args} full_gtfs: str, level: str, times: [int], weekday: str, date: str
# {returns} None, writes gpkg and csv file
def add_corners_for_times(area_name, full_gtfs, times, weekday, date='20240309'):
    time_str = '-'.join([str(t) for t in times])

    # if edge points have already been selected read them from file, if not then make selection here
    expected_file = path.join(RESULTS_PATH, 'geo_data', 'start_points', f'{area_name}_closest_to_bbox.gpkg')
    if path.isfile(expected_file):
        centres = read_file(expected_file)
    else:
        print(f'getting bbox coordinates for {area_name}...')
        centres = bbox_edge_coords(area_name)
        centres.to_file(expected_file)

    output_path = path.join(RESULTS_PATH, f'{area_name}_{time_str}_{weekday}_4.csv')
    if not path.isfile(output_path):
        print(f'{output_path} does not exist')
        get_routes(area_name, full_gtfs, times, centres, weekday, 'bbox', '20240309')
    print(f'{area_name} done!')


if __name__ == "__main__":
    for centrality in ['top', 'mid', 'base']:
        gtfs_filename = 'opnv_240218'
        start_times = [15, 18, 21]

        for name in SELECTED[centrality]:
            print(name)
            batch_route_for_times(name, gtfs_filename, start_times, 10, 'Sat')
            add_corners_for_times(name, gtfs_filename, start_times, 'Sat')

        concat_corners(centrality, '15-18-21_Sat')
