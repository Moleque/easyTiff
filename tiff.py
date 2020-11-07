import rasterio
import warnings
from pyproj.transformer import Transformer
from pyproj.crs import CRS
from geopy.point import Point


class TiffImage:
    def __init__(self, path):
        self.file = rasterio.open(path)
        

    # получить размеры изображения
    def get_size(self):
        return self.file.width, self.file.height


    # получить координаты крайних точек изображения
    def get_corner_coordinates(self):
        width, height = self.get_size()
        return [
            self._transform_to_coordinates(*self.file.xy(0, 0)),
            self._transform_to_coordinates(*self.file.xy(0, width)),
            self._transform_to_coordinates(*self.file.xy(height, 0)),
            self._transform_to_coordinates(*self.file.xy(height, width)),
        ]


    # получить координаты по индексу
    def get_coordinates_by_index(self, width, height):
        row, col = self.file.xy(height, width)
        print(row, col)
        row, col = self.file.transform * (width, height)
        print(row, col)
        return self._transform_to_coordinates(row, col)


    # получить индексы координаты
    def get_index_by_coordinates(self, coordinate):
        x, y = self._transform_to_meters(coordinate)
        return self.file.index(x, y)


    # перевести метрическую систему координат в географическую
    def _transform_to_coordinates(self, x, y):
        transformer = Transformer.from_proj(self.file.crs, CRS("EPSG:4326"))
        lat, lon = transformer.transform(x, y)
        lon = abs(lon+90)
        if abs(lon-90) > abs(lon-180):
            if abs(lon-180) > abs(lon-270):
                lon = abs(270-lon) + 90
            else:
                lon = lon - 90
        return Point(lat, lon)


    # перевести географическую систему координат в метрическую
    def _transform_to_meters(self, coordinate):
        transformer = Transformer.from_crs(CRS("EPSG:4326"), self.file.crs)
        x, y = transformer.transform(coordinate.latitude, coordinate.longitude)
        return y, x
