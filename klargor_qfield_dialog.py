import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (
    QgsProject, QgsField, QgsWkbTypes,
    QgsEditorWidgetSetup, QgsDefaultValue,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsFillSymbol,
    QgsMarkerSymbol,
)

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'klargor_qfield_dialog.ui'))

STATUS_FIELD = 'status'
VAL_IKKE = 'Ikke-udtaget'
VAL_UDTAGET = 'Udtaget'

JORDTYPE_VALG = [
    'Groft og fint grus',
    'Grovkornet sand',
    'Uomsat tørv',
    'Mellemkornet sand',
    'Mellemkornet sand med indslag af omsat tørv',
    'Finkornet sand',
    'Moderat omsat tørv',
    'Gytjeholdig sand',
    'Stærkt omsat tørv',
    'Silt',
    'Ler',
    'Kalkgytje',
    'Fuldstændig omsat tørv',
]

# (feltnavn, QVariant-type, alias, widget-type, widget-config)
FIELDS = [
    ('status',      QVariant.String,  'status',          'ValueMap',  {'map': [{VAL_IKKE: VAL_IKKE}, {VAL_UDTAGET: VAL_UDTAGET}]}),
    ('Vol.lgd',     QVariant.Double,  'Volumen lgd',     'TextEdit',  {}),
    ('Udtaget',     QVariant.String,  'Udtaget',         'TextEdit',  {}),
    ('Tørv. Ty.',   QVariant.Double,  'Tørvetykkelse',   'TextEdit',  {}),
    ('Perm.',       QVariant.Double,  'Permeabilitet',   'TextEdit',  {}),
    ('VSP',         QVariant.Double,  'Vandspejl',       'TextEdit',  {}),
    ('Foto',        QVariant.String,  'Foto af prøve',   'ExternalResource', {'StorageType': '0', 'DocumentViewer': '0', 'FileWidget': '1', 'FileWidgetButton': '1'}),
    ('lag 1',       QVariant.String,  'Lag 1 (cm)',      'TextEdit',  {}),
    ('lag 1 type',  QVariant.String,  'Lag 1 jordtype',  'ValueMap',  {'map': [{v: v} for v in JORDTYPE_VALG]}),
    ('lag 2',       QVariant.String,  'Lag 2 (cm)',      'TextEdit',  {}),
    ('lag 2 type',  QVariant.String,  'Lag 2 jordtype',  'ValueMap',  {'map': [{v: v} for v in JORDTYPE_VALG]}),
    ('lag 3',       QVariant.String,  'Lag 3 (cm)',      'TextEdit',  {}),
    ('lag 3 type',  QVariant.String,  'Lag 3 jordtype',  'ValueMap',  {'map': [{v: v} for v in JORDTYPE_VALG]}),
    ('lag 4',       QVariant.String,  'Lag 4 (cm)',      'TextEdit',  {}),
    ('lag 4 type',  QVariant.String,  'Lag 4 jordtype',  'ValueMap',  {'map': [{v: v} for v in JORDTYPE_VALG]}),
    ('comment',     QVariant.String,  'Kommentar',       'TextEdit',  {}),
]


class KlargorQFieldDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self._populate_lag()
        self.btnKor.clicked.connect(self.kor)

    def _populate_lag(self):
        self.cboLag.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == layer.VectorLayer:
                if layer.geometryType() in (QgsWkbTypes.PolygonGeometry, QgsWkbTypes.PointGeometry):
                    self.cboLag.addItem(layer.name(), layer.id())

    def kor(self):
        layer_id = self.cboLag.currentData()
        if not layer_id:
            QMessageBox.warning(self, 'Fejl', 'Vælg et lag.')
            return

        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            QMessageBox.warning(self, 'Fejl', 'Laget kunne ikke findes.')
            return

        existing = [f.name() for f in layer.fields()]

        # Tilføj manglende felter
        new_fields = []
        for name, vtype, alias, _, _ in FIELDS:
            if name not in existing:
                f = QgsField(name, vtype)
                f.setAlias(alias)
                new_fields.append(f)

        if new_fields:
            layer.startEditing()
            for f in new_fields:
                layer.addAttribute(f)
            layer.commitChanges()

        # Sæt default + udfyld eksisterende features for status-feltet
        status_idx = layer.fields().indexOf(STATUS_FIELD)
        if status_idx >= 0:
            layer.setDefaultValueDefinition(status_idx, QgsDefaultValue(f"'{VAL_IKKE}'"))
            layer.startEditing()
            for feat in layer.getFeatures():
                if not feat[STATUS_FIELD]:
                    layer.changeAttributeValue(feat.id(), status_idx, VAL_IKKE)
            layer.commitChanges()

        # Sæt aliaser og widgets på alle felter
        for name, _, alias, widget_type, widget_config in FIELDS:
            idx = layer.fields().indexOf(name)
            if idx < 0:
                continue
            layer.setFieldAlias(idx, alias)
            layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup(widget_type, widget_config))

        # Farverenderer baseret på status
        self._apply_renderer(layer)

        layer.triggerRepaint()
        QgsProject.instance().setDirty(True)

        added = len(new_fields)
        QMessageBox.information(
            self, 'Klargøring færdig',
            f'"{layer.name()}" er nu klar til QField.\n'
            f'{added} nye felter tilføjet.'
        )
        self.accept()

    def _apply_renderer(self, layer):
        geom_type = layer.geometryType()
        if geom_type == QgsWkbTypes.PolygonGeometry:
            sym_ikke = QgsFillSymbol.createSimple({'color': '#e74c3c', 'outline_color': '#922b21', 'outline_width': '0.4'})
            sym_udtaget = QgsFillSymbol.createSimple({'color': '#2ecc71', 'outline_color': '#1a7a43', 'outline_width': '0.4'})
        else:
            sym_ikke = QgsMarkerSymbol.createSimple({'color': '#e74c3c', 'outline_color': '#922b21', 'size': '3'})
            sym_udtaget = QgsMarkerSymbol.createSimple({'color': '#2ecc71', 'outline_color': '#1a7a43', 'size': '3'})

        categories = [
            QgsRendererCategory(VAL_IKKE, sym_ikke, VAL_IKKE),
            QgsRendererCategory(VAL_UDTAGET, sym_udtaget, VAL_UDTAGET),
        ]
        layer.setRenderer(QgsCategorizedSymbolRenderer(STATUS_FIELD, categories))
