def classFactory(iface):
    from .planet_sandbox_plugin import PlanetSandboxPlugin
    return PlanetSandboxPlugin(iface) 