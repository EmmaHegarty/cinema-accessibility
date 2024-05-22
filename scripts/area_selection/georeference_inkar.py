from os import path
from pandas import read_csv

from scripts.utils import germany_admin
from scripts.constants import INKAR_PATH


# import and format inkar data, merge with geoinformation from administration polygons
# {args} filename: str
# {returns} N/A, writes new gpkg file
def import_inkar(filename):
    mncp = germany_admin('GEM')
    inkar_df = read_csv(path.join(INKAR_PATH, filename), sep=',', na_filter=False)

    # print any differences in name columns of both datasets, since those rows will not be merged
    # if there are any differences, go back and check the name columns to prevent mistakes
    compare = inkar_df[~inkar_df['Raumeinheit'].isin(mncp['GEN'])]['Raumeinheit']
    print(compare.tolist())

    # convert string data in inkar table to floats
    for column in inkar_df.columns:
        if column not in ['Kennziffer', 'Raumeinheit', 'Aggregat']:
            inkar_df[column] = inkar_df[column].astype(float, errors='ignore')

    # join inkar data and shapefiles of administrative region on name
    gdf = (mncp.merge(inkar_df, left_on='GEN', right_on='Raumeinheit'))
    gdf.to_file(path.join(INKAR_PATH, f'{filename.rsplit(".", 1)[0]}.gpkg'))
    print('imported!')


if __name__ == "__main__":
    for centrality in ['top', 'mid', 'base']:
        csv_file = f'cinema-population_{centrality}.csv'

        import_inkar(csv_file)
