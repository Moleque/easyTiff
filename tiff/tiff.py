import warnings, os
from rasterio import rasterio, shutil
from pyproj.transformer import Transformer
from pyproj.crs import CRS
from geopy.point import Point
from PIL import Image
import numpy as np

def check_value(value, max):
    if value < 0:
        return 0
    if value > max:
        return max
    return value

class GeoTiff:
    def __init__(self, path):
        with warnings.catch_warnings(record=True) as w: # отлавливаем ошибки
            self.path = path
            self.path_writable = "writable_temp.tiff"

            self.file = rasterio.open(path) 
            
            if len(w) > 0 and issubclass(w[-1].category, rasterio.errors.NotGeoreferencedWarning): # если файл имеет контрольные точки
                self.file = rasterio.vrt.WarpedVRT(self.file, src_crs=self.file.gcps[1], scrs=self.file.gcps[1])    # приводим его к виду georeferenced

        self._create_writable_file()

    
    def _create_writable_file(self):
        self.writable_file = rasterio.open(
            self.path_writable, "w",
            driver="GTiff",
            height=self.file.height,
            width=self.file.width,
            count=self.file.count,
            dtype=self.file.read(1).dtype,
            crs=self.file.crs,
            transform=self.file.transform,
        )

        for channel in range(1, self.file.count + 1):
            channel_map = self.file.read(channel)
            self.writable_file.write(channel_map, channel)


    def __del__(self):
        try:
            self.file.close()
            self.writable_file.close()
        except AttributeError:
            pass
        if os.path.exists(self.path_writable):
            os.remove(self.path_writable)


    # получить размеры изображения
    def get_size(self):
        return self.file.height, self.file.width


    def get_crs(self):
        return self.file.crs


    def get_transform(self):
        return self.file.transform


    # получить тип данных пикселя
    def get_dtype(self):
        return self.file.read(1).dtype


    # получить координаты крайних точек изображения
    def get_corner_coordinates(self):
        height, width = self.get_size()
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
        height_max, width_max = self.get_size()
        x, y = self._transform_to_meters(coordinate)
        height, width = self.file.index(y, x)
        
        height = check_value(height, height_max)
        width = check_value(width, width_max)
        
        return height, width


    # получить numpy отрезок снимка по индексам
    def get_map_by_indexes(self, width1, height1, width2, height2, channel=1):
        return self.file.read(channel)[height1:height2, width1:width2]


    # получить numpy отрезок снимка по индексам
    def get_stack_by_indexes(self, width1, height1, width2, height2):
        if self.file.count == 1:
            image_map = self.get_map_by_indexes(width1, height1, width2, height2)
        elif self.file.count == 3:
            image_map = np.stack((
                np.reshape(self.get_map_by_indexes(width1, height1, width2, height2, 1), (height2-height1, width2-width1, 1)), 
                np.reshape(self.get_map_by_indexes(width1, height1, width2, height2, 2), (height2-height1, width2-width1, 1)),
                np.reshape(self.get_map_by_indexes(width1, height1, width2, height2, 3), (height2-height1, width2-width1, 1)),
            ), axis=2)
        else:
            image_map = np.stack((
                np.reshape(self.get_map_by_indexes(width1, height1, width2, height2, 1), (height2-height1, width2-width1, 1)), 
                np.reshape(self.get_map_by_indexes(width1, height1, width2, height2, 2), (height2-height1, width2-width1, 1)),
                np.reshape(self.get_map_by_indexes(width1, height1, width2, height2, 3), (height2-height1, width2-width1, 1)),
                np.reshape(self.get_map_by_indexes(width1, height1, width2, height2, 4), (height2-height1, width2-width1, 1)),
            ), axis=2)
        return image_map


    # установить numpy отрезок снимка по индексам TODO check
    def set_map_by_indexes(self, width1, height1, width2, height2, slice_map, channel=1):
        channel_map = self.file.read(channel)
        channel_map[height1:height2, width1:width2] = slice_map
        return self.writable_file.write(channel_map, channel)

    
    # установить numpy отрезок снимка по индексам
    def set_stack_by_indexes(self, width1, height1, width2, height2, slice_map):
        if self.file.count == 1:
            self.set_map_by_indexes(width1, height1, width2, height2, slice_map)
        else:
            maps = np.split(slice_map, self.file.count, axis=2)
            for map in maps:
                map = np.reshape(map, (width2-width1, height2-height1))
                self.set_map_by_indexes(width1, height1, width2, height2, map)


    # получить numpy отрезок снимка по координатам
    def get_map_by_coordinates(self, coordinate1, coordinate2, channel=1):
        height1, width1 = self.get_index_by_coordinate(coordinate1)
        height2, width2 = self.get_index_by_coordinate(coordinate2)
        return self.get_map_by_indexes(width1, height1, width2, height2, channel)


    # изменить значение прозрачности
    def change_transparency(self, transparency=255, pixel_value=0):
        if self.file.count < 4:
            return
        height, width = self.get_size()
        tr = np.zeros((height, width), dtype=self.get_dtype())
        for band in range(1, self.file.count):
            image_map = self.get_map_by_indexes(0, 0, width, height, band)
            for h in range(height):
                for w in range(width):
                    if image_map[h][w] == pixel_value:
                        tr[h][w] = transparency      
        self.file.write(tr, 4)


    # сохранить часть изображения по индексам
    def save_image_by_indexes(self, path, width1, height1, width2, height2, shape=False):
        height, width = self.get_size()
        if width1 > width2 or height1 > height2 or width1 > width or height1 > height:
            return False
        
        if width2 > width:
            if shape:
                return False
            width2 = width
        if height2 > height:
            if shape:
                return False
            height2 = height
        
        if self.file.count == 1:
            mode = "L"
        elif self.file.count == 3:
            mode = "RGB"
        else:
            mode = "RGBA"
        
        stack = self.get_stack_by_indexes(width1, height1, width2, height2)
        Image.fromarray(stack, mode=mode).save(path)
        return True


    # сохранить часть изображения по координатам
    def save_image_by_coordinates(self, path, coordinate1, coordinate2, mode="L"):
        height1, width1 = self.get_index_by_coordinate(coordinate1)
        height2, width2 = self.get_index_by_coordinate(coordinate2)
        return self.save_image_by_indexes(path, width1, height1, width2, height2, mode)


    # сохранить снимок в виде Georeferenced (по умолчанию перезаписать)
    def save_file_as_georeferenced(self, path=None):
        if path is None:
            path = self.path
        shutil.copy(self.file, path, driver='GTiff')
        return True


    # сохранить writable снимок (по умолчанию перезаписать)
    def save_file(self, path=None):
        if path is None:
            path = self.path
        shutil.copy(self.writable_file, path, driver='GTiff')
        return True


    # перевести метрическую систему координат в географическую
    def _transform_to_coordinates(self, x, y):
        if self.file.crs == CRS("EPSG:4326"):
            return Point(y, x)
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
        if self.file.crs != CRS("EPSG:4326"):
            return y, x
        return x, y
