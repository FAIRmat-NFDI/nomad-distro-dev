"""Tests for the advanced manifest parser."""

import logging
from pathlib import Path

from nomad.datamodel import EntryArchive

from nomad_plugin_spectroscopy.parsers.manifest_parser import ManifestParser


# Get path to test data directory
TEST_DATA_DIR = Path(__file__).parent.parent / 'data'


def test_parse_manifest():
    """Test parsing a complete experiment manifest with metadata and spectra."""
    parser = ManifestParser()
    archive = EntryArchive()
    manifest_file = str(TEST_DATA_DIR / 'exp_20251205T151400Z_manifest.csv')
    
    parser.parse(manifest_file, archive, logging.getLogger())
    
    # Verify ExperimentRun was created
    assert archive.data is not None
    assert archive.data.name == 'exp_20251205T151400Z'
    
    # Verify metadata was parsed
    assert archive.data.metadata is not None
    assert archive.data.metadata.run_id == '20251205T151400Z'
    assert archive.data.metadata.n_chemicals == 4
    assert archive.data.metadata.n_mixtures == 260
    
    # Verify chemicals
    assert len(archive.data.metadata.chemicals) == 4
    assert archive.data.metadata.chemicals[0].name == 'LiPF6_pure'
    assert archive.data.metadata.chemicals[1].name == 'EC_pure'
    assert archive.data.metadata.chemicals[2].name == 'DEC_pure'
    assert archive.data.metadata.chemicals[3].name == 'PES_pure'
    
    # Verify steps were parsed
    assert len(archive.data.steps) == 3
    
    # Check first step
    step0 = archive.data.steps[0]
    assert step0.step == 0
    assert step0.timestamp == '2025-12-05T16:15:59.837403'
    assert step0.is_repeat is False
    
    # Compare quantities (handle Quantity objects)
    vol_ecdec = step0.volume_ecdec_stock_ul
    if hasattr(vol_ecdec, 'magnitude'):
        assert abs(vol_ecdec.magnitude - 25.0) < 0.001
    else:
        assert vol_ecdec == 25.0
    
    vol_lp40 = step0.volume_lp40_stock_ul
    if hasattr(vol_lp40, 'magnitude'):
        assert abs(vol_lp40.magnitude - 0.0) < 0.001
    else:
        assert vol_lp40 == 0.0
    
    # Check that spectrum was loaded
    assert step0.spectrum is not None
    assert step0.spectrum.num_points == 1798
    assert step0.spectrum.points[0].wavenumber is not None
    assert step0.spectrum.points[0].absorbance is not None
    
    # Check second step
    step1 = archive.data.steps[1]
    assert step1.step == 1
    assert step1.timestamp == '2025-12-05T16:17:29.794492'
    
    # Check third step
    step2 = archive.data.steps[2]
    assert step2.step == 2
    assert step2.timestamp == '2025-12-05T16:18:59.683020'


def test_parse_experiment_step_with_spectrum():
    """Test that experiment steps correctly load associated spectrum files."""
    parser = ManifestParser()
    archive = EntryArchive()
    manifest_file = str(TEST_DATA_DIR / 'exp_20251205T151400Z_manifest.csv')
    
    parser.parse(manifest_file, archive, logging.getLogger())
    
    # Verify all steps have spectra
    for i, step in enumerate(archive.data.steps):
        assert step.spectrum is not None, f"Step {i} has no spectrum"
        assert len(step.spectrum.points) > 0, f"Step {i} spectrum has no points"
        
        # Check num_points (either from normalize or set explicitly)
        num_points = step.spectrum.num_points
        points_count = len(step.spectrum.points)
        if num_points is None:
            # normalize() hasn't been called yet, check length directly
            assert points_count > 0
        else:
            # normalize() was called, verify consistency
            assert num_points == points_count


def test_spectrum_data_quantities():
    """Test that spectrum data has correct units and values."""
    parser = ManifestParser()
    archive = EntryArchive()
    manifest_file = str(TEST_DATA_DIR / 'exp_20251205T151400Z_manifest.csv')
    
    parser.parse(manifest_file, archive, logging.getLogger())
    
    step = archive.data.steps[0]
    spectrum = step.spectrum
    
    # Check first point
    point0 = spectrum.points[0]
    assert point0.wavenumber is not None
    assert point0.absorbance == 0.006448
    
    # Check that wavenumber has correct unit
    wn = point0.wavenumber
    if hasattr(wn, 'magnitude'):
        assert abs(wn.magnitude - 650.4205) < 0.001
    else:
        assert abs(float(wn) - 650.4205) < 0.001


def test_experiment_composition_quantities():
    """Test that mixture composition quantities are parsed correctly."""
    parser = ManifestParser()
    archive = EntryArchive()
    manifest_file = str(TEST_DATA_DIR / 'exp_20251205T151400Z_manifest.csv')
    
    parser.parse(manifest_file, archive, logging.getLogger())
    
    step0 = archive.data.steps[0]
    
    # Helper function to extract magnitude from Quantity
    def get_magnitude(value):
        if hasattr(value, 'magnitude'):
            return value.magnitude
        return float(value) if value is not None else 0.0
    
    # All volume quantities should be parsed
    assert abs(get_magnitude(step0.volume_ecdec_stock_ul) - 25.0) < 0.001
    assert abs(get_magnitude(step0.volume_lp40_stock_ul) - 0.0) < 0.001
    assert abs(get_magnitude(step0.volume_pes_in_lp40_stock_ul) - 0.0) < 0.001
    
    # All weight quantities should be parsed
    assert abs(get_magnitude(step0.weight_lipf6_pure) - 0.0) < 0.001
    assert abs(get_magnitude(step0.weight_ec_pure) - 0.5764192139737991) < 0.0001
    assert abs(get_magnitude(step0.weight_dec_pure) - 0.42358078602620086) < 0.0001
    assert abs(get_magnitude(step0.weight_pes_pure) - 0.0) < 0.001
