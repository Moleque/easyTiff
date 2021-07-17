import numpy as np

from rasterio import rasterio
from PIL import Image

from .tiff import GeoTiff

transparency = 255


def compose(path: str, hh: GeoTiff, hv: GeoTiff, bands=4, np_type=None):
    if np_type is None:
        np_type = hh.get_dtype()

    height, width = hh.get_size()

    result = rasterio.open(
        path, "w", 
        driver="GTiff",
        height=height,
        width=width,
        count=bands,
        dtype=np_type,
        crs=hh.get_crs(),
        transform=hh.get_transform(),
    )

    first_band = hh.get_map_by_indexes(0, 0, height, width).astype(np_type)
    second_band = hv.get_map_by_indexes(0, 0, height, width).astype(np_type)

    result.write(first_band, 1)
    result.write(second_band, 2)
    result.write(np.zeros((height, width), dtype=np_type), 3)
    
    if bands == 4:
        transparency_band = np.full((height, width), transparency, dtype=np_type)
        transparency_band[np.all([first_band==0, second_band==0], axis=0)] = 0
        result.write(transparency_band, 4)

    result.close()


def compose_grayscale(path: str, hh: GeoTiff, hv: GeoTiff, np_type=None):
    if np_type is None:
        np_type = hh.get_dtype()

    height, width = hh.get_size()

    result = rasterio.open(
        path, "w", 
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=np_type,
        crs=hh.get_crs(),
        transform=hh.get_transform(),
    )

    image = np.stack((
        np.reshape(hh.get_map_by_indexes(0, 0, height, width).astype(np_type), (height, width)),
        np.reshape(hv.get_map_by_indexes(0, 0, height, width).astype(np_type), (height, width)),
        np.zeros((height, width), dtype=np_type),
    ), axis=2)

    grayscale = np.asarray(Image.fromarray(image, mode="RGB").convert("L"))

    result.write(grayscale, 1)

    result.close()
