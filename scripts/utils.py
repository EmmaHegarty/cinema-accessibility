from os import path
from geopandas import read_file


# read shapefile of Germany at given administration level { GEM, KRS, LAN, LI, RBZ, STA, VWG }
# {args} level: str, in_parent_folder: boolean
# {returns} geodataframe
def germany_admin(level):
    shp_path = path.join('data', 'administrative_geographic_data')

    geom = read_file(path.join(shp_path, f'VG5000_{level}_wLAN.shp'))
    return geom[['GEN', 'BEZ', 'LAN', 'geometry']]
