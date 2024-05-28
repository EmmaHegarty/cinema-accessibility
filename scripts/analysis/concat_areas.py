from os import path
from pandas import read_csv, DataFrame, concat
from geopandas import read_file

from scripts.constants import RESULTS_PATH, SELECTED, SELECTED_VALID, LVL_DUMMY


# concatenate the resulting dataframe for all selected areas
# {args} prefix: str, path_end: str, times: [int]
# {returns} None, writes new file
def make_big_df(times, prefix='analysis', path_end='15-18-21_Sat_104'):
    dfs = []
    for level in ['top', 'mid', 'base']:
        inkar = read_csv(path.join('data', 'inkar', f'cinema-population_{level}.csv'))
        for area in SELECTED[level]:
            df = read_csv(path.join(RESULTS_PATH, 'analysis', f'{prefix}_{area}_{path_end}.csv'))
            if 'cinema_name' in df.columns.values and 'osm_cinemas' not in df.columns.values:
                osm_cinemas = len(df['cinema_name'].unique())
                df['osm_cinemas'] = osm_cinemas

            if 'average changes' not in df.columns.values:
                df['average changes'] = df.apply(
                    lambda row: sum([row[f'{t}_total_changes'] for t in times]) / len(times), axis=1)

            df['area average changes'] = df['average changes'].mean()

            # add column denominating area's centrality level with string and with a dummy variable
            if 'level' not in df.columns.values:
                df['level'] = level
                df['level_dummy'] = LVL_DUMMY[level]

            if 'Kinos' not in df.columns.values:
                print('join with pop file')
                gdf = read_file(
                    path.join(RESULTS_PATH, 'geo_data', 'manually_edited', f'analysis_{area}_{path_end}_pop.gpkg'))
                df = df[df.columns.values]

                irow = inkar[inkar['Raumeinheit'] == area]
                variables = [irow[i].values[0] for i in ['Kinos', 'Bevölkerung', 'Einwohnerdichte',
                                                         'Siedlungs- und Verkehrsfläche', 'ÖV-Abfahrten',
                                                         'ÖV-Haltestellen']]
                rows = ['cinemas', 'population aggr', 'population density', 'built-up area', 'transit departures',
                        'transit stops']
                for rid, r in enumerate(rows):
                    df[r] = variables[rid]

            if 'example_for' in df.columns.values:
                print('renaming...')
                df.rename(columns={'example_for': 'area'}, inplace=True)

            # in case columns were added, save updated dataframe to file
            df.iloc[:, 1::].to_csv(path.join(RESULTS_PATH, 'analysis', f'{prefix}_{area}_{path_end}.csv'))

            dfs.append(df.iloc[:, 1::])

    concat(dfs).to_csv(path.join(RESULTS_PATH, 'analysis', f'all_{prefix}_{path_end}.csv'))


# aggregate results for each area
# {args} prefix: str, path_end: str, times: [int]
# {returns} None, writes new file
def make_areas_df(only_valid=False, path_end='15-18-21_Sat_104'):
    selected = SELECTED_VALID if only_valid else SELECTED
    dfs = []
    for level in ['top', 'mid', 'base']:
        rows = []
        inkar = read_csv(path.join('data', 'inkar', f'cinema-population_{level}.csv'))
        for area in selected[level]:
            df = read_csv(path.join(RESULTS_PATH, 'analysis', f'variables_{area}_{path_end}.csv'))
            irow = inkar[inkar['Raumeinheit'] == area]

            arr = [area]
            arr.extend(df.iloc[1][1:])
            arr.extend([irow[i].values[0] for i in ['Kinos', 'Bevölkerung', 'Einwohnerdichte',
                                                    'Siedlungs- und Verkehrsfläche', 'ÖV-Abfahrten',
                                                    'ÖV-Haltestellen']])
            rows.append(arr)
        df = DataFrame(rows, columns=['area', 'time', 'average speed', 'average duration', 'average transit time',
                                      'average walk time', 'average walk share', 'walk share under 40%',
                                      'average amount of changes', 'max changes', 'time difference to car',
                                      'transit is reasonable', 'out of', 'cinemas', 'population aggr',
                                      'population density', 'built-up area', 'transit departures', 'transit stops'])
        df['level'] = level
        dfs.append(df)

    filename = f'all_variables_{path_end}_valid.csv' if only_valid else f'all_variables_{path_end}.csv'
    concat(dfs).to_csv(path.join(RESULTS_PATH, 'analysis', filename))


if __name__ == "__main__":
    time = [15, 18, 21]
    make_big_df(time, 'analysis')
    make_big_df(time, 'starts_variables')
    make_areas_df(True)
