from nomad.config.models.plugins import ParserEntryPoint


class ManifestParserEntryPoint(ParserEntryPoint):
    """Entry point for the Spectroscopy Manifest parser."""

    def load(self):
        from nomad_plugin_spectroscopy.parsers.manifest_parser import ManifestParser

        return ManifestParser(**self.dict())


class SpectrumParserEntryPoint(ParserEntryPoint):
    """Entry point for the Spectrum CSV parser."""

    def load(self):
        from nomad_plugin_spectroscopy.parsers.spectrum_parser import SpectrumParser

        return SpectrumParser(**self.dict())


manifest_parser = ManifestParserEntryPoint(
    name='SpectroscopyManifestParser',
    description='Parser for spectroscopy experiment manifest CSV files with step definitions.',
    mainfile_name_re=r'.+_manifest\.csv',  # Match manifest files specifically
    mainfile_mime_re=r'text/csv',
)

spectrum_parser = SpectrumParserEntryPoint(
    name='SpectrumParser',
    description='Parser for IR spectroscopy CSV files with wavenumber and absorbance data.',
    mainfile_name_re=r'(scan_.*\.csv|spectrum_.*\.csv|step.*\.csv)',  # Match spectrum files
    mainfile_mime_re=r'text/csv',
)

