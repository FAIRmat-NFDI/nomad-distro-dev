"""
Parser for IR spectroscopy CSV files.

"""

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive

from nomad.parsing import MatchingParser
from nomad.units import ureg

from nomad_plugin_spectroscopy.schema_packages.spectroscopy import (
    ChemicalInformation,
    ExperimentMetadata,
    ExperimentRun,
    ExperimentStep,
    SpectrumData,
    SpectrumPoint,
)


class SpectrumParser(MatchingParser):
    """
    Parser for spectroscopy files.
    
    Handles both:
    - Simple spectrum CSV files (wavenumber + absorbance)
    - Manifest-based experiments (manifest + metadata + spectrum files)
    """

    def parse(
        self,
        mainfile: str,
        archive: 'EntryArchive',
        logger,
    ) -> None:
        """
        Parse spectroscopy file(s) and populate the archive.
        
        Args:
            mainfile: Path to the CSV file
            archive: The entry archive to populate
            logger: Structlog logger
        """
        try:
            mainfile_path = Path(mainfile)
            
            # Check if this is a manifest file
            if '_manifest.csv' in mainfile:
                self._parse_manifest(mainfile_path, archive, logger)
            else:
                # Fall back to simple spectrum parsing
                self._parse_spectrum_simple(mainfile_path, archive, logger)
                
        except Exception as e:
            if logger:
                logger.error(f"Error parsing spectroscopy file: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            # Still create an empty ExperimentRun
            archive.data = ExperimentRun()

    def _parse_manifest(self, mainfile_path: Path, archive, logger) -> None:
        """
        Parse a manifest-based experiment with metadata and multiple steps.
        """
        parent_dir = mainfile_path.parent
        
        # Extract base name (e.g., "exp_20251205T151400Z" from "exp_20251205T151400Z_manifest.csv")
        manifest_name = mainfile_path.stem.rsplit('_', 1)[0]
        metadata_file = parent_dir / f'{manifest_name}_metadata.csv'
        
        # Create ExperimentRun
        exp_run = ExperimentRun()
        exp_run.name = manifest_name
        
        if logger:
            logger.info(f'Parsing manifest: {mainfile_path.name}')
            logger.info(f'Parent directory: {parent_dir}')
            logger.info(f'Manifest name: {manifest_name}')
        
        # Parse metadata file
        metadata = self._parse_metadata(metadata_file, logger)
        if metadata:
            exp_run.metadata = metadata
        else:
            if logger:
                logger.warning(f'No metadata found for {manifest_name}')
        
        # Parse manifest file and create steps
        manifest_df = pd.read_csv(mainfile_path)
        if logger:
            logger.info(f'Manifest has {len(manifest_df)} rows')
            logger.info(f'Manifest columns: {list(manifest_df.columns)}')
        
        steps = []
        
        for idx, (_, row) in enumerate(manifest_df.iterrows()):
            if logger:
                logger.info(f'Parsing step {idx}')
            step = self._parse_step(row, parent_dir, logger)
            if step:
                steps.append(step)
                if logger:
                    logger.info(f'Successfully parsed step {idx}')
            else:
                if logger:
                    logger.warning(f'Failed to parse step {idx}')
        
        exp_run.steps = steps
        archive.data = exp_run
        
        if logger:
            logger.info(f'Successfully parsed experiment {manifest_name} with {len(steps)} steps')

    def _parse_metadata(self, metadata_file: Path, logger) -> 'ExperimentMetadata':
        """
        Parse metadata CSV file.
        """
        if not metadata_file.exists():
            if logger:
                logger.warning(f'Metadata file not found: {metadata_file}')
            return None
        
        try:
            df = pd.read_csv(metadata_file)
            metadata = ExperimentMetadata()
            
            for _, row in df.iterrows():
                field = str(row.get('field', '')).strip()
                value = str(row.get('value', '')).strip()
                
                if field == 'run_id':
                    metadata.run_id = value
                elif field == 'n_chemicals':
                    metadata.n_chemicals = int(value)
                elif field == 'n_mixtures':
                    metadata.n_mixtures = int(value)
                elif field.startswith('chemical_') and field.endswith('_name'):
                    if metadata.chemicals is None:
                        metadata.chemicals = []
                    index = int(field.split('_')[1])
                    chem = ChemicalInformation()
                    chem.index = index
                    chem.name = value
                    metadata.chemicals.append(chem)
            
            return metadata
        except Exception as e:
            if logger:
                logger.warning(f'Error parsing metadata file {metadata_file}: {e}')
            return None

    def _parse_step(self, row, parent_dir: Path, logger) -> 'ExperimentStep':
        """
        Parse a single step from the manifest file.
        """
        try:
            step = ExperimentStep()
            
            # Parse basic step information
            if 'step' in row.index:
                step.step = int(row['step'])
            if 'timestamp' in row.index:
                step.timestamp = str(row['timestamp'])
            if 'is_repeat' in row.index:
                step.is_repeat = row['is_repeat'].lower() == 'true'
            if 'repeat_of' in row.index:
                val = row['repeat_of']
                if pd.notna(val) and str(val).strip():
                    step.repeat_of = int(val)
            
            # Parse volume fields
            volume_fields = {
                'V_ECDEC_stock_ul': 'volume_ecdec_stock_ul',
                'V_LP40_stock_ul': 'volume_lp40_stock_ul',
                'V_PES_in_LP40_stock_ul': 'volume_pes_in_lp40_stock_ul',
            }
            for csv_col, attr in volume_fields.items():
                if csv_col in row.index and pd.notna(row[csv_col]):
                    try:
                        setattr(step, attr, ureg.Quantity(float(row[csv_col]), 'microliter'))
                    except (ValueError, TypeError):
                        if logger:
                            logger.warning(f'Could not parse {csv_col}: {row[csv_col]}')
            
            # Parse weight fields
            weight_fields = {
                'wt_LiPF6_pure': 'weight_lipf6_pure',
                'wt_EC_pure': 'weight_ec_pure',
                'wt_DEC_pure': 'weight_dec_pure',
                'wt_PES_pure': 'weight_pes_pure',
            }
            for csv_col, attr in weight_fields.items():
                if csv_col in row.index and pd.notna(row[csv_col]):
                    try:
                        setattr(step, attr, ureg.Quantity(float(row[csv_col]), 'gram'))
                    except (ValueError, TypeError):
                        if logger:
                            logger.warning(f'Could not parse {csv_col}: {row[csv_col]}')
            
            # Parse and attach spectrum data
            if 'scan_filename' in row.index:
                scan_filename = str(row['scan_filename']).strip()
                scan_file = parent_dir / scan_filename
                if logger:
                    logger.info(f'Looking for spectrum file: {scan_file}')
                    logger.info(f'File exists: {scan_file.exists()}')
                spectrum_data = self._parse_spectrum_data(scan_file, logger)
                if spectrum_data:
                    step.spectrum = spectrum_data
                    if logger:
                        logger.info(f'Successfully attached spectrum with {spectrum_data.num_points} points')
                else:
                    if logger:
                        logger.warning(f'Could not parse spectrum from {scan_filename}')
            else:
                if logger:
                    logger.warning('No scan_filename column found in manifest row')
            
            return step
            
        except Exception as e:
            if logger:
                logger.warning(f'Error parsing step: {e}')
            return None

    def _parse_spectrum_data(self, spectrum_file: Path, logger) -> 'SpectrumData':
        """
        Parse a spectrum CSV file into SpectrumData.
        """
        if not spectrum_file.exists():
            if logger:
                logger.warning(f'Spectrum file not found: {spectrum_file}')
                logger.warning(f'Searched in: {spectrum_file.parent}')
                logger.warning(f'Available files: {list(spectrum_file.parent.glob("*"))}'[:200])
            return None
        
        try:
            df = pd.read_csv(spectrum_file)
            spectrum = SpectrumData()
            spectrum.name = spectrum_file.stem
            
            if logger:
                logger.info(f'Successfully loaded spectrum file: {spectrum_file.name}')
                logger.info(f'Columns: {list(df.columns)}')
            points = []
            for _, row in df.iterrows():
                point = SpectrumPoint()
                
                # Parse wavenumber
                for wn_col in ['wavenumber_cm1', 'wavenumber_cm-1', 'wavenumber [cm-1]', 'wavenumber']:
                    if wn_col in df.columns:
                        try:
                            point.wavenumber = ureg.Quantity(float(row[wn_col]), '1/cm')
                            break
                        except (ValueError, TypeError):
                            pass
                
                # Parse absorbance
                for ab_col in ['absorbance', 'Absorbance', 'absorbance_au', 'absorbance [a.u.]', 'intensity']:
                    if ab_col in df.columns:
                        try:
                            point.absorbance = float(row[ab_col])
                            break
                        except (ValueError, TypeError):
                            pass
                
                if point.wavenumber is not None and point.absorbance is not None:
                    points.append(point)
            
            spectrum.points = points
            spectrum.num_points = len(points)
            
            return spectrum
            
        except Exception as e:
            if logger:
                logger.warning(f'Error parsing spectrum file {spectrum_file}: {e}')
            return None

    def _parse_spectrum_simple(self, mainfile_path: Path, archive, logger) -> None:
        """
        Parse a simple spectrum CSV file (fallback for non-manifest files).
        """
        df = pd.read_csv(mainfile_path)
        
        # Create simple spectrum data
        spectrum = SpectrumData()
        spectrum.name = mainfile_path.stem
        
        if logger:
            logger.info(f"Reading CSV with columns: {list(df.columns)}")
        
        # Parse each row as a SpectrumPoint
        points = []
        for _, row in df.iterrows():
            point = SpectrumPoint()
            
            # Try different column name variants for wavenumber
            wavenumber_found = False
            for wavenumber_col in ['wavenumber_cm1', 'wavenumber_cm-1', 'wavenumber [cm-1]', 'wavenumber', 'Wavenumber']:
                if wavenumber_col in df.columns:
                    try:
                        point.wavenumber = ureg.Quantity(float(row[wavenumber_col]), '1/cm')
                        wavenumber_found = True
                    except (ValueError, TypeError) as e:
                        if logger:
                            logger.warning(f"Could not parse wavenumber from {wavenumber_col}: {row[wavenumber_col]}, error: {e}")
                    break
            
            # Try different column name variants for absorbance
            absorbance_found = False
            for absorbance_col in ['absorbance', 'Absorbance', 'absorbance_au', 'absorbance [a.u.]', 'intensity']:
                if absorbance_col in df.columns:
                    try:
                        point.absorbance = float(row[absorbance_col])
                        absorbance_found = True
                    except (ValueError, TypeError) as e:
                        if logger:
                            logger.warning(f"Could not parse absorbance from {absorbance_col}: {row[absorbance_col]}, error: {e}")
                    break
            
            if point.wavenumber is not None and point.absorbance is not None:
                points.append(point)
        
        spectrum.points = points
        spectrum.num_points = len(points)
        archive.data = spectrum
        
        if logger:
            logger.info(f"Successfully parsed spectrum with {len(points)} data points")

