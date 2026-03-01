import logging
from pathlib import Path

from nomad.datamodel import EntryArchive

from nomad_plugin_spectroscopy.parsers.spectrum_parser import SpectrumParser

# Get path to test data directory
TEST_DATA_DIR = Path(__file__).parent.parent / 'data'


def test_parse_spectrum_step000():
    """Test parsing an IR spectrum file - step 000."""
    parser = SpectrumParser()
    archive = EntryArchive()
    parser.parse(str(TEST_DATA_DIR / 'scan_20251205T151400Z_step000.csv'), archive, logging.getLogger())

    assert archive.data is not None
    assert archive.data.name == 'scan_20251205T151400Z_step000'


def test_parse_spectrum_step001():
    """Test parsing an IR spectrum file - step 001."""
    parser = SpectrumParser()
    archive = EntryArchive()
    parser.parse(str(TEST_DATA_DIR / 'scan_20251205T151400Z_step001.csv'), archive, logging.getLogger())

    assert archive.data is not None
    assert archive.data.name == 'scan_20251205T151400Z_step001'


def test_parse_spectrum_step002():
    """Test parsing an IR spectrum file - step 002."""
    parser = SpectrumParser()
    archive = EntryArchive()
    parser.parse(str(TEST_DATA_DIR / 'scan_20251205T151400Z_step002.csv'), archive, logging.getLogger())

    assert archive.data is not None
    assert archive.data.name == 'scan_20251205T151400Z_step002'
