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

from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np
import plotly.graph_objects as go

from nomad.datamodel.data import ArchiveSection, EntryData
from nomad.datamodel.metainfo.annotations import ELNAnnotation, SectionProperties
from nomad.datamodel.metainfo.basesections import Process
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import Package, Quantity, Section, SubSection

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='Spectroscopy Schema')


class SpectrumPoint(ArchiveSection):
    """
    A single point in a spectrum with wavenumber and absorbance.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    "wavenumber",
                    "absorbance",
                ],
            ),
        ),
    )

    wavenumber = Quantity(
        type=np.float64,
        description='Wavenumber in cm^-1',
        a_eln={
            "component": "NumberEditQuantity",
            "defaultDisplayUnit": "1/cm"
        },
        unit="1/cm",
    )

    absorbance = Quantity(
        type=np.float64,
        description='Absorbance (dimensionless)',
        a_eln={
            "component": "NumberEditQuantity",
        },
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalize the SpectrumPoint entry.

        Args:
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)


class ChemicalInformation(ArchiveSection):
    """
    Information about a chemical in the experiment.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    "index",
                    "name",
                ],
            ),
        ),
    )

    index = Quantity(
        type=int,
        description='Index of the chemical',
    )

    name = Quantity(
        type=str,
        description='Name of the chemical',
        a_eln={
            "component": "StringEditQuantity",
        },
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class ExperimentMetadata(ArchiveSection):
    """
    Metadata information for the spectroscopy experiment.
    Parsed from the metadata CSV file.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    "run_id",
                    "n_chemicals",
                    "n_mixtures",
                    "chemicals",
                ],
            ),
        ),
    )

    run_id = Quantity(
        type=str,
        description='Unique identifier for the experiment run',
        a_eln={
            "component": "StringEditQuantity",
        },
    )

    n_chemicals = Quantity(
        type=int,
        description='Number of chemicals used in the experiment',
        a_eln={
            "component": "NumberEditQuantity",
        },
    )

    n_mixtures = Quantity(
        type=int,
        description='Number of mixture samples created',
        a_eln={
            "component": "NumberEditQuantity",
        },
    )

    chemicals = SubSection(
        section_def=ChemicalInformation,
        repeats=True,
        description='List of chemicals used',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class SpectrumData(PlotSection, ArchiveSection):
    """
    IR Spectroscopy data containing wavenumber and absorbance measurements.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    "num_points",
                    "points",
                ],
            ),
        ),
    )

    num_points = Quantity(
        type=int,
        description='Number of data points in the spectrum',
        a_eln={
            "component": "NumberEditQuantity",
        },
    )

    points = SubSection(
        section_def=SpectrumPoint,
        repeats=True,
        description='Individual spectral data points',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalize the SpectrumData entry and generate plots.

        Args:
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        
        # Set num_points based on actual points
        if self.points:
            self.num_points = len(self.points)
            
            # Extract wavenumber and absorbance values
            wavenumbers = []
            absorbances = []
            
            for p in self.points:
                if p.wavenumber is not None:
                    wn = p.wavenumber
                    if hasattr(wn, 'magnitude'):
                        wn = wn.magnitude
                    wavenumbers.append(float(wn))
                
                if p.absorbance is not None:
                    ab = p.absorbance
                    if hasattr(ab, 'magnitude'):
                        ab = ab.magnitude
                    absorbances.append(float(ab))
            
            if wavenumbers and absorbances:
                # Create Plotly figure
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=wavenumbers,
                        y=absorbances,
                        name='Absorbance',
                        mode='lines',
                        line=dict(color='#2A4CDF', width=2),
                    ),
                )
                
                fig.update_layout(
                    title={'text': 'Spectrum', 'x': 0.5, 'xanchor': 'center'},
                    xaxis_title='Wavenumber (cm⁻¹)',
                    yaxis_title='Absorbance',
                    template='plotly_white',
                    dragmode='zoom',
                    hovermode='closest',
                    hoverlabel=dict(bgcolor='white'),
                    xaxis=dict(
                        fixedrange=False,
                        showline=True,
                        gridcolor='#EAEDFC',
                    ),
                    yaxis=dict(
                        fixedrange=False,
                        showline=True,
                        gridcolor='#EAEDFC',
                        tickfont=dict(color='#2A4CDF'),
                    ),
                    width=600,
                    height=400,
                )
                
                self.figures = [PlotlyFigure(label='Spectrum', figure=fig.to_plotly_json())]


class ExperimentStep(ArchiveSection):
    """
    A single step in the spectroscopy experiment.
    Represents one row from the manifest CSV with its associated spectrum.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    "step",
                    "timestamp",
                    "is_repeat",
                    "repeat_of",
                    "volume_ecdec_stock_ul",
                    "volume_lp40_stock_ul",
                    "volume_pes_in_lp40_stock_ul",
                    "weight_lipf6_pure",
                    "weight_ec_pure",
                    "weight_dec_pure",
                    "weight_pes_pure",
                    "spectrum",
                ],
            ),
        ),
    )

    step = Quantity(
        type=int,
        description='Step number in the experiment',
        a_eln={
            "component": "NumberEditQuantity",
        },
    )

    timestamp = Quantity(
        type=str,
        description='ISO format timestamp when the step was recorded',
        a_eln={
            "component": "StringEditQuantity",
        },
    )

    is_repeat = Quantity(
        type=bool,
        description='Whether this step is a repeat of a previous step',
        a_eln={
            "component": "BoolEditQuantity",
        },
    )

    repeat_of = Quantity(
        type=int,
        description='Step number that this step repeats (if is_repeat is True)',
        a_eln={
            "component": "NumberEditQuantity",
        },
    )

    volume_ecdec_stock_ul = Quantity(
        type=np.float64,
        description='Volume of EC:DEC stock added in microliters',
        a_eln={
            "component": "NumberEditQuantity",
            "defaultDisplayUnit": "microliter",
        },
        unit="microliter",
    )

    volume_lp40_stock_ul = Quantity(
        type=np.float64,
        description='Volume of LP40 stock added in microliters',
        a_eln={
            "component": "NumberEditQuantity",
            "defaultDisplayUnit": "microliter",
        },
        unit="microliter",
    )

    volume_pes_in_lp40_stock_ul = Quantity(
        type=np.float64,
        description='Volume of PES in LP40 stock added in microliters',
        a_eln={
            "component": "NumberEditQuantity",
            "defaultDisplayUnit": "microliter",
        },
        unit="microliter",
    )

    weight_lipf6_pure = Quantity(
        type=np.float64,
        description='Weight of LiPF6 pure in grams',
        a_eln={
            "component": "NumberEditQuantity",
            "defaultDisplayUnit": "gram",
        },
        unit="gram",
    )

    weight_ec_pure = Quantity(
        type=np.float64,
        description='Weight of EC pure in grams',
        a_eln={
            "component": "NumberEditQuantity",
            "defaultDisplayUnit": "gram",
        },
        unit="gram",
    )

    weight_dec_pure = Quantity(
        type=np.float64,
        description='Weight of DEC pure in grams',
        a_eln={
            "component": "NumberEditQuantity",
            "defaultDisplayUnit": "gram",
        },
        unit="gram",
    )

    weight_pes_pure = Quantity(
        type=np.float64,
        description='Weight of PES pure in grams',
        a_eln={
            "component": "NumberEditQuantity",
            "defaultDisplayUnit": "gram",
        },
        unit="gram",
    )

    spectrum = SubSection(
        section_def=SpectrumData,
        description='Spectroscopy data acquired at this step',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """Normalize the experiment step."""
        super().normalize(archive, logger)


class ExperimentRun(Process, EntryData, ArchiveSection):
    """
    Complete spectroscopy experiment run containing metadata and multiple steps.
    
    The main entry class that represents one complete spectroscopy experiment with:
    - Experiment metadata (run_id, chemicals, mixtures count)
    - Multiple experiment steps with associated IR spectra
    - Each step contains mixture composition and the resulting spectrum
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    "name",
                    "metadata",
                    "steps",
                ],
            ),
        ),
    )

    name = Quantity(
        type=str,
        description='Name of the experiment run',
        a_eln={
            "component": "StringEditQuantity",
        },
    )

    metadata = SubSection(
        section_def=ExperimentMetadata,
        description='Metadata information for the experiment',
    )

    steps = SubSection(
        section_def=ExperimentStep,
        repeats=True,
        description='Individual steps in the experiment, each containing a spectrum',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalize the ExperimentRun entry.

        Args:
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        # Don't call Process.normalize() as it expects steps to have to_task() method
        # Instead call EntryData and ArchiveSection normalize directly
        ArchiveSection.normalize(self, archive, logger)
        EntryData.normalize(self, archive, logger)


m_package.__init_metainfo__()
