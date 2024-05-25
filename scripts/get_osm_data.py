from os import path
from shapely import geometry, Point, LineString
from osmnx import features
from pandas import notna
from geopandas import read_file, GeoDataFrame

from scripts.utils import transform_crs, germany_admin
from scripts.constants import RESULTS_PATH


# request cinemas
# {args} area: shapely polygon
# {returns} dataframe containing cinemas
def get_cinema(area):
    tags = {'amenity': 'cinema'}
    try:
        cinemas = features.features_from_polygon(area, tags)
        if cinemas.empty:
            raise ValueError('Dataframe is empty')

        for rid, row in cinemas.iterrows():
            if type(row['geometry']) is geometry.polygon.Polygon:
                pg = transform_crs(row['geometry'], 4326, 25832, True)
                pt = pg.centroid
                cinemas.at[rid, 'geometry'] = transform_crs(pt, 25832, 4326, True)

        if 'name' in cinemas.columns:
            if 'amenity' in cinemas.columns:
                return cinemas[['geometry', 'name', 'amenity']]
            else:
                return cinemas[['geometry', 'name']]
        else:
            if 'amenity' in cinemas.columns:
                return cinemas[['geometry', 'amenity']]
            else:
                return cinemas[['geometry']]
    except ValueError:
        return None


# get random selection of features as list
# {args} feat: series or list, number: int, seed: int
# {returns} list of pois
def random_features(feat, number, seed=None):
    if len(feat) > number:
        rows = feat.sample(number, seed)
        return rows
    else:
        raise Exception('too few features in given dataframe')


# get a given amount of randomly selected residential features as point objects
# {args} area_name: string, start_count: int
# {returns} geodataframe
def get_random_start(area_name, start_count):
    districts = germany_admin('GEM')
    # get polygon of area
    area = districts[districts['GEN'] == area_name]

    # there are two seefelds, the second one is the area studied here
    if area_name == 'Seefeld':
        area_polygon = area.geometry.iloc[1]
    else:
        area_polygon = area.geometry.iloc[0]

    area_pg_wgs84 = transform_crs(area_polygon, 25832, 4326, True)

    tags = {
        'building': ['apartments', 'dormitory', 'residential']
    }

    # get GeoDataFrame of features
    filepath = path.join(RESULTS_PATH, 'geo_data', 'residential', f'residential_{area_name}.gpkg')
    if path.isfile(filepath):
        start_gdf = read_file(filepath)
    else:
        start_gdf = features.features_from_polygon(area_pg_wgs84, tags)
        if 'name' in start_gdf.columns:
            residential = start_gdf[['name', 'geometry']]
        else:
            residential = start_gdf[['geometry']]
        residential.to_file(filepath)

    # save Point features and centroids of Polygon features
    geometries = start_gdf['geometry']
    for rid, row in enumerate(geometries):
        if type(row) is geometry.point.Point:
            continue
        elif type(row) is geometry.polygon.Polygon:
            geometries.iloc[rid] = row.centroid
        else:
            geometries.iloc[rid] = None

    chosen_starts = random_features(geometries, start_count)

    start_points = []
    names = []
    for start in chosen_starts:
        obj = start_gdf[geometries == start]

        if 'name' in start_gdf.columns and notna(obj['name'].iloc[0]):
            name = obj['name'].iloc[0]
        else:
            name = f'osmid_{obj.index[0]}'
        start_points.append(start)
        names.append(name)

    return GeoDataFrame({'name': names, 'geometry': start_points}, geometry='geometry')


# get residential features closest to bbox boundaries as point objects
# {args} area_name: string
# {returns} geodataframe
def bbox_edge_coords(area_name):
    districts = germany_admin('GEM')
    # get polygon of area
    area = districts[districts['GEN'] == area_name]
    area_polygon = area.geometry.iloc[0]
    bbox = transform_crs(area_polygon.envelope, 25832, 4326, True)

    filepath = path.join(RESULTS_PATH, 'geo_data', f'residential_{area_name}.gpkg')
    if path.isfile(filepath):
        residential = read_file(filepath)
    else:
        raise Exception('no residential area saved')
    edges = [LineString([bbox.exterior.coords[i], bbox.exterior.coords[i + 1]]) for i in range(4)]
    houses = [min(residential['geometry'], key=lambda point: edge.distance(point)) for edge in edges]

    names = []
    for geom in houses:
        obj = residential[residential['geometry'] == geom]

        if 'name' in residential.columns and notna(obj['name'].iloc[0]):
            name = obj['name'].iloc[0]
        else:
            name = f'osmid_{obj.index[0]}'
        names.append(name)

    # save Point features and centroids of Polygon features
    for index, pg in enumerate(houses):
        if type(pg) is geometry.point.Point:
            continue
        elif type(pg) is geometry.polygon.Polygon:
            houses[index] = pg.centroid
        else:
            raise Exception('is neither point nor polygon')

    return GeoDataFrame({'name': names, 'geometry': houses}, geometry='geometry')


# test if arg is a Point object, if tuple or list convert it to Point
# {args} arg: Point, tuple or list
# {returns} Point
def is_point_object(arg):
    if isinstance(arg, geometry.point.Point):
        return arg
    elif isinstance(arg, tuple) or isinstance(arg, list):
        return Point(arg[1], arg[0])
    else:
        raise TypeError('is not Point, tuple or list object')


# get the closest stations for one point as a GeoDataFrame
# {args} gtfs_name: str/df, point: Point, number: int, gtfs_zipped: boolean
# {returns} dataframe
def get_stations(gtfs_df, point, number=10):
    stops = gtfs_df['stops']
    point = is_point_object(point)

    # calculate distance from point to all stops in gtfs data
    stops['distance'] = stops.apply(
        lambda row: point.distance(Point(row['stop_lon'], row['stop_lat'])),
        axis=1
    )
    # sort stops by ascending distance and delete duplicate names
    sorted_stops = stops.sort_values('distance')
    unique_stops = sorted_stops[~sorted_stops.duplicated('stop_name')]

    # return stops with the shortest distance to point
    return unique_stops.head(number)


# get the closest stations for all POIs as list of GeoDataFrame
# {args} gtfs_name: str/df, pois: df, number: int, gtfs_zipped: boolean
# {returns} dict
def get_all_stations(gtfs_name, pois, number=10):  # point: [lat, lon] shapely point
    stations = []
    poi_names = []
    poi_locations = []
    for pid, poi in pois.iterrows():
        stations.append(get_stations(gtfs_name, poi['geometry'], number))
        poi_names.append(poi['name'])
        poi_locations.append(poi['geometry'])

    return {'stations': stations, 'cinema_name': poi_names, 'cinema_location': poi_locations}
