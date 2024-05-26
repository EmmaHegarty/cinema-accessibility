from os import path
from shapely import wkt
from pandas import read_csv, DataFrame, concat
from geopandas import read_file, GeoDataFrame

from scripts.constants import RESULTS_PATH, SELECTED
from scripts.analysis.variables import (get_avg_time, get_speed, get_car_compare, get_transit_time, get_walk_percent,
                                        get_avg_changes, get_walk_time, get_max_changes, get_fastest_mode,
                                        get_valid_entries, get_majority_mode, get_min_max_cinema)


# calculate derived variables and write them into new columns
# {args} df: df, times: [int], filename: str
# {returns} None, writes new file
def write_new_columns(df, times, filename=None):
    df.rename(columns={'example_for': 'area'}, inplace=True)
    df['average duration'] = get_avg_time(df, times)
    df['average speed'] = get_speed(df, times)
    df['average duration difference to car'] = get_car_compare(df, times)
    for t in times:
        df[f'{t}_fastest_mode'] = df.apply(
            lambda row: 'transit' if row['foot_duration'] > row[f'{t}_total_duration'] else 'foot', axis=1)
        df[f'{t}_trip_duration'] = df.apply(
            lambda row: row[f'{t}_total_duration'] if row['foot_duration'] > row[f'{t}_total_duration'] else row[
                'foot_duration'], axis=1)
        df[f'{t}_fastest_overall_mode'] = df.apply(
            lambda row: row[f'{t}_fastest_mode'] if row['car_duration'] > row[f'{t}_total_duration'] else 'car', axis=1)
        df[f'{t}_transit_dur'] = get_transit_time(df, t)
        df[f'{t}_walk_share'] = get_walk_percent(df, t, 'column')
    df['average transit duration'] = df.apply(lambda row: sum([row[f'{t2}_transit_dur'] for t2 in times]), axis=1)
    df['average walk share'] = df.apply(lambda row: sum([row[f'{t2}_walk_share'] for t2 in times]), axis=1)
    df['average changes'] = [get_avg_changes(df, t) for t in times]

    if filename is not None:
        df.loc[:, 'cinema_name'::].to_csv(path.join(RESULTS_PATH, 'analysis', f'analysis_{filename}.csv'))
    else:
        return df


# calculate derived variables and write them into new columns
# {args} df: df, times: [int], filename: str
# {returns} None, writes new file
def write_point_layer(df, times, filename, count):
    gdf = read_file(path.join(RESULTS_PATH, 'geo_data', f'{filename}.gpkg'))

    cinema_size = int(len(gdf) / count)

    wanted_cols = [col for col in gdf.columns if
                   'duration' in col or 'walk' in col or 'changes' in col or 'distance' in col]
    new_gdf = DataFrame(columns=wanted_cols)

    points = []
    for g in range(count):
        start = g * cinema_size
        g_df = df[wanted_cols][start:start + cinema_size]

        new_gdf.loc[g] = g_df.apply(lambda col: col.mean())
        points.append(gdf.iloc[start]['geometry'])

    new_gdf.set_axis([col.replace('total', 'average') for col in wanted_cols], axis=1)
    new_gdf['geometry'] = points
    result = GeoDataFrame(new_gdf, geometry='geometry')

    result.to_file(path.join(RESULTS_PATH, 'geo_data', 'analysis', f'analysis_{filename}.gpkg'))


# calculate averages for all routes at every departure time
# {args} df: df, times: [int], filename: str
# {returns} None, writes new file
def get_variables_per_time(df, times, filename):
    time_str_arr = [str(t) for t in times]
    col = ['index'] + time_str_arr

    for t in times:
        df[f'{t}_fastest_mode'] = df.apply(
            lambda row: 'transit' if row['foot_duration'] > row[f'{t}_total_duration'] else 'foot', axis=1)
    new_df = DataFrame({
        'departure times': times,
        'average speed': [get_speed(df, t, True) for t in times],
        'average time': [get_avg_time(df, t) for t in times],
        'average transit time': [get_transit_time(df, t, True) for t in times],
        'average walk time': [get_walk_time(df, t, True) for t in times],
        'average walk share': [get_walk_percent(df, t, 'avg') for t in times],
        'walk share under 40%': [get_walk_percent(df, t, 40) for t in times],
        'average amount of changes': [get_avg_changes(df, t) for t in times],
        'max changes': [get_max_changes(df, t) for t in times],
        'time difference to car': [get_car_compare(df, t, True) for t in times],
        'transit is reasonable': [get_fastest_mode(df, t) for t in times],
        'out of': [get_valid_entries(df, t, True) for t in times]
    })

    new_df.to_csv(path.join(RESULTS_PATH, 'analysis', f'variables_{filename}.csv'))


# calculate averages for all the routes from each start point
# {args} area: df/str, times: [int], filename: str
# {returns} None, writes new file
def get_variables_per_start(times, filename):
    df = read_csv(path.join(RESULTS_PATH, 'analysis', f'analysis_{filename}.csv'))
    starts = df['start_location'].unique()

    def get_variables(s):
        sdf = df[df['start_location'] == s]
        sdf = sdf[sdf.loc[:, 'cinema_name'::].columns]
        cols = [item for item in sdf.columns
                if all(c not in item for c in ['total_route', 'cinema_name', 'area', 'start_location',
                                               'geometry', 'fastest_mode', 'fastest_overall_mode', 'level'])]
        row = [sdf[col].mean() for col in sdf[cols].columns.values]
        row.extend([sdf['area'].iloc[0], s])
        row.extend(get_majority_mode(sdf, t) for t in times)
        row.extend(get_fastest_mode(sdf, t) for t in times)
        row.extend(sum([get_min_max_cinema(sdf, t, 'min') for t in times], []))
        row.extend(sum([get_min_max_cinema(sdf, t, 'max') for t in times], []))
        cols.extend(['area', 'start_location'])
        cols.extend([f'{t} fastest mode' for t in times])
        cols.extend([f'{t} transit is fastest' for t in times])
        cols.extend(sum([[f'{t} min cinema dur', f'{t} most accessible cinema'] for t in times], []))
        cols.extend(sum([[f'{t} max cinema dur', f'{t} least accessible cinema'] for t in times], []))
        return DataFrame([row], columns=cols)

    results = [get_variables(start) for start in starts]
    save_df = concat(results)

    if filename is not None:
        save_df.to_csv(path.join(RESULTS_PATH, 'analysis', f'starts_variables_{filename}.csv'))
        save_df['start_location'] = save_df['start_location'].apply(wkt.loads)
        GeoDataFrame(save_df, geometry='start_location', crs=4326).to_file(
            path.join(RESULTS_PATH, 'geo_data', 'analysis', f'starts_variables_{filename}.gpkg'))
    else:
        return save_df


# calculate all variables and write to new files
# {args} timesdate: str, count: int, level: str
# {returns} None, writes new files
def get_all_variables(timesdate, count, level):
    for area in SELECTED[level]:
        filename = f'{area}_{timesdate}_{count}'
        times = [int(t) for t in timesdate.split('_', 1)[0].split('-')]
        df = read_csv(path.join(RESULTS_PATH, f'{filename}.csv'))

        write_new_columns(df, times, filename)
        write_point_layer(df, times, filename, count)
        get_variables_per_time(df, times, filename)
        get_variables_per_start(times, filename)
        print(f'{area} done!')


if __name__ == "__main__":
    for centrality in ['top', 'mid', 'base']:
        get_all_variables('15-18-21_Sat', 104, centrality)
