from os import path
from geopandas import read_file
from shapely.ops import transform
from pyproj import CRS, Transformer


# read shapefile of Germany at given administration level { GEM, KRS, LAN, LI, RBZ, STA, VWG }
# {args} level: str, in_parent_folder: boolean
# {returns} geodataframe
def germany_admin(level):
    shp_path = path.join('data', 'administrative_geographic_data')

    geom = read_file(path.join(shp_path, f'VG5000_{level}_wLAN.shp'))
    return geom[['GEN', 'BEZ', 'LAN', 'geometry']]


# {args} geometries: Series or single geometry, current_epsg: int, goal_epsg: int, single_geom: boolean
# {returns} Series or single geometry
def transform_crs(geometries, current_epsg=25832, goal_epsg=4326, single_geom=False):
    og_crs = CRS(f'EPSG:{current_epsg}')
    wgs84 = CRS(f'EPSG:{goal_epsg}')
    project = Transformer.from_crs(og_crs, wgs84, always_xy=True).transform

    if single_geom:
        return transform(project, geometries)
    else:
        return geometries.apply(lambda geo: transform(project, geo))
