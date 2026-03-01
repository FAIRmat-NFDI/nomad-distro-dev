"""
Parser for spectroscopy experiment manifest files.

Reads three coordinated CSV files:
1. exp_XXX_manifest.csv - Defines experiment steps with mixture compositions
2. exp_XXX_metadata.csv - Contains metadata like run_id and chemical names
3. scan_XXX_stepN.csv - IR spectra files referenced in the manifest

Creates an ExperimentRun entry with nested ExperimentSteps and SpectrumData.
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


class ManifestParser(MatchingParser):
    """
    Parser for spectroscopy experiment manifest files.
    
    Reads a manifest CSV that references spectrum files and metadata,
    creating a complete ExperimentRun structure.
    """

    def parse(
        self,
        mainfile: str,
        archive: 'EntryArchive',
        logger,
    ) -> None:
        """
        Parse experiment manifest and create ExperimentRun structure.
        
        Args:
            mainfile: Path to the manifest CSV file
            archive: The entry archive to populate
            logger: Structlog logger
        """
        try:
            mainfile_path = Path(mainfile)
            
            # Extract run_id from filename (exp_XXXXXXXX_manifest.csv)
            filename_stem = mainfile_path.stem
            if filename_stem.endswith('_manifest'):
                run_id = filename_stem.replace('_manifest', '')
            else:
                run_id = filename_stem
            
            # Read manifest CSV
            manifest_df = pd.read_csv(mainfile)
            
            if logger:
                logger.info(f"Parsing manifest for run: {run_id}, found {len(manifest_df)} rows")
            
            # Create ExperimentRun
            experiment = ExperimentRun()
            experiment.name = run_id
            
            # Try to read and parse metadata file
            metadata_file = mainfile_path.parent / f"{run_id}_metadata.csv"
            if metadata_file.exists():
                experiment.metadata = self._parse_metadata(metadata_file, logger)
            
            # Parse each step from manifest
            steps = []
            for idx, row in manifest_df.iterrows():
                try:
                    step = self._parse_manifest_row(row, mainfile_path.parent, logger)
                    if step:
                        steps.append(step)
                        if logger:
                            logger.info(f"Created step {idx}, step_number={step.step}")
                    else:
                        if logger:
                            logger.warning(f"Step {idx} returned None")
                except Exception as e:
                    if logger:
                        logger.error(f"Error parsing step {idx}: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
            
            # Assign all steps to experiment as a list
            experiment.steps = steps
            
            archive.data = experiment
            
            if logger:
                logger.info(f"Successfully parsed experiment with {len(experiment.steps)} steps")
        
        except Exception as e:
            if logger:
                logger.error(f"Error parsing manifest: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            # Create empty experiment
            archive.data = ExperimentRun()
    
    def _parse_metadata(self, metadata_file: Path, logger) -> ExperimentMetadata:
        """
        Parse metadata CSV file.
        
        Expected format:
            field,value
            run_id,20251205T151400Z
            n_chemicals,4
            n_mixtures,260
            chemical_0_name,LiPF6_pure
            chemical_1_name,EC_pure
            ...
        """
        try:
            metadata_df = pd.read_csv(metadata_file)
            metadata = ExperimentMetadata()
            
            # Convert dataframe to dict
            meta_dict = dict(zip(metadata_df['field'], metadata_df['value']))
            
            metadata.run_id = meta_dict.get('run_id', '')
            
            # Parse n_chemicals and n_mixtures
            try:
                metadata.n_chemicals = int(meta_dict.get('n_chemicals', 0))
            except (ValueError, TypeError):
                metadata.n_chemicals = 0
            
            try:
                metadata.n_mixtures = int(meta_dict.get('n_mixtures', 0))
            except (ValueError, TypeError):
                metadata.n_mixtures = 0
            
            # Parse chemical information
            chemicals = []
            for i in range(metadata.n_chemicals):
                key = f'chemical_{i}_name'
                if key in meta_dict:
                    chem = ChemicalInformation()
                    chem.index = i
                    chem.name = str(meta_dict[key])
                    chemicals.append(chem)
            
            metadata.chemicals = chemicals
            
            if logger:
                logger.info(f"Parsed metadata: {metadata.run_id}, {metadata.n_chemicals} chemicals")
            
            return metadata
        
        except Exception as e:
            if logger:
                logger.error(f"Error parsing metadata file: {str(e)}")
            return ExperimentMetadata()
    
    def _parse_manifest_row(
        self, row, data_dir: Path, logger
    ) -> ExperimentStep:
        """
        Parse a single row from the manifest CSV.
        """
        step = ExperimentStep()
        
        # Parse step metadata
        try:
            step.step = int(row.get('step', -1))
        except (ValueError, TypeError):
            step.step = -1
        
        step.timestamp = str(row.get('timestamp', ''))
        
        # Parse boolean field
        is_repeat_val = row.get('is_repeat', 'False')
        step.is_repeat = str(is_repeat_val).lower() == 'true'
        
        if logger:
            logger.info(f"Parsing step {step.step}, timestamp={step.timestamp}")
        
        # Parse repeat_of if it exists
        try:
            repeat_of = row.get('repeat_of', '')
            if repeat_of and str(repeat_of).strip() and str(repeat_of).lower() != 'nan':
                step.repeat_of = int(repeat_of)
        except (ValueError, TypeError):
            pass
        
        # Parse volume quantities
        try:
            step.volume_ecdec_stock_ul = float(row.get('V_ECDEC_stock_ul', 0))
        except (ValueError, TypeError):
            step.volume_ecdec_stock_ul = 0.0
        
        try:
            step.volume_lp40_stock_ul = float(row.get('V_LP40_stock_ul', 0))
        except (ValueError, TypeError):
            step.volume_lp40_stock_ul = 0.0
        
        try:
            step.volume_pes_in_lp40_stock_ul = float(
                row.get('V_PES_in_LP40_stock_ul', 0)
            )
        except (ValueError, TypeError):
            step.volume_pes_in_lp40_stock_ul = 0.0
        
        # Parse weight quantities
        try:
            step.weight_lipf6_pure = float(row.get('wt_LiPF6_pure', 0))
        except (ValueError, TypeError):
            step.weight_lipf6_pure = 0.0
        
        try:
            step.weight_ec_pure = float(row.get('wt_EC_pure', 0))
        except (ValueError, TypeError):
            step.weight_ec_pure = 0.0
        
        try:
            step.weight_dec_pure = float(row.get('wt_DEC_pure', 0))
        except (ValueError, TypeError):
            step.weight_dec_pure = 0.0
        
        try:
            step.weight_pes_pure = float(row.get('wt_PES_pure', 0))
        except (ValueError, TypeError):
            step.weight_pes_pure = 0.0
        
        # Parse associated spectrum file
        spectrum_filename = row.get('scan_filename', '')
        if spectrum_filename:
            spectrum_file = data_dir / str(spectrum_filename)
            if logger:
                logger.info(f"Looking for spectrum file: {spectrum_file}")
            if spectrum_file.exists():
                if logger:
                    logger.info(f"Found spectrum file, parsing it")
                try:
                    step.spectrum = self._parse_spectrum(spectrum_file, logger)
                    if logger:
                        logger.info(f"Successfully parsed spectrum")
                except Exception as e:
                    if logger:
                        logger.error(f"Error parsing spectrum {spectrum_filename}: {str(e)}")
            else:
                if logger:
                    logger.warning(f"Spectrum file not found: {spectrum_file}")
        else:
            if logger:
                logger.warning(f"No scan_filename in row")
        
        return step
    
    def _parse_spectrum(self, spectrum_file: Path, logger) -> SpectrumData:
        """
        Parse a spectrum CSV file and create SpectrumData section.
        """
        try:
            spectrum_df = pd.read_csv(spectrum_file)
            spectrum = SpectrumData()
            
            # Parse each row as a SpectrumPoint
            points = []
            for _, row in spectrum_df.iterrows():
                point = SpectrumPoint()
                
                # Try different column name variants for wavenumber
                wavenumber_found = False
                for wavenumber_col in [
                    'wavenumber_cm1',
                    'wavenumber_cm-1',
                    'wavenumber [cm-1]',
                    'wavenumber',
                    'Wavenumber',
                ]:
                    if wavenumber_col in spectrum_df.columns:
                        try:
                            wn_value = float(row[wavenumber_col])
                            point.wavenumber = ureg.Quantity(wn_value, '1/cm')
                            wavenumber_found = True
                        except (ValueError, TypeError) as e:
                            if logger:
                                logger.warning(
                                    f"Could not parse wavenumber: {row[wavenumber_col]}"
                                )
                        break
                
                # Try different column name variants for absorbance
                absorbance_found = False
                for absorbance_col in [
                    'absorbance',
                    'Absorbance',
                    'absorbance_au',
                    'absorbance [a.u.]',
                    'intensity',
                ]:
                    if absorbance_col in spectrum_df.columns:
                        try:
                            point.absorbance = float(row[absorbance_col])
                            absorbance_found = True
                        except (ValueError, TypeError):
                            if logger:
                                logger.warning(
                                    f"Could not parse absorbance: {row[absorbance_col]}"
                                )
                        break
                
                if wavenumber_found and absorbance_found:
                    points.append(point)
            
            spectrum.points = points
            
            # Set num_points manually after assigning points
            if spectrum.points:
                spectrum.num_points = len(spectrum.points)
            
            if logger:
                logger.info(f"Parsed spectrum with {len(points)} data points")
            
            return spectrum
        
        except Exception as e:
            if logger:
                logger.error(f"Error reading spectrum file: {str(e)}")
            return SpectrumData()
