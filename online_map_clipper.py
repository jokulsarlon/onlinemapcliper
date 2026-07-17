# -*- coding: utf-8 -*-
import os
import math
import numpy as np
from osgeo import gdal, osr
from qgis.PyQt.QtCore import QSize, Qt, QCoreApplication
from qgis.PyQt.QtWidgets import (
    QAction, QMessageBox, QProgressDialog
)
from qgis.PyQt.QtGui import QIcon, QImage
from qgis.core import (
    QgsProject, QgsMapSettings, QgsMapRendererSequentialJob,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsProcessingUtils, QgsWkbTypes, QgsApplication,
    QgsGeometry, QgsFeature, QgsVectorLayer, QgsRectangle,
    QgsVectorFileWriter
)
from qgis import processing
from .online_map_clipper_dialog import OnlineMapClipperDialog

MAX_PIXELS = 4000 * 4000

class OnlineMapClipper:
    def __init__(self, iface):
        self.iface = iface
        self.dlg = None
        self.render_cache = {}

    def initGui(self):
        plugin_dir = os.path.dirname(__file__)
        icon_path = os.path.join(plugin_dir, "icon.svg")
        icon = QIcon(icon_path)
        self.action = QAction(icon, "Online Map Clipper", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Online Map Clipper", self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&Online Map Clipper", self.action)

    def translate(self, text):
        if self.dlg:
            return self.dlg.translate(text)
        locale = QgsApplication.locale()[:2]
        translations = {
            "Error": "错误",
            "Both online and mask layers must be selected.": "必须选择在线图层和掩膜图层（或勾选画布范围）。",
            "Mask layer must be a polygon layer.": "掩膜图层必须是面图层。",
            "Please specify an output file when saving to file.": "保存到文件时，请指定输出文件路径。",
            "Extent too small to calculate resolution.": "范围太小，无法计算分辨率。",
            "Clip completed successfully!": "裁剪完成！",
            "Success": "成功",
            "Processing error": "处理错误",
            "Image too large": "图像尺寸过大",
            "The output image would be {w}×{h} pixels ({mp:.1f} MP). Continue?":
                "输出图像 {w}×{h} 像素 ({mp:.1f} MP)，可能卡死。继续？",
            "JPEG does not support transparency. The background will be white.":
                "JPEG 不支持透明，背景将变为白色。",
            "Canceled by user": "已取消",
            "Processing...": "处理中...",
            "Cancel": "取消",
            "Rendering online map...": "正在渲染在线地图...",
            "Clipping...": "正在裁剪...",
            "Converting to PNG...": "正在转换为 PNG...",
            "Converting to JPEG (no transparency)...": "正在转换为 JPEG (无透明)...",
            "Creating Cloud Optimized GeoTIFF...": "正在创建云优化 GeoTIFF...",
            "Loading layer...": "正在加载图层...",
        }
        if locale == 'zh':
            return translations.get(text, text)
        return text

    def run(self):
        if self.dlg:
            self.dlg.deleteLater()
        self.dlg = OnlineMapClipperDialog()
        self.dlg.mQgsFileWidget_output.setFilePath("")

        self.dlg.button_box.accepted.connect(self.on_accept)
        self.dlg.button_box.rejected.connect(self.dlg.reject)
        self.dlg.pushButton_zoom_from_canvas.clicked.connect(self._zoom_from_canvas)
        self.dlg.spinBox_zoom.valueChanged.connect(self._update_pixel_preview)
        self.dlg.checkBox_use_canvas.toggled.connect(self._update_pixel_preview)
        self.dlg.mMapLayerComboBox_online.currentIndexChanged.connect(self._update_pixel_preview)
        self.dlg.mMapLayerComboBox_mask.currentIndexChanged.connect(self._update_pixel_preview)
        self.dlg.checkBox_buffer.toggled.connect(self._update_pixel_preview)
        self.dlg.spinBox_buffer.valueChanged.connect(self._update_pixel_preview)
        self.dlg.show()

    def _zoom_from_canvas(self):
        if self.iface.mapCanvas().scale() == 0:
            return
        dpi = 96
        circum_m = 40075016.686
        pixel_per_meter = dpi / 0.0254
        scale = self.iface.mapCanvas().scale()
        zoom = math.log2((circum_m * pixel_per_meter) / (256 * scale))
        zoom = int(round(zoom))
        zoom = max(0, min(22, zoom))
        self.dlg.spinBox_zoom.setValue(zoom)

    def _update_pixel_preview(self):
        online_layer = self.dlg.mMapLayerComboBox_online.currentLayer()
        use_canvas = self.dlg.checkBox_use_canvas.isChecked()
        mask_layer = self.dlg.mMapLayerComboBox_mask.currentLayer()

        if not online_layer:
            self.dlg.label_pixel_estimate.setText("--")
            return
        if not use_canvas and not mask_layer:
            self.dlg.label_pixel_estimate.setText("--")
            return

        try:
            if use_canvas:
                extent = self.iface.mapCanvas().extent()
                extent_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
            else:
                extent = mask_layer.extent()
                extent_crs = mask_layer.crs()

            target_crs = online_layer.crs()
            xform = QgsCoordinateTransform(extent_crs, target_crs, QgsProject.instance())
            extent = xform.transform(extent)

            if self.dlg.checkBox_buffer.isChecked():
                buffer_dist = self.dlg.spinBox_buffer.value()
                extent = extent.buffered(buffer_dist)

            zoom = self.dlg.spinBox_zoom.value()
            lat_center = QgsCoordinateTransform(
                target_crs,
                QgsCoordinateReferenceSystem('EPSG:4326'),
                QgsProject.instance()
            ).transform(extent.center()).y()
            res = self._resolution_from_zoom(zoom, lat_center, crs=target_crs)
            w = int(math.ceil(extent.width() / res))
            h = int(math.ceil(extent.height() / res))
            unit = "像素" if self.dlg._locale == 'zh' else "px"
            self.dlg.label_pixel_estimate.setText(f"{w} × {h} {unit}")
        except:
            self.dlg.label_pixel_estimate.setText("--")

    def on_accept(self):
        online_layer = self.dlg.mMapLayerComboBox_online.currentLayer()
        use_canvas = self.dlg.checkBox_use_canvas.isChecked()
        mask_layer = self.dlg.mMapLayerComboBox_mask.currentLayer()

        if not online_layer:
            QMessageBox.warning(self.dlg, self.translate("Error"),
                                self.translate("Both online and mask layers must be selected."))
            return
        if not use_canvas and not mask_layer:
            QMessageBox.warning(self.dlg, self.translate("Error"),
                                self.translate("Both online and mask layers must be selected."))
            return
        if not use_canvas and mask_layer:
            if mask_layer.geometryType() != QgsWkbTypes.PolygonGeometry:
                QMessageBox.warning(self.dlg, self.translate("Error"),
                                    self.translate("Mask layer must be a polygon layer."))
                return

        zoom = self.dlg.spinBox_zoom.value()
        tile_size = self.dlg.spinBox_tile_size.value()
        transparent = self.dlg.checkBox_transparent.isChecked()
        fmt = self.dlg.comboBox_format.currentText()
        save_to_file = self.dlg.checkBox_save_to_file.isChecked()
        buffer_enabled = self.dlg.checkBox_buffer.isChecked()
        buffer_dist = self.dlg.spinBox_buffer.value() if buffer_enabled else 0

        target_crs = online_layer.crs()

        # 构建裁剪几何
        if use_canvas:
            canvas_extent = self.iface.mapCanvas().extent()
            canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
            rect = QgsRectangle(canvas_extent)
            geom = QgsGeometry.fromRect(rect)
            xform = QgsCoordinateTransform(canvas_crs, target_crs, QgsProject.instance())
            geom.transform(xform)
        else:
            features = mask_layer.getFeatures()
            geoms = [f.geometry() for f in features]
            if not geoms:
                QMessageBox.warning(self.dlg, self.translate("Error"), "Mask layer has no features.")
                return
            geom = QgsGeometry.unaryUnion(geoms)
            mask_crs = mask_layer.crs()
            if mask_crs != target_crs:
                xform = QgsCoordinateTransform(mask_crs, target_crs, QgsProject.instance())
                geom.transform(xform)

        if buffer_dist > 0:
            if target_crs.isGeographic():
                QMessageBox.warning(self.dlg, self.translate("Error"),
                                    "Buffer distance in degrees not recommended. "
                                    "Please use a projected CRS for the mask.")
                return
            geom = geom.buffer(buffer_dist, 5)

        extent = geom.boundingBox()
        extent.scale(1.001)

        lat_center = QgsCoordinateTransform(
            target_crs,
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsProject.instance()
        ).transform(extent.center()).y()
        res = self._resolution_from_zoom(zoom, lat_center, tile_size, target_crs)
        width_pix = int(math.ceil(extent.width() / res))
        height_pix = int(math.ceil(extent.height() / res))
        if width_pix == 0 or height_pix == 0:
            QMessageBox.warning(self.dlg, self.translate("Error"),
                                self.translate("Extent too small to calculate resolution."))
            return

        total_pixels = width_pix * height_pix
        if total_pixels > MAX_PIXELS:
            reply = QMessageBox.warning(
                self.dlg,
                self.translate("Image too large"),
                self.translate("The output image would be {w}×{h} pixels ({mp:.1f} MP). Continue?")
                .format(w=width_pix, h=height_pix, mp=total_pixels/1e6),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        suffix_map = {"GeoTIFF": ".tif", "PNG": ".png", "JPEG": ".jpg", "COG": ".tif"}

        if save_to_file:
            output_base = self.dlg.mQgsFileWidget_output.filePath()
            if not output_base:
                QMessageBox.warning(self.dlg, self.translate("Error"),
                                    self.translate("Please specify an output file when saving to file."))
                return
            ext = suffix_map.get(fmt, ".tif")
            if not output_base.lower().endswith(ext):
                output_base += ext
            output = output_base
            is_temp = False
        else:
            ext = suffix_map.get(fmt, ".tif")
            output = QgsProcessingUtils.generateTempFilename(f"clipped{ext}")
            is_temp = True

        temp_mask_path = QgsProcessingUtils.generateTempFilename('mask.shp')
        mask_layer_tmp = QgsVectorLayer("Polygon?crs=" + target_crs.authid(),
                                        "mask_tmp", "memory")
        prov = mask_layer_tmp.dataProvider()
        feat = QgsFeature()
        feat.setGeometry(geom)
        prov.addFeatures([feat])
        error = QgsVectorFileWriter.writeAsVectorFormat(
            mask_layer_tmp, temp_mask_path, "UTF-8", target_crs, "ESRI Shapefile"
        )
        if error[0] != QgsVectorFileWriter.NoError:
            raise Exception("Failed to write temporary mask shapefile")

        progress = QProgressDialog(self.translate("Processing..."), self.translate("Cancel"), 0, 100, self.dlg)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(5)

        def update_progress(val, text_key=None):
            if text_key:
                progress.setLabelText(self.translate(text_key))
            progress.setValue(val)
            QCoreApplication.processEvents()
            return progress.wasCanceled()

        cancel = False

        render_tif = None
        cache_key = (online_layer.id(), extent.toString(), zoom, tile_size, transparent)
        if cache_key in self.render_cache:
            render_tif = self.render_cache[cache_key]
            if not os.path.exists(render_tif):
                del self.render_cache[cache_key]
                render_tif = None

        if not render_tif:
            cancel = update_progress(10, "Rendering online map...")
            if cancel:
                progress.close()
                self._cleanup_temp(temp_mask_path)
                return

            settings = QgsMapSettings()
            settings.setLayers([online_layer])
            settings.setDestinationCrs(target_crs)
            settings.setExtent(extent)
            settings.setOutputSize(QSize(width_pix, height_pix))
            settings.setBackgroundColor(Qt.transparent if transparent else Qt.white)

            job = QgsMapRendererSequentialJob(settings)
            job.start()
            job.waitForFinished()
            image = job.renderedImage()
            if image.isNull():
                raise Exception("Render produced null image")

            render_tif = QgsProcessingUtils.generateTempFilename('render_cache.tif')
            self._qimage_to_geotiff(image, extent, target_crs, render_tif)
            if len(self.render_cache) > 5:
                old_key = next(iter(self.render_cache))
                old_path = self.render_cache.pop(old_key)
                if os.path.exists(old_path):
                    os.remove(old_path)
            self.render_cache[cache_key] = render_tif

        if fmt == "GeoTIFF":
            clip_output = output
        else:
            clip_output = QgsProcessingUtils.generateTempFilename('clip.tif')

        cancel = update_progress(60, "Clipping...")
        if cancel:
            progress.close()
            self._cleanup_temp(temp_mask_path, clip_output)
            return

        try:
            processing.run("gdal:cliprasterbymasklayer", {
                'INPUT': render_tif,
                'MASK': temp_mask_path,
                'SOURCE_CRS': None,
                'TARGET_CRS': None,
                'ALPHA_BAND': True,
                'CROP_TO_CUTLINE': True,
                'KEEP_RESOLUTION': True,
                'OUTPUT': clip_output
            })
        except Exception as e:
            progress.close()
            self._cleanup_temp(temp_mask_path, clip_output)
            raise e

        if fmt == "PNG":
            cancel = update_progress(80, "Converting to PNG...")
            if cancel:
                progress.close()
                self._cleanup_temp(temp_mask_path, clip_output)
                return
            self._convert_raster(clip_output, output, "PNG")
            os.remove(clip_output)
        elif fmt == "JPEG":
            cancel = update_progress(80, "Converting to JPEG (no transparency)...")
            if cancel:
                progress.close()
                self._cleanup_temp(temp_mask_path, clip_output)
                return
            self._convert_raster(clip_output, output, "JPEG", quality=90)
            os.remove(clip_output)
        elif fmt == "COG":
            cancel = update_progress(80, "Creating Cloud Optimized GeoTIFF...")
            if cancel:
                progress.close()
                self._cleanup_temp(temp_mask_path, clip_output)
                return
            processing.run("gdal:translate", {
                'INPUT': clip_output,
                'OUTPUT': output,
                'TILED': True,
                'COPY_SUBDATASETS': False,
                'EXTRA': '-co COMPRESS=LZW -co COPY_SRC_OVERVIEWS=YES',
            })
            ds = gdal.Open(output, 1)
            if ds:
                ds.BuildOverviews("NEAREST", [2,4,8,16])
                ds = None
            if clip_output != output:
                self._cleanup_temp(clip_output)

        self._cleanup_temp(temp_mask_path)

        cancel = update_progress(90, "Loading layer...")
        layer_name = "Clipped" if is_temp else os.path.splitext(os.path.basename(output))[0]
        new_layer = self.iface.addRasterLayer(output, layer_name)
        if new_layer:
            self.iface.setActiveLayer(new_layer)
            self.iface.zoomToActiveLayer()

        progress.setValue(100)
        progress.close()

        QMessageBox.information(self.dlg, self.translate("Success"),
                                self.translate("Clip completed successfully!"))

    def _resolution_from_zoom(self, zoom, lat_center, tile_size=256, crs=None):
        """
        根据缩放级别计算每个像素所代表的地图单位。
        如果 crs 是地理坐标系（度），返回每像素度数；
        否则返回每像素米数（基于 Web Mercator 投影）。
        """
        if crs and crs.isGeographic():
            return 360.0 / (tile_size * (2 ** zoom))
        else:
            circum = 40075016.68557849
            res = circum / (tile_size * (2 ** zoom))
            res *= math.cos(math.radians(lat_center))
            return res

    def _qimage_to_geotiff(self, qimage, extent, crs, output_path):
        img = qimage.convertToFormat(QImage.Format_RGBA8888).copy()
        width, height = img.width(), img.height()
        ptr = img.bits()
        ptr.setsize(img.byteCount())
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 4))

        driver = gdal.GetDriverByName('GTiff')
        ds = driver.Create(output_path, width, height, 4, gdal.GDT_Byte)
        geotrans = [extent.xMinimum(), extent.width()/width, 0,
                    extent.yMaximum(), 0, -extent.height()/height]
        ds.SetGeoTransform(geotrans)

        # 使用 authid 代替 toWkt() 以避免 GDAL 解析错误
        srs = osr.SpatialReference()
        authid = crs.authid()
        if authid:
            srs.SetFromUserInput(authid)
        else:
            # 回退到 WKT，但清理换行符
            wkt = crs.toWkt().replace('\n', ' ').strip()
            srs.ImportFromWkt(wkt)
        ds.SetProjection(srs.ExportToWkt())

        for b in range(4):
            ds.GetRasterBand(b+1).WriteArray(arr[:,:,b])
        ds.FlushCache()
        ds = None

    def _convert_raster(self, src, dst, fmt, quality=90):
        src_ds = gdal.Open(src)
        if not src_ds:
            raise Exception("Cannot open source for conversion")
        if fmt == "JPEG":
            gdal.Translate(dst, src_ds, format='JPEG',
                           outputType=gdal.GDT_Byte,
                           creationOptions=[f'QUALITY={quality}'])
        elif fmt == "PNG":
            gdal.Translate(dst, src_ds, format='PNG',
                           outputType=gdal.GDT_Byte)
        else:
            raise ValueError(f"Unsupported conversion format: {fmt}")
        src_ds = None

    def _cleanup_temp(self, *paths):
        for p in paths:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass