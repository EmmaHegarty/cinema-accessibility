from os import path
from geopandas import read_file

from scripts.constants import INKAR_PATH


# remove regions that contain no cinemas and/or are not classified from a geopackage file
# {args} filename: str, column_name: str, level: str
# return: geodataframe, writes new gpkg file
def inkar_keep_options(filename, column_name, level):
    inkar_gdf = read_file(path.join(INKAR_PATH, filename))

    # remove the municipalities that contain no cinemas from the (classified) inkar file
    inkar_gdf = inkar_gdf[inkar_gdf['OSM_cinemas'].notna()]
    # remove regions that have no classification
    inkar_gdf = inkar_gdf.dropna(subset=column_name)

    inkar_gdf.to_file(path.join(INKAR_PATH, f'{filename.rsplit("_", 1)[0]}_options_{level}.gpkg'))


if __name__ == "__main__":
    for centrality in ['top', 'mid', 'base']:
        gpkg_file = f'cinema-population_{centrality}.gpkg'

        inkar_keep_options(gpkg_file, 'population_per_cinema', centrality)
