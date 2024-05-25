from os import path, walk, remove, rmdir
from zipfile import ZipFile
from datetime import datetime, timedelta
from pandas import read_csv, isna, to_datetime
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


# {args} Polygon
# {returns} string
def bbox_to_string(envelope):
    coords = envelope.exterior.coords

    lat = [round(p[1], 7) for p in coords]
    lon = [round(p[0], 7) for p in coords]

    return ','.join(map(str, [min(lon), min(lat), max(lon), max(lat)]))


# {args} polygon: Polygon, current_crs: int, return_string: boolean
# {returns} string or Polygon
def get_polygon_bbox(polygon, current_crs=25832, return_string=False):
    poly = transform_crs(polygon, current_crs, 4326, True)
    bbox = poly.envelope

    return bbox_to_string(bbox) if return_string else bbox


# {args} folder_path: str, output_zip: str
# {returns} zip archive in folder_path location
def create_zip(folder_path, output_zip):
    with ZipFile(output_zip, 'w') as zipf:
        for root, _, files in walk(folder_path):
            for file in files:
                file_path = path.join(root, file)
                zipf.write(file_path, path.relpath(file_path, folder_path))


# {args} folder_path: str
# {returns} None, deletes directory
def remove_dir(folder_path):
    for root, _, files in walk(folder_path):
        for name in files:
            remove(path.join(root, name))
        rmdir(folder_path)


# convert gtfs time (exceeds 24:00:00) to pandas datetime format
# {args} gtfs_date: string, gtfs_time: string
# {returns} Datetime
def gtfs_time_to_pandas_datetime(gtfs_date, gtfs_time):
    if isna(gtfs_time):
        return None
    else:
        hours, minutes, seconds = map(int, gtfs_time.split(":"))
        date_time = datetime.strptime(gtfs_date, "%Y%m%d") + timedelta(
               hours=hours, minutes=minutes, seconds=seconds)

        return to_datetime(date_time)
