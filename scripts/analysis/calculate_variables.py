from os import path
from pandas import read_csv, DataFrame
from geopandas import read_file, GeoDataFrame

from scripts.constants import RESULTS_PATH, SELECTED
from scripts.analysis.variables import (get_avg_time, get_speed, get_car_compare, get_transit_time, get_walk_percent,
                                        get_avg_changes)


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
        print(f'{area} done!')


if __name__ == "__main__":
    for centrality in ['top', 'mid', 'base']:
        get_all_variables('15-18-21_Sat', 104, centrality)
