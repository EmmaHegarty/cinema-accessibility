from os import path
from shapely import wkt
from pandas import read_csv, DataFrame, concat, unique
from geopandas import read_file, GeoDataFrame

from scripts.constants import RESULTS_PATH, SELECTED, LEISURE_TIME
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
    df['average walk share'] = df.apply(lambda row: sum([row[f'{t2}_walk_share'] / 3 for t2 in times]), axis=1)
    df['average changes'] = get_avg_changes(df, times)

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
# {args} times: [int], filename: str
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


# calculates cumulative opportunity measures for different time limits
# {args} area: str, times: [int] or int, prefix: str, path_end: str,
# {returns} None, writes new file
def within_time_limit(area, time, prefix='analysis', path_end='15-18-21_Sat_104'):
    df = read_csv(path.join(RESULTS_PATH, 'analysis', f'{prefix}_{area}_{path_end}.csv'))

    # choose walk duration if walking is faster than transit, else choose transit duration
    if isinstance(time, list):
        for t in time:
            df[f'{t}_chosen_route'] = df.apply(
                lambda row: None if row[f'{t}_total_duration'] is None else row[f'{t}_total_duration']
                if row[f'{t}_fastest_mode'] == 'transit' else row['foot_duration'], axis=1)
        df['average_chosen_route'] = df.apply(lambda row: sum([row[f'{t2}_chosen_route'] for t2 in time]) / len(time),
                                              axis=1)
    else:
        df[f'{time}_chosen_route'] = df.apply(
            lambda row: None if row[f'{time}_total_duration'] is None else row[f'{time}_total_duration']
            if row[f'{time}_fastest_mode'] == 'transit' else row['foot_duration'], axis=1)
        time = [time]

    first_row = DataFrame({'group': None, 'average travel time': None, 'average visit time': None,
                           'average likely': 'yes', 'average possible': 'yes'}, index=[0])
    for t in time:
        new_cols = DataFrame({f'{t} travel time': None, f'{t} visit time': None,
                              f'{t} mode': 'transit', f'{t} likely': 'yes', f'{t} possible': 'yes'}, index=[0])
        first_row = concat([first_row, new_cols], axis=1)

    dfs = [first_row]
    for group in LEISURE_TIME['typical']:
        data = {'group': group}
        for t in time:
            # add times for trip there, 90 minutes film and trip back
            df[f'{t}_visit_time'] = df.apply(
                lambda row: row[f'{t}_chosen_route'] * 2 + 5400, axis=1)
            # yes if 'social life and entertainment' threshold allows for visit time
            df[f'{t}_likely_{group}'] = df.apply(
                lambda row: 'no data' if row[f'{t}_chosen_route'] is None else 'yes'
                if row[f'{t}_visit_time'] < LEISURE_TIME['typical'][group] else 'no', axis=1)
            # yes if total leisure time threshold allows for visit time
            df[f'{t}_possible_{group}'] = df.apply(
                lambda row: 'no data' if row[f'{t}_chosen_route'] is None else 'yes'
                if row[f'{t}_visit_time'] < LEISURE_TIME['available'][group] else 'no', axis=1)

            data.update({f'{t} travel time': df[f'{t}_chosen_route'], f'{t} visit time': df[f'{t}_visit_time'],
                         f'{t} mode': df[f'{t}_fastest_mode'], f'{t} likely': df[f'{t}_likely_{group}'],
                         f'{t} possible': df[f'{t}_possible_{group}']})

        # also calculate average of all departure times for each route if more than one time given
        if isinstance(time, list):
            df['average_visit_time'] = df.apply(
                lambda row: row['average_chosen_route'] * 2 + 5400, axis=1)
            df[f'average_likely_{group}'] = df.apply(
                lambda row: 'no data' if row['average_chosen_route'] is None else 'yes'
                if row['average_visit_time'] < LEISURE_TIME['typical'][group] else 'no', axis=1)
            df[f'average_possible_{group}'] = df.apply(
                lambda row: 'no data' if row['average_chosen_route'] is None else 'yes'
                if row['average_visit_time'] < LEISURE_TIME['available'][group] else 'no', axis=1)
            data.update({'average travel time': df['average_chosen_route'],
                         'average visit time': df['average_visit_time'],
                         'average likely': df[f'average_likely_{group}'],
                         'average possible': df[f'average_possible_{group}']})

        dfs.append(DataFrame(data))

    df.loc[:, 'cinema_name'::].to_csv(path.join(RESULTS_PATH, 'groups', f'{prefix}_{area}_{path_end}_groups.csv'))
    concat(dfs).to_csv(path.join(RESULTS_PATH, 'groups', f'groups_{area}_{time}.csv'))


# calculates cumulative opportunity measures for different time limits
# {args} area: str, times: [int], time: str or int, prefix: str, path_end: str,
# {returns} None, writes new file
def time_limit_ratio(area, times, time='average', prefix='analysis', path_end='15-18-21_Sat_104'):
    df = read_csv(path.join(RESULTS_PATH, 'groups', f'{prefix}_{area}_{path_end}_groups.csv'))
    starts = df['start_location'].unique()
    cinemas = unique(df['cinema_name'])

    def get_indices(s):
        sdf = df[df['start_location'] == s]
        if len(sdf) != len(cinemas):
            sdfs = [sdf.iloc[:len(cinemas), :], sdf.iloc[len(cinemas):, :]]
        else:
            sdfs = [sdf]

        data = []
        for split_df in sdfs:
            split_df = split_df[split_df.loc[:, 'cinema_name'::].columns]
            cols = [item for item in split_df.columns
                    if any(c in item for c in ['likely', 'possible'])]
            row = [len(split_df), s]
            names = ['osm_cinemas', 'start_location']
            row.extend(sum(split_df[col].str.count('yes')) for col in cols)
            names.extend(cols)
            row.extend(get_fastest_mode(split_df, t) for t in times)
            names.extend([f'{t} transit is reasonable' for t in times])
            row.extend(get_fastest_mode(split_df, t, 'fastest_overall_mode') for t in times)
            names.extend([f'{t} transit is more reasonable than car' for t in times])

            data.append(DataFrame([row], columns=names))

        return concat(data)

    results = [get_indices(start) for start in starts]
    res = concat(results)
    res.to_csv(path.join(RESULTS_PATH, 'groups', f'starts_groups_{area}_{path_end}.csv'))
    res['geometry'] = res['start_location'].apply(wkt.loads)
    GeoDataFrame(res).to_file(path.join(RESULTS_PATH, 'geo_data', 'groups', f'starts_groups_{area}_{path_end}.gpkg'))

    dfs = [DataFrame(
        {'group': [None, None], 'osm_cinemas': [None, None], 'likely count': [0, 5], 'possible count': [0, 5]})]
    for group in LEISURE_TIME['typical']:
        dfs.append(DataFrame({'group': group, 'osm_cinemas': res['osm_cinemas'].iloc[0],
                              'likely count': res[f'{time}_likely_{group}'],
                              'possible count': res[f'{time}_possible_{group}']}))

    concat(dfs).to_csv(path.join(RESULTS_PATH, 'groups', f'groups_cum_{area}_{time}.csv'))


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
        within_time_limit(area, times)
        time_limit_ratio(area, times)
        print(f'{area} done!')


# move results for different departure times from columns into adjoining rows
# {args} area: str, times: [int], path_end: str
# {returns} None, writes new file
def get_analysis_per_time(area, times=[15, 18, 21], path_end='15-18-21_Sat_104'):
    df = read_csv(path.join(RESULTS_PATH, 'analysis', f'analysis_{area}_{path_end}.csv'))

    dfs = []
    for t in times:
        df[f'{t}_fastest_mode'] = df.apply(lambda row: 'transit' if row['foot_duration'] > row[f'{t}_total_duration'] else 'foot', axis=1)

        if 'population' not in df.columns.values:
            print('join with pop file')
            gdf = read_file(path.join(RESULTS_PATH, 'geo_data', 'manually_edited', f'analysis_{area}_{path_end}_pop.gpkg'))
            df = df[df.columns.values]
            df['population'] = gdf['population']

        new_df = DataFrame({
            'total duration': df[f'{t}_total_duration'],
            'total changes': df[f'{t}_total_changes'],
            'speed': df[f'{t}_speed'],
            'fastest mode': df[f'{t}_fastest_mode'],
            'fastest overall mode': df[f'{t}_fastest_overall_mode'],
            'walk share': df[f'{t}_walk_share'],
            'population': df['population']
        })
        new_df['departure time'] = t
        dfs.append(new_df)

    concat(dfs).to_csv(path.join(RESULTS_PATH, 'analysis', f'time_analysis_{area}_{path_end}.csv'))


if __name__ == "__main__":
    for centrality in ['top', 'mid', 'base']:
        get_all_variables('15-18-21_Sat', 104, centrality)

        for name in SELECTED[centrality]:
            get_analysis_per_time(name)
