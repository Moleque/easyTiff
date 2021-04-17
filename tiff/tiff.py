import os
import warnings
from rasterio import rasterio, shutil
from pyproj.transformer import Transformer
from pyproj.crs import CRS
from geopy.point import Point
from PIL import Image


class GeoTiff:
    def __init__(self, path):
        with warnings.catch_warnings(record=True) as w: # отлавливаем ошибки
            self.path = path
            self.file = rasterio.open(path)
            if len(w) > 0 and issubclass(w[-1].category, rasterio.errors.NotGeoreferencedWarning): # если файл имеет контрольные точки
                self.file = rasterio.vrt.WarpedVRT(self.file, src_crs=self.file.gcps[1], scrs=self.file.gcps[1])    # приводим его к виду georeferenced


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
    def get_coordinate_by_index(self, width, height):
        row, col = self.file.xy(height, width)
        return self._transform_to_coordinates(row, col)


    # получить индексы координаты
    def get_index_by_coordinate(self, coordinate):
        x, y = self._transform_to_meters(coordinate)
        return self.file.index(x, y)


    # получить numpy отрезок снимка по индексам
    def get_map_by_indexes(self, width1, height1, width2, height2):
        return self.file.read(1)[width1:width2, height1:height2]


    # получить numpy отрезок снимка по координатам
    def get_map_by_coordinates(self, coordinate1, coordinate2):
        width1, height1 = self.get_index_by_coordinate(coordinate1)
        width2, height2 = self.get_index_by_coordinate(coordinate2)
        return self.get_map_by_indexes(width1, height1, width2, height2)


    # сохранить часть изображения по индексам
    def save_image_by_indexes(self, path, width1, height1, width2, height2):
        image_map = self.get_map_by_indexes(width1, height1, width2, height2)
        Image.fromarray(image_map, mode='L').save(path)


    # сохранить часть изображения по координатам
    def save_image_by_coordinates(self, path, coordinate1, coordinate2):
        image_map = self.get_map_by_coordinates(coordinate1, coordinate2)
        Image.fromarray(image_map, mode='L').save(path)


    # сохранить снимок в виде Georeferenced (по умолчанию перезаписать)
    def save_file_as_georeferenced(self, path=None):
        if path is None:
            path = self.path

        shutil.copy(self.file, path, driver='GTiff')


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
