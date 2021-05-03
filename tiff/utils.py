from rasterio import rasterio, shutil
import numpy as np

from .tiff import GeoTiff

np_type = "uint8"
transparency = 255

def compose(path: str, hh: GeoTiff, hv: GeoTiff, bands=4):
    width, height = hh.get_size()

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

    result.write(hh.get_map_by_indexes(0, 0, width, height).astype(np_type), 1)
    result.write(hv.get_map_by_indexes(0, 0, width, height).astype(np_type), 2)
    result.write(np.zeros((width, height), dtype=np_type), 3)
    if bands == 4:
        result.write(np.full((width, height), transparency, dtype=np_type), 4)

    result.close()
