from os import path
from pandas import concat
from geopandas import read_file

from scripts.utils import get_polygon_bbox
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


# return a specified number of random areas that have the specified classification
def choose_random_area(gdf, selected_class, number):
    subset = gdf[gdf['population/cinema class'] == selected_class]
    return subset.sample(number)


# get a specified number of random regions from a geodataframe for each classification
# {args} filename: str, level: str, classification: int, number_per_class: int
# {returns} geodataframe, writes new gpkg file to new folder
def choose_regions(filename, level, selected_class, number_per_class):
    options_inkar = read_file(path.join(INKAR_PATH, filename))

    to_reject = []
    responses = []
    # manually confirm the region has satisfactory osm data quality, continue until given number of areas is selected
    while len(responses) < number_per_class:
        res = choose_random_area(options_inkar, selected_class, 1)

        if res['GEN'].values[0] in to_reject:
            continue
        else:
            print(res['GEN'].values[0])
            # print bbox of randomly selected area, copy to clipboard to check data quality in that extent
            print(get_polygon_bbox(res['geometry'].iloc[0], 25832, True))
            user_input = input('Is the OSM data quality for this region satisfactory? (yes/no): ')

            # if data quality satisfactory and input is yes, append area gdf to responses
            # also append to rejection list, so it will not be offered for selection twice
            if user_input.lower() == 'yes':
                responses.append(res)
                to_reject.append(res['GEN'].values[0])
            # if data quality not satisfactory and input is no, append area name to rejection list
            elif user_input.lower() == 'no':
                to_reject.append(res['GEN'].values[0])
            else:
                print('Invalid input. Please enter "yes" or "no".')

    concat(responses).to_file(path.join(INKAR_PATH, f'selected_{level}_{selected_class}.gpkg'))


if __name__ == "__main__":
    for centrality in ['top', 'mid', 'base']:
        gpkg_file = f'cinema-population_{centrality}.gpkg'

        inkar_keep_options(gpkg_file, 'population_per_cinema', centrality)

        # TODO: choose representative category from the Jenks Natural Breaks classification
        median_class = {'top': 3, 'mid': 2, 'base': 3}

        options_file = f'cinema-population_options_{centrality}.gpkg'
        choose_regions(options_file, centrality, [median_class[centrality]], 4)
