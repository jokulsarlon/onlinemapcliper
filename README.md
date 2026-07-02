Plugin Name: Online Map Clipper
Brief Description
Clip online basemaps (XYZ tiles, WMS) using a vector mask or canvas extent at a specified zoom level. Output as GeoTIFF, PNG, JPEG, or COG.
Full Description
This plugin solves a common frustration in QGIS: the built‑in “Rasterize Map Canvas” tool renders all visible layers together, so you can’t isolate just the online basemap. Moreover, online layers are tiled at fixed zoom levels – exporting without considering this leads to blurry or misaligned results.
Online Map Clipper gives you full control:
Single‑layer rendering – only the selected online map layer is rendered, keeping the background transparent.
Flexible clipping – use any polygon vector layer as a mask, or simply clip to the current map canvas extent.
Zoom‑level accuracy – specify the tile zoom level (0‑22) to match the exact resolution you need. A “From Canvas” button estimates the closest zoom.
Buffer support – expand the mask by a distance in meters (useful for adding margins when using a projected CRS).
Multiple output formats – save as GeoTIFF, PNG, JPEG, or Cloud Optimized GeoTIFF (COG). Transparency is preserved in all formats except JPEG.
Automatic layer loading – the clipped raster is added to the map and the canvas is zoomed to it immediately.
Performance aids – a render cache prevents redundant tile downloads for the same area/zoom; a progress bar shows each step, and you can cancel at any time.
Bilingual interface – switch between English and Chinese (中文) with a dropdown in the dialog.
Usage
Ideal for creating custom offline basemaps, extracting satellite imagery for reports, or preparing tiles for mobile GIS applications.
Limitations
To avoid freezing QGIS, the plugin warns when the output image exceeds 16 megapixels (≈4000×4000 px). For larger exports, reduce the zoom level or split the area into multiple clips.
Installation
Copy the plugin folder into your QGIS profile’s python/plugins/ directory, enable it in the Plugin Manager, and a toolbar icon will appear. Requires QGIS 3.22+ and the standard NumPy/GDAL libraries (included in QGIS).
