from nomad.config.models.plugins import SchemaPackageEntryPoint


class SpectroscopyEntryPoint(SchemaPackageEntryPoint):
    """Entry point for the Spectroscopy schema package."""

    def load(self):
        from nomad_plugin_spectroscopy.schema_packages.spectroscopy import m_package

        return m_package


spectroscopy = SpectroscopyEntryPoint(
    name='Spectroscopy',
    description='Schema package for spectroscopy data (IR, Raman, UV-Vis, etc.)',
)

schema_package_entry_point = spectroscopy
