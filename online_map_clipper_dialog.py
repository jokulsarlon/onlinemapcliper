# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QFormLayout,
    QLabel, QSpinBox, QPushButton, QCheckBox, QProgressBar,
    QDialogButtonBox, QHBoxLayout, QDoubleSpinBox, QComboBox
)
from qgis.gui import QgsMapLayerComboBox, QgsFileWidget
from qgis.core import QgsMapLayerProxyModel, QgsApplication

class OnlineMapClipperDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.languages = {"English": "en", "中文": "zh"}
        qgis_locale = QgsApplication.locale()[:2]
        self._locale = qgis_locale if qgis_locale in self.languages.values() else "en"

        self.setWindowTitle("Online Map Clipper")
        self.resize(500, 580)

        main_layout = QVBoxLayout()

        # 语言选择
        lang_layout = QHBoxLayout()
        lang_layout.addStretch()
        self.comboBox_lang = QComboBox()
        self.comboBox_lang.addItems(list(self.languages.keys()))
        current_lang_text = [k for k, v in self.languages.items() if v == self._locale]
        if current_lang_text:
            self.comboBox_lang.setCurrentText(current_lang_text[0])
        self.comboBox_lang.currentTextChanged.connect(self.on_language_changed)
        self.label_lang = QLabel()
        lang_layout.addWidget(self.label_lang)
        lang_layout.addWidget(self.comboBox_lang)
        main_layout.addLayout(lang_layout)

        # 图层
        self.layers_group = QGroupBox()
        layers_form = QFormLayout()

        self.mMapLayerComboBox_online = QgsMapLayerComboBox()
        self.mMapLayerComboBox_online.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.label_online_layer = QLabel()
        layers_form.addRow(self.label_online_layer, self.mMapLayerComboBox_online)

        self.mMapLayerComboBox_mask = QgsMapLayerComboBox()
        self.mMapLayerComboBox_mask.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.label_mask_layer = QLabel()
        layers_form.addRow(self.label_mask_layer, self.mMapLayerComboBox_mask)

        self.checkBox_use_canvas = QCheckBox()
        layers_form.addRow("", self.checkBox_use_canvas)
        self.checkBox_use_canvas.toggled.connect(self.mMapLayerComboBox_mask.setDisabled)

        self.layers_group.setLayout(layers_form)
        main_layout.addWidget(self.layers_group)

        # 设置
        self.settings_group = QGroupBox()
        settings_form = QFormLayout()

        zoom_layout = QHBoxLayout()
        self.spinBox_zoom = QSpinBox()
        self.spinBox_zoom.setRange(0, 22)
        self.spinBox_zoom.setValue(15)
        zoom_layout.addWidget(self.spinBox_zoom)
        self.pushButton_zoom_from_canvas = QPushButton()
        zoom_layout.addWidget(self.pushButton_zoom_from_canvas)
        self.label_zoom = QLabel()
        settings_form.addRow(self.label_zoom, zoom_layout)

        self.checkBox_buffer = QCheckBox()
        self.spinBox_buffer = QDoubleSpinBox()
        self.spinBox_buffer.setRange(0, 100000)
        self.spinBox_buffer.setValue(100)
        self.spinBox_buffer.setSuffix(" m")
        self.spinBox_buffer.setEnabled(False)
        self.checkBox_buffer.toggled.connect(self.spinBox_buffer.setEnabled)
        buf_layout = QHBoxLayout()
        buf_layout.addWidget(self.checkBox_buffer)
        buf_layout.addWidget(self.spinBox_buffer)
        self.label_buffer = QLabel()
        settings_form.addRow(self.label_buffer, buf_layout)

        self.comboBox_format = QComboBox()
        self.comboBox_format.addItems(["GeoTIFF", "PNG", "JPEG", "COG"])
        self.label_format = QLabel()
        settings_form.addRow(self.label_format, self.comboBox_format)

        save_layout = QVBoxLayout()
        self.checkBox_save_to_file = QCheckBox()
        self.checkBox_save_to_file.setChecked(False)
        save_layout.addWidget(self.checkBox_save_to_file)
        self.mQgsFileWidget_output = QgsFileWidget()
        self.mQgsFileWidget_output.setStorageMode(QgsFileWidget.SaveFile)
        self.mQgsFileWidget_output.setFilter("All files (*.*)")
        self.mQgsFileWidget_output.setEnabled(False)
        save_layout.addWidget(self.mQgsFileWidget_output)
        self.label_output_file = QLabel()
        settings_form.addRow(self.label_output_file, save_layout)
        self.checkBox_save_to_file.toggled.connect(self.mQgsFileWidget_output.setEnabled)

        self.label_pixel_estimate = QLabel("--")
        self.label_estimate = QLabel()
        settings_form.addRow(self.label_estimate, self.label_pixel_estimate)

        self.settings_group.setLayout(settings_form)
        main_layout.addWidget(self.settings_group)

        # 高级
        self.adv_group = QGroupBox()
        self.adv_group.setCheckable(True)
        self.adv_group.setChecked(False)
        adv_form = QFormLayout()

        self.spinBox_tile_size = QSpinBox()
        self.spinBox_tile_size.setRange(64, 1024)
        self.spinBox_tile_size.setValue(256)
        self.label_tile_size = QLabel()
        adv_form.addRow(self.label_tile_size, self.spinBox_tile_size)

        self.spinBox_dpi = QSpinBox()
        self.spinBox_dpi.setRange(72, 600)
        self.spinBox_dpi.setValue(96)
        self.label_dpi = QLabel()
        adv_form.addRow(self.label_dpi, self.spinBox_dpi)

        self.checkBox_transparent = QCheckBox()
        self.checkBox_transparent.setChecked(True)
        adv_form.addRow("", self.checkBox_transparent)

        self.adv_group.setLayout(adv_form)
        main_layout.addWidget(self.adv_group)

        self.progressBar = QProgressBar()
        self.progressBar.setValue(0)
        main_layout.addWidget(self.progressBar)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_ok = self.button_box.button(QDialogButtonBox.Ok)
        self.button_cancel = self.button_box.button(QDialogButtonBox.Cancel)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)
        self.retranslateUi()

    def on_language_changed(self, text):
        self._locale = self.languages.get(text, "en")
        self.retranslateUi()

    def retranslateUi(self):
        self.setWindowTitle(self.tr("Online Map Clipper"))
        self.label_lang.setText(self.tr("Language:"))
        self.layers_group.setTitle(self.tr("Layers"))
        self.settings_group.setTitle(self.tr("Settings"))
        self.adv_group.setTitle(self.tr("Advanced"))

        self.label_online_layer.setText(self.tr("Online map layer:"))
        self.label_mask_layer.setText(self.tr("Mask layer (optional):"))
        self.checkBox_use_canvas.setText(self.tr("Use current canvas extent"))

        self.label_zoom.setText(self.tr("Zoom level (0-22):"))
        self.pushButton_zoom_from_canvas.setText(self.tr("From Canvas"))
        self.checkBox_buffer.setText(self.tr("Expand mask by buffer"))
        self.label_buffer.setText(self.tr("Buffer:"))
        self.label_format.setText(self.tr("Output format:"))
        self.checkBox_save_to_file.setText(self.tr("Save to file"))
        self.label_output_file.setText(self.tr("Output file:"))
        self.label_estimate.setText(self.tr("Estimated size:"))

        self.label_tile_size.setText(self.tr("Tile size (px):"))
        self.label_dpi.setText(self.tr("DPI:"))
        self.checkBox_transparent.setText(self.tr("Transparent background"))

        self.button_ok.setText(self.tr("OK"))
        self.button_cancel.setText(self.tr("Cancel"))

    def tr(self, text):
        translations = {
            "Online Map Clipper": "在线地图裁剪器",
            "Language:": "语言:",
            "Layers": "图层",
            "Settings": "设置",
            "Advanced": "高级",
            "Online map layer:": "在线地图图层:",
            "Mask layer (optional):": "掩膜图层（可选）:",
            "Use current canvas extent": "使用当前画布范围",
            "Zoom level (0-22):": "缩放级别 (0-22):",
            "From Canvas": "从画布获取",
            "Expand mask by buffer": "掩膜外扩缓冲",
            "Buffer:": "缓冲距离:",
            "Output format:": "输出格式:",
            "Save to file": "保存到文件",
            "Output file:": "输出文件:",
            "Estimated size:": "预估尺寸:",
            "Tile size (px):": "瓦片大小 (像素):",
            "DPI:": "DPI:",
            "Transparent background": "透明背景",
            "OK": "确定",
            "Cancel": "取消",
        }
        if self._locale == 'zh':
            return translations.get(text, text)
        return text

    def translate(self, text):
        return self.tr(text)