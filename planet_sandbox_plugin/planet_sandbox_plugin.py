import os
from qgis.PyQt.QtWidgets import QAction, QPushButton
from qgis.PyQt.QtGui import QIcon
from qgis.core import (QgsVectorLayer, QgsProject, QgsRasterLayer,
                      QgsMessageLog, Qgis)
import requests

class PlanetSandboxPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.wmts_layer = None
        self.vector_layer = None
        # Connect to project clear signal
        QgsProject.instance().cleared.connect(self.clear_layers)

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            'Load Sandbox',
            self.iface.mainWindow())
        
        # Connect the action to the run method
        self.action.triggered.connect(self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu('Planet Sandbox', self.action)
        
        # Connect to scale change signal
        self.iface.mapCanvas().scaleChanged.connect(self.check_scale)

    def unload(self):
        # Disconnect signals
        self.iface.mapCanvas().scaleChanged.disconnect(self.check_scale)
        QgsProject.instance().cleared.disconnect(self.clear_layers)
        
        # Remove the plugin menu item and icon
        self.iface.removePluginToMenu('Planet Sandbox', self.action)
        self.iface.removeToolBarIcon(self.action)
        
        # Clear layer references
        self.clear_layers()

    def clear_layers(self):
        """Reset layer references when project is cleared"""
        try:
            self.wmts_layer = None
            self.vector_layer = None
        except:
            pass

    def check_scale(self, scale):
        try:
            root = QgsProject.instance().layerTreeRoot()
            
            # Handle WMTS layer visibility
            if self.wmts_layer and self.wmts_layer.isValid():
                wmts_node = root.findLayer(self.wmts_layer.id())
                if wmts_node:
                    should_show = scale < 2375073
                    wmts_node.setItemVisibilityChecked(should_show)
            
            # Handle vector layer visibility - opposite logic
            if self.vector_layer and self.vector_layer.isValid():
                vector_node = root.findLayer(self.vector_layer.id())
                if vector_node:
                    should_show = scale >= 2375073
                    vector_node.setItemVisibilityChecked(should_show)
        except:
            pass

    def add_wmts_layer(self):
        # WMTS URL and parameters
        url = 'type=xyz&url=https://services.sentinel-hub.com/ogc/wmts/c2a920b7-6e18-4fa9-9878-96f47837cf6d?SERVICE%3DWMTS%26VERSION%3D1.0.0%26REQUEST%3DGetTile%26LAYER%3DSANDBOX-PLANET-BASEMAPS-TRUE-COLOUR%26STYLE%3Ddefault%26FORMAT%3Dimage%252Fpng%26TILEMATRIXSET%3DPopularWebMercator256%26TILEMATRIX%3D%7Bz%7D%26TILEROW%3D%7By%7D%26TILECOL%3D%7Bx%7D'
        
        # Add the XYZ layer
        layer = self.iface.addRasterLayer(url, "Planet Basemap", "wms")
        
        if not layer.isValid():
            self.iface.messageBar().pushCritical("Error", "Failed to load WMTS layer")
            QgsMessageLog.logMessage(f"Layer invalid: {layer.error().message()}", level=Qgis.Critical)
            return None

        # Store reference to layer
        self.wmts_layer = layer
        
        # Set initial visibility based on current scale
        self.check_scale(self.iface.mapCanvas().scale())
        
        return layer

    def run(self):
        # First add the WMTS layer
        wmts_layer = self.add_wmts_layer()
        if not wmts_layer:
            return
        
        # Then handle the GeoJSON
        url = "https://collections.sentinel-hub.com/planet-basemaps/polygons.geojson"
        
        try:
            # Download the GeoJSON
            response = requests.get(url)
            response.raise_for_status()
            
            # Save the GeoJSON to a temporary file
            temp_geojson = os.path.join(self.plugin_dir, 'temp_sandbox_data.geojson')
            with open(temp_geojson, 'w') as f:
                f.write(response.text)
            
            # Create and add the vector layer
            vector_layer = QgsVectorLayer(temp_geojson, "Planet Sandbox Data", "ogr")
            if vector_layer.isValid():
                QgsProject.instance().addMapLayer(vector_layer)
                self.vector_layer = vector_layer  # Store reference to vector layer
                # Set initial visibility based on current scale
                self.check_scale(self.iface.mapCanvas().scale())
                self.iface.messageBar().pushSuccess("Success", "GeoJSON data loaded successfully!")
            else:
                self.iface.messageBar().pushCritical("Error", "Failed to load the GeoJSON layer")
                
        except Exception as e:
            self.iface.messageBar().pushCritical("Error", f"Failed to download data: {str(e)}") 