from shapely import geometry
from osmnx import features

from scripts.utils import transform_crs


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
