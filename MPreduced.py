
from typing import (
    TYPE_CHECKING,
)

from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.metainfo import (
    MEnum,
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)
from nomad_material_processing.general import (
    TimeSeries,
)
from nomad_material_processing.vapor_deposition.general import (
    EvaporationSource,
    SampleParameters,
    VaporDeposition,
    VaporDepositionSource,
    VaporDepositionStep,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

from typing import (
    TYPE_CHECKING,
)

from nomad.config import config
from nomad.datamodel.data import (
    ArchiveSection,
)
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import (
    ActivityStep,
    Component,
    Collection,
    CompositeSystemReference,
    Entity,
    PubChemPureSubstanceSection,
    PureSubstanceSection,
    PureSubstanceComponent,
    ReadableIdentifiers
)
from nomad.datamodel.metainfo.plot import (
    PlotSection,
)
from nomad.datamodel.metainfo.workflow import (
    Link,
    Task,
)
from nomad.metainfo import (
    MEnum,
    Quantity,
    SchemaPackage,
    Section,
    SubSection,
)
from nomad_material_processing.general import (
    Geometry,
    SampleDeposition,
    ThinFilmReference,
    ThinFilmStackReference,
    TimeSeries,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

from nomad.config import config


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

import numpy as np
from nomad.config import config
from nomad.datamodel.data import ArchiveSection, EntryData
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
    SectionProperties,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystem,
    CompositeSystemReference,
    ElementalComposition,
    Process,
    ProcessStep,
    SynthesisMethod,
    SystemComponent,
)
from nomad.datamodel.metainfo.workflow import (
    Link,
)
from nomad.metainfo import (
    MEnum,
    Quantity,
    Reference,
    SchemaPackage,
    Section,
    SectionProxy,
    SubSection,
)


class Geometry(ArchiveSection):
    volume = float()

class Parallelepiped(Geometry):
    height = float()
    width = float()
    length = float()
    alpha = float()
    beta = float()
    gamma = float()
    surface_area = float()

class SquareCuboid(Parallelepiped):
    height = float()
    width = float()
    length = float()
    alpha = float()
    beta = float()
    gamma = float()
    surface_area = float()

class RectangleCuboid(Parallelepiped):
    height = float()
    width = float()
    length = float()
    alpha = float()
    beta = float()
    gamma = float()
    surface_area = float()
    
class TruncatedCone(Geometry):
    height = float()
    lower_cap_radius = float()
    upper_cap_radius = float()
    lower_cap_surface_area = float()
    upper_cap_surface_area = float()
    lateral_surface_area = float()


class Cylinder(Geometry):
    height = float()
    radius = float()
    lower_cap_surface_area = float()
    cap_surface_area = float()
    lateral_surface_area = float()

class CylinderSector(Cylinder):
    central_angle = float()

class IrregularParallelSurfaces(Geometry):
    height = float()

class MillerIndices(ArchiveSection):
    h_index = float()
    k_index = float()
    l_index = float()

class BravaisMillerIndices(MillerIndices):
    i_index = float()

class CrystallographicDirection(ArchiveSection):
    hkl_reciprocal = MillerIndices()
    hkl_direct = MillerIndices()

class ProjectedMiscutOrientation(CrystallographicDirection):
    angle = float()
    angle_deviation = float()

class CartesianMiscut(ArchiveSection):
    reference_orientation = ProjectedMiscutOrientation()
    perpendicular_orientation = ProjectedMiscutOrientation()

class PolarMiscut(ArchiveSection):
    rho = float()
    theta = float()
    reference_orientation = ProjectedMiscutOrientation()

class Miscut(ArchiveSection):
    cartesian_miscut = CartesianMiscut()
    polar_miscut = PolarMiscut()
    directions_image = str()

class Dopant(ElementalComposition):
    doping_level = float()
    doping_deviation = float()

class CrystalProperties(ArchiveSection):
    pass

class SubstrateCrystalProperties(CrystalProperties):
    bravais_lattices = MEnum()
    surface_orientation = CrystallographicDirection()
    miscut = Miscut()

class ElectronicProperties(ArchiveSection):
    conductivity_type = MEnum()
    carrier_density = float()
    carrier_density_deviation = float()
    electrical_resistivity = float()


class Substrate(CompositeSystem):
    supplier = str()
    supplier_id = str()
    lab_id = str()
    image = str()
    information_sheet = str()
    
class CrystallineSubstrate(Substrate):
    geometry = Geometry()
    crystal_properties = SubstrateCrystalProperties()
    electronic_properties = ElectronicProperties()
    dopants = Dopant()

class ThinFilm(CompositeSystem):
    geometry = Geometry()

class ThinFilmReference(CompositeSystemReference):
    lab_id = str()
    reference = ThinFilm()

class SubstrateReference(CompositeSystemReference):
    lab_id = str()
    reference = Substrate()

class ThinFilmStack(CompositeSystem):
    layers = ThinFilmReference()
    substrate = SubstrateReference()

class ThinFilmStackReference(CompositeSystemReference):
    lab_id = str()
    reference = ThinFilmStack()

class SampleDeposition(SynthesisMethod):
    pass

class TimeSeries(ArchiveSection):
    value = float()
    set_value = float()
    time = float()
    set_time = float()

class Recipe(ArchiveSection):
    pass


class EtchingStep(ProcessStep):
    duration = float()
    temperature = float()
    agitation = MEnum()
    etching_reagents = CompositeSystemReference()


class Etching(Process, EntryData):
    tags = str()
    recipe = Recipe()
    steps = EtchingStep()


class EtchingRecipe(Etching, Recipe, EntryData):
    lab_id = str()

class AnnealingStep(ProcessStep):
    duration = float()
    starting_temperature = float()
    ending_temperature = float()

class Annealing(Process, EntryData):
    tags = str()
    recipe = Recipe()
    steps = AnnealingStep()

class AnnealingRecipe(Annealing, Recipe, EntryData):
    lab_id = str()

class CleaningStep(ProcessStep):
    duration = float()
    temperature = float()
    agitation = MEnum()
    cleaning_reagents = CompositeSystemReference()


class Cleaning(Process, EntryData):
    tags = str()
    recipe = Recipe()
    steps = CleaningStep()

class CleaningRecipe(Cleaning, Recipe, EntryData):
    lab_id = str()
    
class InsertReduction(Entity):
    name = str()
    lab_id = str()
    image = str()
    material = PubChemPureSubstanceSection()
    inner_geometry = Geometry()
    outer_geometry = Geometry()

class SubstrateHolderPosition(ArchiveSection):

    name = str()
    x_position = float()
    y_position = float()
    slot_geometry = Geometry()
    insert_reduction = InsertReduction()

class SubstrateHolder(Entity):
    name = str()
    lab_id = str()
    material = PubChemPureSubstanceSection()
    thickness = float()
    outer_diameter = float()
    number_of_positions = int()
    image = str()
    positions = SubstrateHolderPosition()

class FilledSubstrateHolderPosition(SubstrateHolderPosition):
    substrate = CompositeSystemReference()

class FilledSubstrateHolder(SubstrateHolder):
    substrate_holder = SubstrateHolder()
    positions = FilledSubstrateHolderPosition()

class MolarFlowRate(TimeSeries):
    measurement_type = MEnum()
    value = float()
    set_value = float()

class EvaporationSource(ArchiveSection):
    pass


class VaporDepositionSource(ArchiveSection):
    name = str()
    material = Component()
    vapor_source = EvaporationSource()
    vapor_molar_flow_rate = MolarFlowRate()



class GrowthRate(TimeSeries):
    measurement_type = MEnum()
    value = float()
    set_value = float()


class Temperature(TimeSeries):
    measurement_type = MEnum()
    value = float()
    set_value = float()

class SampleParameters(PlotSection, ArchiveSection):
    growth_rate = GrowthRate()
    substrate_temperature = Temperature()
    layer = ThinFilmReference()
    substrate = ThinFilmStackReference()

  
class Pressure(TimeSeries):
    measurement_type = MEnum()
    value = float()
    set_value = float()

class VolumetricFlowRate(TimeSeries):
    measurement_type = MEnum()
    value = float()
    set_value = float()
    

class GasFlow(ArchiveSection):
    gas = PureSubstanceSection()
    flow_rate = VolumetricFlowRate()

class SubstrateHeater(ArchiveSection):
    pass

class ChamberEnvironment(ArchiveSection):
    gas_flow = GasFlow()
    pressure = Pressure()
    heater = SubstrateHeater()

class VaporDepositionStep(ActivityStep):
    
    creates_new_thin_film = bool()
    duration = float()
    sources = VaporDepositionSource()
    sample_parameters = SampleParameters()
    environment = ChamberEnvironment()


class VaporDeposition(SampleDeposition):
    steps = VaporDepositionStep()


class SourcePower(TimeSeries):
    value = float()
    set_value = float()


class PVDEvaporationSource(EvaporationSource):
    power = SourcePower()


class ImpingingFlux(TimeSeries):
    
    measurement_type = MEnum()
    value = float()
    set_value = float()


class PVDSource(VaporDepositionSource):
    vapor_source = PVDEvaporationSource()
    impinging_flux = ImpingingFlux()

class PVDSampleParameters(SampleParameters):
    heater = MEnum()
    distance_to_source = float()


class PVDStep(VaporDepositionStep):
    sources = PVDSource()
    sample_parameters = PVDSampleParameters()

class PhysicalVaporDeposition(VaporDeposition):
    steps = PVDStep()

class SputterDeposition(PhysicalVaporDeposition):
    method = str()

class ThermalEvaporationHeaterTemperature(TimeSeries):
    value = float()
    set_value = float()

class ThermalEvaporationHeater(PVDEvaporationSource):
    temperature = ThermalEvaporationHeaterTemperature()

class ThermalEvaporationSource(PVDSource):
    vapor_source = ThermalEvaporationHeater()

class ThermalEvaporationStep(PVDStep):
    sources = ThermalEvaporationSource()

class ThermalEvaporation(PhysicalVaporDeposition):
    method = str()
    steps = ThermalEvaporationStep()


class PLDTarget(CompositeSystem):
    target_id = ReadableIdentifiers()
    

class PLDTargetComponent(SystemComponent):
    lab_id = str()
    system = PLDTarget()

class PLDLaser(PVDEvaporationSource):
    wavelength = float()
    repetition_rate = float()
    spot_size = float()
    pulses = int()

class PLDSource(PVDSource):
    material = PLDTargetComponent()
    vapor_source = PLDLaser()

class PLDStep(PVDStep):
    sources = PLDSource()

class PulsedLaserDeposition(PhysicalVaporDeposition):
    method = str()
    steps = PLDStep()

class ComponentConcentration(PureSubstanceComponent):
    theoretical_concentration = float()
    effective_concentration = float()


class PushPurgeGasFlow(GasFlow):
    push_flow_rate = VolumetricFlowRate()
    purge_flow_rate = VolumetricFlowRate()


class Rotation(TimeSeries):
    set_value = float()
    value = float()

    
class PartialVaporPressure(Pressure):
    value = float()
    set_value = float()
    time = float()

class BubblerMolarFlowRate(MolarFlowRate):
    pass


class CVDEvaporationSource(EvaporationSource):
    pressure = Pressure()
    precursor_partial_pressure = PartialVaporPressure()
    temperature = Temperature()
    total_flow_rate = VolumetricFlowRate()
    
class BubblerEvaporator(CVDEvaporationSource):
    carrier_gas = PureSubstanceSection()
    carrier_push_flow_rate = VolumetricFlowRate()
    carrier_purge_flow_rate = VolumetricFlowRate()
    dilution = float()
    source = float()
    inject = float()

class FlashEvaporator(CVDEvaporationSource):
    carrier_gas = PureSubstanceSection()
    carrier_push_flow_rate = VolumetricFlowRate()
    carrier_purge_flow_rate = VolumetricFlowRate()

class MistEvaporator(CVDEvaporationSource):
    pass

class GasLineEvaporator(CVDEvaporationSource):
    pass


class GasCylinderEvaporator(CVDEvaporationSource):
    dilution_in_cylinder = float()
    effective_flow_rate = VolumetricFlowRate()


class CVDSource(VaporDepositionSource):
    valve = bool()
    vapor_source = EvaporationSource()

class BubblerSource(CVDSource):
    vapor_source = BubblerEvaporator()

class GasLineSource(CVDSource):
    vapor_source = GasLineEvaporator()

class GasCylinderSource(CVDSource):
    vapor_source = GasCylinderEvaporator()

class FlashSource(CVDSource):
    vapor_source = FlashEvaporator()

class MistSource(CVDSource):
    item = str()
    stirring_time = float()
    description = str()
    vapor_source = MistEvaporator()
    material = ComponentConcentration()


class CVDStep(VaporDepositionStep):
    step_index = str()
    sources = CVDSource()
    sample_parameters = SampleParameters()


class ChemicalVaporDeposition(VaporDeposition):
    steps = CVDStep()

class FilamentTemperature(Temperature):
    value = float()
    set_value = float()

class MovpeSampleParameters(SampleParameters):
    filament_temperature = FilamentTemperature()

class MovpeChamberEnvironment(ChamberEnvironment):
    uniform_gas_flow_rate = VolumetricFlowRate()
    pressure = Pressure()
    throttle_valve = Pressure()
    rotation = Rotation()
    heater = SubstrateHeater()


class StepMovpe(CVDStep, PlotSection):
    sample_parameters = MovpeSampleParameters()
    sources = CVDSource()
    environment = MovpeChamberEnvironment()

class Movpe(ChemicalVaporDeposition, EntryData):
    method = str()
    steps = StepMovpe()

class CombinatorialLibrary(CompositeSystem, EntryData, PlotSection):
    pass

class CombinatorialSamplePosition(ArchiveSection):
    x = float()
    y = float()
    z = float()


class CombinatorialLibraryReference(CompositeSystemReference):
    reference = CombinatorialLibrary()

class CombinatorialSample(CompositeSystem, EntryData):
    sample_number = int()
    lab_id = str()
    library = CombinatorialLibraryReference()
    position = CombinatorialSamplePosition()


# Discrete combinatorial library classes:
class DiscreteCombinatorialSample(CompositeSystem):
    pass

class DiscreteCombinatorialSampleReference(CompositeSystemReference):
    sample_number = int()
    reference = DiscreteCombinatorialSample()

class DiscreteCombinatorialLibrary(Collection):
    lab_id = str()
    entities = DiscreteCombinatorialSampleReference()