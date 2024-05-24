from os import path
from geopandas import read_file

from scripts.utils import transform_crs
from scripts.constants import INKAR_PATH, RESULTS_PATH
from scripts.get_osm_data import get_cinema


# calculate ratio of population to cinema and write into new columns
# {args} filename: str
# {returns} geodataframe, overwrites given file
def population_per_cinema(filename):
    gdf = read_file(path.join(INKAR_PATH, filename))
    label = 'population'
    column = 'Bevölkerung'

    def get_cinemas(row):
        cinemas_path = path.join(RESULTS_PATH, 'geo_data', 'cinemas', f'{row["GEN"]}_cinemas.gpkg')
        if not path.isfile(cinemas_path):
            cinemas = get_cinema(row['geometry'])
        else:
            cinemas = read_file(cinemas_path)
            print('read cinemas')
        if cinemas is None:
            return None
        else:
            cinemas.to_file(cinemas_path)
            return len(cinemas)

    def per_cinema(row):
        cin = row['OSM_cinemas']
        if cin is None or cin == 0 or row['Kinos'] is None:
            return None
        elif abs(row['cinemas_accuracy']) > 1:
            print(f'OSM {cin} does not match INKAR {row["Kinos"]} for {row["GEN"]}')
            return None
        else:
            print('matched!')
            return row[column]/cin

    gdf['geometry'] = transform_crs(gdf['geometry'], 25832)
    gdf['OSM_cinemas'] = gdf.apply(lambda row: get_cinemas(row), axis=1)
    gdf['cinemas_accuracy'] = gdf.apply(lambda row: row['OSM_cinemas']-row['Kinos'], axis=1)
    gdf[f'{label}_per_cinema'] = gdf.apply(lambda row: per_cinema(row), axis=1)
    print('reprojecting...')
    gdf['geometry'] = transform_crs(gdf['geometry'], 4326, 25832)

    gdf.to_file(path.join(INKAR_PATH, filename))
    print('done!')


if __name__ == "__main__":
    for centrality in ['top', 'mid', 'base']:
        gpkg_file = f'cinema-population_{centrality}.gpkg'

        population_per_cinema(gpkg_file)
