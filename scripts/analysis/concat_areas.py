from os import path
from pandas import read_csv, concat
from geopandas import read_file

from scripts.constants import RESULTS_PATH, SELECTED, LVL_DUMMY


# concatenate the resulting dataframe for all selected areas
# {args} prefix: str, path_end: str, times: [int]
# {returns} None, writes new file
def make_big_df(times, prefix='analysis', path_end='15-18-21_Sat_104'):
    dfs = []
    for level in ['top', 'mid', 'base']:
        inkar = read_csv(path.join('data', 'INKAR-files', f'cinema-population_{level}.csv'))
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

            if 'population' not in df.columns.values:
                print('join with population file')
                gdf = read_file(path.join(RESULTS_PATH, 'geo_data', 'analysis', f'{prefix}_{area}_{path_end}_pop.gpkg'))
                df = df[df.columns.values]
                df['population'] = gdf['population']

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

            dfs.append(df.iloc[:, 1::].iloc[:100 * df['osm_cinemas'][0], :])

    concat(dfs).to_csv(path.join(RESULTS_PATH, 'analysis', f'all_{prefix}_{path_end}.csv'))


if __name__ == "__main__":
    time = [15, 18, 21]
    make_big_df(time, 'analysis')
    make_big_df(time, 'starts_variables')
