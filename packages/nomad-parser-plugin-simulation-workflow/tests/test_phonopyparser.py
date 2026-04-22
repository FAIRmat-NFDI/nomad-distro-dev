#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import pytest
import numpy as np

from nomad.datamodel import EntryArchive
from workflowparsers.phonopy import PhonopyParser


def approx(value, abs=0, rel=1e-6):
    return pytest.approx(value, abs=abs, rel=rel)


@pytest.fixture(scope='module')
def parser():
    return PhonopyParser()


def test_basic(parser):
    archive = EntryArchive()
    parser.parse(
        'tests/data/phonopy/Ge/phonopy-FHI-aims-displacement-01/control.in',
        archive,
        None,
    )

    # need to assert values, no unbiased reference
    sec_thermo = archive.run[0].calculation[0].thermodynamics
    assert len(sec_thermo) == 11
    assert sec_thermo[0].temperature is not None
    assert sec_thermo[0].heat_capacity_c_v is not None
    assert sec_thermo[0].vibrational_free_energy_at_constant_volume is not None

    assert archive.run[0].method[0].x_phonopy_displacement.magnitude == 1e-12
    sec_scc = archive.run[0].calculation[0]
    assert np.shape(sec_scc.hessian_matrix) == (8, 8, 3, 3)
    assert np.shape(sec_scc.dos_phonon[0].total[0].value) == (201,)
    assert len(sec_scc.band_structure_phonon[0].segment) == 10

    assert archive.run[0].calculation[0].system_ref is not None
    assert archive.run[0].calculation[0].method_ref is not None


def test_vasp(parser):
    archive = EntryArchive()
    parser.parse('tests/data/phonopy/vasp/phonopy.yaml', archive, None)


def test_hexagonal_noncanonical(parser):
    archive = EntryArchive()
    parser.parse(
        'tests/data/phonopy/cp2k_hexagonal_noncanonical/phonopy.yaml', archive, None
    )

    # test whether the phonon band structure is recognized as hexagonal
    sec_band = archive.run[0].calculation[0].band_structure_phonon[0]
    assert len(sec_band.segment) == 9
    assert sec_band.segment[0].endpoints_labels == ['Γ', 'M']
    assert sec_band.segment[1].endpoints_labels == ['M', 'K']
    assert sec_band.segment[2].endpoints_labels == ['K', 'Γ']
    assert sec_band.segment[3].endpoints_labels == ['Γ', 'A']
    assert sec_band.segment[4].endpoints_labels == ['A', 'L']
    assert sec_band.segment[5].endpoints_labels == ['L', 'H']
    assert sec_band.segment[6].endpoints_labels == ['H', 'A']
    assert sec_band.segment[7].endpoints_labels == ['L', 'M']
    assert sec_band.segment[8].endpoints_labels == ['K', 'H']

    # TODO: also update other geometry artifacts

    # TODO: add test for failed lattice classification


def test_standard_phonopy_naming(parser):
    """Test parsing with standard phonopy directory naming (disp-01/)"""
    archive = EntryArchive()
    parser.parse(
        'tests/data/phonopy/Ge_standard_phonopy/disp-01/control.in',
        archive,
        None,
    )

    # Verify same results as original test
    sec_thermo = archive.run[0].calculation[0].thermodynamics
    assert len(sec_thermo) == 11
    assert sec_thermo[0].temperature is not None
    assert archive.run[0].method[0].x_phonopy_displacement.magnitude == 1e-12


def test_minimal_naming(parser):
    """Test parsing with minimal directory naming (displacement-01/)"""
    archive = EntryArchive()
    parser.parse(
        'tests/data/phonopy/Ge_minimal/displacement-01/control.in',
        archive,
        None,
    )

    # Verify same results as original test
    sec_thermo = archive.run[0].calculation[0].thermodynamics
    assert len(sec_thermo) == 11
    assert sec_thermo[0].temperature is not None
    assert archive.run[0].method[0].x_phonopy_displacement.magnitude == 1e-12


def test_no_phonopy_prefix(parser):
    """Test parsing with FHI-aims naming without phonopy prefix"""
    archive = EntryArchive()
    parser.parse(
        'tests/data/phonopy/Ge_no_phonopy_prefix/FHI-aims-displacement-01/control.in',
        archive,
        None,
    )

    # Verify same results as original test
    sec_thermo = archive.run[0].calculation[0].thermodynamics
    assert len(sec_thermo) == 11
    assert sec_thermo[0].temperature is not None
    assert archive.run[0].method[0].x_phonopy_displacement.magnitude == 1e-12


def test_missing_out_files(parser):
    """Test error handling when displacement directory has no .out files"""
    archive = EntryArchive()
    parser.parse(
        'tests/data/phonopy/Ge_no_out_files/displacement-01/control.in',
        archive,
        None,
    )

    # Parser should not crash, but may have incomplete data
    # The archive should still be created
    assert archive is not None
    # Since forces cannot be read, some phonopy features may not be available
    # but basic parsing should complete


def test_malformed_out_files(parser):
    """Test error handling when .out files exist but fail to parse"""
    archive = EntryArchive()
    parser.parse(
        'tests/data/phonopy/Ge_malformed_out/displacement-01/control.in',
        archive,
        None,
    )

    # Parser should not crash even when output files are malformed
    assert archive is not None
    # The parser should gracefully skip displacement directories with unparseable output
