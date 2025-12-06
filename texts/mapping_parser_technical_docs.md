# MappingParser Technical Documentation

## Overview

The MappingParser is NOMAD's declarative framework for converting structured file data (XML, HDF5, text, JSON) into NOMAD archive entries. Instead of writing imperative parsing code with explicit loops and conditionals, you define mappings that describe how source data paths correspond to target schema locations, optionally applying transformations.

This documentation follows the Diataxis framework:
- **Tutorial**: Learning-oriented introduction to building your first parser
- **How-To Guides**: Task-oriented solutions for specific scenarios
- **Reference**: Information-oriented API documentation
- **Explanation**: Understanding-oriented conceptual discussion

---

# Tutorial: Your First MappingParser

This tutorial walks you through creating a simple parser from scratch, introducing core concepts progressively.

## Prerequisites

- Familiarity with NOMAD's metainfo system and archive structure
- Basic understanding of NOMAD's parsing pipeline
- Python 3.10+ with type hints

## Step 1: Understanding the Problem

Let's parse a simple XML output file from a fictional quantum chemistry code:

```xml
<calculation>
  <program>
    <name>FakeQM</name>
    <version>2.0.1</version>
  </program>
  <system>
    <atoms>
      <atom element="H" position="0.0 0.0 0.0"/>
      <atom element="O" position="1.0 0.0 0.0"/>
      <atom element="H" position="1.0 1.0 0.0"/>
    </atoms>
  </system>
  <energy units="eV">-123.456</energy>
</calculation>
```

We want to map this to NOMAD's schema structure.

## Step 2: Create a Basic Parser Class

```python
from nomad.parsing.file_parser.mapping_parser import XMLParser
from nomad.datamodel import EntryArchive

class FakeQMParser(XMLParser):
    """Parser for FakeQM XML output files."""

    def __init__(self):
        super().__init__(
            # Mapping annotation key for this file format
            annotation_key='fakeqm',
            # Don't remove XML attributes
            convert_dict=dict(remove_attributes=False)
        )
```

**Key Concepts Introduced:**
- Extend `XMLParser` for XML files (or `HDF5Parser`, `TextParser` for other formats)
- `annotation_key` identifies which mapping annotations to use from the schema
- `convert_dict` controls how the file is parsed into a Python dictionary

## Step 3: Define Schema Mappings with Annotations

Now we annotate the NOMAD schema to define how data flows from source to target:

```python
from nomad.datamodel.metainfo.simulation.program import Program
from nomad.datamodel.metainfo.simulation.system import ModelSystem
from nomad.parsing.file_parser.mapping_parser import MAPPING_ANNOTATION_KEY
from nomad_simulations.schema_packages.utils import add_mapping_annotation

# Map program name
add_mapping_annotation(
    Program.name,
    annotation_key='fakeqm',
    mapper='.calculation.program.name'
)

# Map program version
add_mapping_annotation(
    Program.version,
    annotation_key='fakeqm',
    mapper='.calculation.program.version'
)

# Map total energy
add_mapping_annotation(
    TotalEnergy.value,
    annotation_key='fakeqm',
    mapper='.calculation.energy.__value'
)
```

**Key Concepts Introduced:**
- `add_mapping_annotation` is a helper to attach mappers to schema properties
- Mapper strings use JMESPath-like syntax with dot notation
- `.__value` accesses the text content of an XML element
- Attributes are accessed with `@` prefix (e.g., `.calculation.energy.@units`)

## Step 4: Simple Path Mapping

The mapper string `.calculation.program.name` means:
1. Start at root of parsed dictionary
2. Navigate to `calculation` key
3. Then to `program` key
4. Finally to `name` key
5. Extract the value

For our XML, this extracts `"FakeQM"`.

## Step 5: Add Custom Transformation

Sometimes you need to transform data. Let's parse the atom positions:

```python
class FakeQMParser(XMLParser):
    """Parser for FakeQM XML output files."""

    def __init__(self):
        super().__init__(
            annotation_key='fakeqm',
            convert_dict=dict(remove_attributes=False)
        )

    def get_positions(self, source: list[dict]) -> np.ndarray:
        """Extract positions from atom list."""
        positions = []
        for atom in source:
            pos_str = atom['@position']
            positions.append([float(x) for x in pos_str.split()])
        return np.array(positions) * ureg.angstrom
```

Then annotate the schema:

```python
add_mapping_annotation(
    ModelSystem.atoms_state.positions,
    annotation_key='fakeqm',
    mapper=('get_positions', ['.calculation.system.atoms.atom'])
)
```

**Key Concepts Introduced:**
- Mapper can be a tuple: `(function_name, [source_paths])`
- Function name refers to a method on your parser class
- Method receives extracted source data and returns transformed data
- Return values can include pint units

## Step 6: Parse a File

```python
from nomad.datamodel import EntryArchive

# Create archive and parser
archive = EntryArchive()
parser = FakeQMParser()

# Parse file
parser.parse('path/to/output.xml', archive, logger)
```

The parser will:
1. Load and convert XML to dictionary
2. Find all annotated properties in the schema
3. Extract data using mapper paths
4. Apply transformations
5. Set values in the archive

## Step 7: Understanding the Data Flow

```
XML File
   ↓ [load_file()]
Dictionary {'calculation': {'program': {'name': 'FakeQM', ...}, ...}}
   ↓ [Path extraction via mapper string]
Extracted Data: "FakeQM"
   ↓ [Optional transformation via custom method]
Transformed Data: "FakeQM"
   ↓ [Set in archive]
archive.run[0].program.name = "FakeQM"
```

## Step 8: Next Steps

You now understand:
- How to create a parser class
- How to annotate schema properties with mappers
- How to write custom transformation methods
- The basic data flow from file to archive

The How-To Guides section covers more advanced scenarios like nested mappers, caching, and complex transformations.

---

# How-To Guides

Task-oriented guides for solving specific problems with MappingParser.

## How to Write Custom Transformer Methods

### Problem
You need to transform raw file data before storing it in the archive.

### Solution

**Step 1: Define the method in your parser class**

```python
class MyParser(XMLParser):
    def transform_energy(self, source: str) -> pint.Quantity:
        """Convert energy string to quantity with units."""
        value = float(source)
        return value * ureg.eV
```

**Step 2: Reference it in the mapper annotation**

```python
add_mapping_annotation(
    TotalEnergy.value,
    annotation_key='myparser',
    mapper=('transform_energy', ['.output.energy'])
)
```

### Multiple Source Paths

Transformers can take multiple inputs:

```python
def combine_forces(self, atoms: list, forces: list) -> dict:
    """Combine atom labels with force vectors."""
    return {
        'labels': [a['@element'] for a in atoms],
        'vectors': np.array(forces) * ureg('eV/angstrom')
    }

# Mapper with multiple sources
mapper=('combine_forces', ['.atoms.atom', '.forces.force'])
```

### Best Practices

1. **Type hints**: Always use type hints for clarity
2. **Unit handling**: Return pint quantities when appropriate
3. **Error handling**: Wrap in try/except and return None on failure
4. **Static methods**: Use `@staticmethod` when transformation doesn't need parser state
5. **Naming**: Use descriptive names like `get_*`, `transform_*`, `parse_*`

---

## How to Use Nested Mappers

### Problem
You need to map a list of objects, where each object has multiple properties.

### Solution

Use nested mapper configuration with subsections:

```python
# Schema definition
class Atom(ArchiveSection):
    element = Quantity(type=str)
    position = Quantity(type=np.ndarray, shape=[3])

class System(ArchiveSection):
    atoms = SubSection(sub_section=Atom, repeats=True)

# Annotation
add_mapping_annotation(
    System.atoms,
    annotation_key='myparser',
    mapper='.system.atoms.atom'  # Maps to list of atom dicts
)

# Each atom property is automatically mapped
add_mapping_annotation(
    Atom.element,
    annotation_key='myparser',
    mapper='.@element'  # Relative path within each atom
)

add_mapping_annotation(
    Atom.position,
    annotation_key='myparser',
    mapper=('parse_position', ['.@position'])
)
```

**Key Points:**
- Parent mapper extracts the list
- Child mappers use relative paths (starting from each list item)
- Automatically iterates over all items

---

## How to Handle Conditional Mapping

### Problem
A value might be in different locations depending on file version or configuration.

### Solution

Use JMESPath filter expressions and the `||` operator:

```python
# Try multiple paths (first non-null wins)
mapper='.output.energy || .results.total_energy || .energy'

# Conditional selection with filters
mapper='.energies[?"@type"==\'total\'].value | [0]'

# Complex condition
mapper='.calculations[?converged==`true`][-1].energy'
```

### Fallback in Transformer

Alternatively, handle fallback in custom method:

```python
def get_energy(self, source: dict) -> float | None:
    """Get energy with fallback logic."""
    if 'output' in source and 'energy' in source['output']:
        return float(source['output']['energy'])
    elif 'results' in source:
        return float(source['results'].get('total_energy', 0.0))
    return None

# Simple mapper delegates to method
mapper=('get_energy', ['.@'])  # Pass entire dict
```

---

## How to Implement Caching for Expensive Transformations

### Problem
A transformation is computationally expensive and used multiple times.

### Solution

Enable caching with `cache=True`:

```python
add_mapping_annotation(
    property,
    annotation_key='myparser',
    mapper=('expensive_calculation', ['.data']),
    cache=True  # Enable caching
)
```

**How it works:**
1. First call: Method executes, result stored in `Mapper.__cache[function_name]`
2. Subsequent calls: Cached result returned immediately
3. Cache key: Function name string
4. Cache lifetime: Duration of parser instance

### When to Use Caching

✅ **Use caching when:**
- Transformation involves heavy computation (array operations, numerical methods)
- Same transformation used multiple times in mapper tree
- Transformation result is deterministic

❌ **Avoid caching when:**
- Transformation is trivial (simple type conversion)
- Result depends on external state or file system
- Memory usage of cached data is prohibitive

### Example: Expensive XC Functional Parsing

```python
def get_xc_functionals(self, source: str) -> list[dict]:
    """Parse XC functional string (expensive regex and lookups)."""
    # Complex parsing logic with database lookups
    functionals = []
    for component in parse_xc_string(source):
        libxc_id = lookup_libxc_mapping(component)  # Database query
        functionals.append({
            'name': component,
            'libxc_name': libxc_id
        })
    return functionals

# Enable caching - this might be used in multiple schema locations
add_mapping_annotation(
    XCFunctional.components,
    annotation_key='myparser',
    mapper=('get_xc_functionals', ['.xc_functional_name']),
    cache=True
)
```

---

## How to Parse Text Files with Regex

### Problem
You need to parse unstructured text output.

### Solution

Use `TextParser` with a mapping configuration:

```python
from nomad.parsing.file_parser.mapping_parser import TextParser

class MyTextParser(TextParser):
    def __init__(self):
        super().__init__(
            annotation_key='myparser',
            # Define regex patterns
            quantities={
                'program_version': {
                    're': r'Program Version:\s*(\S+)',
                    'dtype': str
                },
                'total_energy': {
                    're': r'Total Energy\s*=\s*([-\d.]+)\s*eV',
                    'dtype': float,
                    'unit': 'eV'
                },
                'forces': {
                    're': r'Force\s+(\d+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',
                    'dtype': float,
                    'repeats': True  # Match multiple times
                }
            }
        )
```

**Mapping to Schema:**

```python
add_mapping_annotation(
    Program.version,
    annotation_key='myparser',
    mapper='.program_version'  # Matches quantity key
)

add_mapping_annotation(
    TotalEnergy.value,
    annotation_key='myparser',
    mapper='.total_energy'
)

# For repeated matches, reference as list
add_mapping_annotation(
    Forces.value,
    annotation_key='myparser',
    mapper=('reshape_forces', ['.forces'])
)
```

---

## How to Work with HDF5 Files

### Problem
Parse HDF5 files with hierarchical datasets.

### Solution

Use `HDF5Parser`:

```python
from nomad.parsing.file_parser.mapping_parser import HDF5Parser

class MyHDF5Parser(HDF5Parser):
    def __init__(self):
        super().__init__(
            annotation_key='myhdf5'
        )
```

**HDF5 Path Syntax:**
- Datasets: `.group.subgroup.dataset`
- Attributes: `.group.dataset.@attribute`
- Array indexing: `.data[0]`, `.data[0:10]`, `.data[:, 0]`

**Example Annotations:**

```python
# Access dataset
add_mapping_annotation(
    Positions.value,
    annotation_key='myhdf5',
    mapper='.atoms.positions'  # Maps to HDF5 dataset /atoms/positions
)

# Access attribute
add_mapping_annotation(
    Program.version,
    annotation_key='myhdf5',
    mapper='.metadata.@version'  # Attribute 'version' of group 'metadata'
)

# Slice array
add_mapping_annotation(
    InitialEnergy.value,
    annotation_key='myhdf5',
    mapper='.trajectory.energies[0]'  # First element
)
```

---

## How to Handle Multiple File Formats

### Problem
Your code produces multiple output files (main output, XML metadata, binary trajectory).

### Solution

Create separate parsers with different annotation keys:

```python
# Main parser for primary output
class MainParser(TextParser):
    def __init__(self):
        super().__init__(annotation_key='main')

# Auxiliary XML parser
class MetadataParser(XMLParser):
    def __init__(self):
        super().__init__(annotation_key='metadata')

# Trajectory parser
class TrajectoryParser(HDF5Parser):
    def __init__(self):
        super().__init__(annotation_key='trajectory')
```

**Use different annotation keys in schema:**

```python
# Energy from main output
add_mapping_annotation(
    TotalEnergy.value,
    annotation_key='main',
    mapper='.total_energy'
)

# Version from XML metadata
add_mapping_annotation(
    Program.version,
    annotation_key='metadata',
    mapper='.metadata.version'
)

# Positions from trajectory
add_mapping_annotation(
    Trajectory.positions,
    annotation_key='trajectory',
    mapper='.positions'
)
```

**Parse all files:**

```python
def parse(self, mainfile: str, archive: EntryArchive, logger):
    # Parse main output
    main_parser = MainParser()
    main_parser.parse(mainfile, archive, logger)

    # Parse auxiliary files
    metadata_file = mainfile.replace('.out', '.xml')
    if os.path.exists(metadata_file):
        metadata_parser = MetadataParser()
        metadata_parser.parse(metadata_file, archive, logger)

    trajectory_file = mainfile.replace('.out', '.h5')
    if os.path.exists(trajectory_file):
        traj_parser = TrajectoryParser()
        traj_parser.parse(trajectory_file, archive, logger)
```

---

## How to Debug Mapper Issues

### Problem
Your mapper isn't extracting data correctly.

### Solution Strategies

**1. Inspect Parsed Dictionary**

```python
parser = MyParser()
parser.filepath = 'test.xml'
data = parser.data  # Lazy-loaded parsed dictionary
print(json.dumps(data, indent=2))  # See structure
```

**2. Test Path Extraction**

```python
from nomad.parsing.file_parser.mapping_parser import Path

# Create Path object
path = Path('.calculation.energy')

# Test extraction
result = path.get_data(data)
print(f"Extracted: {result}")
```

**3. Test JMESPath Queries**

```python
import jmespath

query = '.energies[?"@type"==\'total\'].value | [0]'
result = jmespath.search(query, data)
print(f"Query result: {result}")
```

**4. Add Logging in Transformers**

```python
def my_transformer(self, source):
    logger.debug(f"Transformer input: {source}")
    result = transform(source)
    logger.debug(f"Transformer output: {result}")
    return result
```

**5. Validate Annotation Registration**

```python
# Check if annotation exists
quantity = Program.version
annotations = quantity.m_annotations.get(MAPPING_ANNOTATION_KEY, {})
print(f"Registered mappers: {annotations}")
```

**6. Use the Test Framework**

```python
def test_my_mapper():
    parser = MyParser()
    parser.filepath = 'test_data/sample.xml'

    archive = EntryArchive()
    parser.parse('test_data/sample.xml', archive, logger)

    # Assert expected values
    assert archive.run[0].program.name == 'ExpectedName'
    assert archive.run[0].calculation[0].energy.total.value.magnitude == -123.456
```

---

## How to Optimize Parser Performance

### Problem
Parser is slow for large files.

### Solutions

**1. Use Caching for Repeated Transformations**

```python
add_mapping_annotation(
    property,
    annotation_key='myparser',
    mapper=('expensive_method', ['.data']),
    cache=True  # Cache result
)
```

**2. Minimize File Reads**

```python
# Bad: Multiple parsers reading same file
parser1.parse(file, archive, logger)
parser2.parse(file, archive, logger)

# Good: Single parser with shared data_object
parser = MyParser()
parser.filepath = file
data_obj = parser.data_object  # Loaded once
# Both use cached data_object
```

**3. Use Lazy Properties**

Don't load all data upfront; use properties that load on demand:

```python
@property
def expensive_data(self):
    if not hasattr(self, '_expensive_data'):
        self._expensive_data = self.compute_expensive()
    return self._expensive_data
```

**4. Optimize Regex Patterns**

```python
# Bad: Catastrophic backtracking
're': r'.*Energy.*=.*([-\d.]+).*'

# Good: Specific pattern
're': r'Energy\s*=\s*([-\d.]+)'
```

**5. Use Compiled Patterns**

```python
import re

class MyParser(TextParser):
    ENERGY_PATTERN = re.compile(r'Energy\s*=\s*([-\d.]+)')

    def get_energy(self, text: str) -> float:
        match = self.ENERGY_PATTERN.search(text)
        return float(match.group(1)) if match else None
```

---

# Reference

Complete API documentation for all MappingParser components.

## Core Classes

### `MappingParser`

**Location:** `nomad.parsing.file_parser.mapping_parser.MappingParser`

Abstract base class for all mapping parsers.

**Constructor Parameters:**
- `annotation_key` (str): Key to identify mapper annotations in schema
- `mapper` (BaseMapper, optional): Pre-built mapper tree
- `data` (dict, optional): Pre-loaded data dictionary
- `**kwargs`: Additional parser-specific arguments

**Properties:**
- `mapper`: BaseMapper - Lazy-loaded mapper tree (calls `build_mapper()` if needed)
- `data`: dict - Lazy-loaded parsed data dictionary (calls `to_dict()` if needed)
- `data_object`: Any - Lazy-loaded raw file object (calls `load_file()` if needed)
- `filepath`: str - Path to file being parsed (setter invalidates cached data)
- `open`: Callable - File open function (handles compression automatically)

**Abstract Methods to Implement:**

```python
def to_dict(self) -> dict:
    """Convert data_object to dictionary representation.

    Returns:
        Parsed data as nested dictionary
    """
    raise NotImplementedError

def from_dict(self, data: dict) -> Any:
    """Convert dictionary back to original format.

    Args:
        data: Dictionary representation

    Returns:
        Data in original format
    """
    raise NotImplementedError

def load_file(self) -> Any:
    """Load file from filepath.

    Returns:
        Raw file object/data structure
    """
    raise NotImplementedError
```

**Concrete Methods:**

```python
def parse(
    self,
    filepath: str,
    archive: EntryArchive,
    logger,
    **kwargs
) -> None:
    """Main parsing method. Loads file, applies mappers, populates archive.

    Args:
        filepath: Path to file to parse
        archive: EntryArchive to populate
        logger: Logger instance
        **kwargs: Additional arguments passed to transformers
    """
```

**Usage Example:**

```python
class MyParser(MappingParser):
    def __init__(self):
        super().__init__(annotation_key='myparser')

    def to_dict(self) -> dict:
        # Convert self.data_object to dict
        return dict(self.data_object)

    def from_dict(self, data: dict) -> Any:
        # Convert dict back to original
        return data

    def load_file(self) -> Any:
        # Load file
        with self.open(self.filepath) as f:
            return load_my_format(f)
```

---

### `XMLParser`

**Location:** `nomad.parsing.file_parser.mapping_parser.XMLParser`

Specialized parser for XML files, extends `MappingParser`.

**Constructor Parameters:**
- `annotation_key` (str): Annotation key for this format
- `convert_dict` (dict, optional): Options for XML to dict conversion
  - `remove_attributes` (bool): Convert attributes to sub-keys (default: True)
  - `remove_namespace` (bool): Strip XML namespaces (default: False)
  - Other xmltodict parameters

**Automatic Behaviors:**
- Loads XML using xmltodict
- Converts to dictionary representation
- Handles compressed XML (.xml.gz, .xml.bz2, .xml.xz)
- Attributes prefixed with `@` (e.g., `element.@attr`)
- Text content available as `.__value`

**Usage Example:**

```python
class MyXMLParser(XMLParser):
    def __init__(self):
        super().__init__(
            annotation_key='myxml',
            convert_dict=dict(
                remove_attributes=False,  # Keep @ prefix
                remove_namespace=True     # Strip ns0: prefixes
            )
        )
```

**Mapper Path Examples:**

```xml
<root>
  <energy units="eV">-123.456</energy>
  <atoms>
    <atom element="H" x="0" y="0" z="0"/>
  </atoms>
</root>
```

```python
# Access element text
'.root.energy.__value'  # → "-123.456"

# Access attribute
'.root.energy.@units'  # → "eV"

# Access nested attribute
'.root.atoms.atom.@element'  # → "H"

# Multiple atoms (list)
'.root.atoms.atom[0].@x'  # → "0"
```

---

### `HDF5Parser`

**Location:** `nomad.parsing.file_parser.mapping_parser.HDF5Parser`

Specialized parser for HDF5 files, extends `MappingParser`.

**Constructor Parameters:**
- `annotation_key` (str): Annotation key for this format

**Automatic Behaviors:**
- Loads HDF5 using h5py
- Converts to dictionary (groups → dicts, datasets → arrays)
- Attributes available with `@` prefix
- Supports array slicing in mapper paths

**HDF5 Structure Mapping:**

```python
# HDF5 structure:
# /group1/dataset1       (array of shape (10, 3))
# /group1/@attr1         (attribute)
# /metadata/version      (scalar dataset)

# Mapper paths:
'.group1.dataset1'           # → Full array (10, 3)
'.group1.dataset1[0]'        # → First row (3,)
'.group1.dataset1[:, 0]'     # → First column (10,)
'.group1.@attr1'             # → Attribute value
'.metadata.version'          # → Scalar value
```

**Usage Example:**

```python
class MyHDF5Parser(HDF5Parser):
    def __init__(self):
        super().__init__(annotation_key='myhdf5')

    def get_dataset_slice(self, source: np.ndarray) -> np.ndarray:
        """Custom slicing logic."""
        return source[::2, :]  # Every other row
```

---

### `TextParser`

**Location:** `nomad.parsing.file_parser.mapping_parser.TextParser`

Specialized parser for text files using regex patterns, extends `MappingParser`.

**Constructor Parameters:**
- `annotation_key` (str): Annotation key for this format
- `quantities` (dict, optional): Regex pattern definitions
- `**kwargs`: Additional arguments

**Quantities Dictionary Structure:**

```python
quantities = {
    'quantity_name': {
        're': r'pattern with (capture) groups',
        'dtype': type,              # int, float, str, bool
        'unit': 'unit_string',      # Optional pint unit
        'repeats': bool,            # Match multiple times (default: False)
        'convert': bool,            # Auto-convert dtype (default: True)
        'shape': tuple,             # Reshape array (optional)
    }
}
```

**Example:**

```python
class MyTextParser(TextParser):
    def __init__(self):
        super().__init__(
            annotation_key='mytext',
            quantities={
                'program_version': {
                    're': r'Version:\s*(\S+)',
                    'dtype': str
                },
                'energy': {
                    're': r'Energy\s*=\s*([-\d.]+)',
                    'dtype': float,
                    'unit': 'eV'
                },
                'lattice_vectors': {
                    're': r'Lattice:\s*([-\d.]+)\s*([-\d.]+)\s*([-\d.]+)',
                    'dtype': float,
                    'repeats': True,
                    'shape': (3, 3)
                }
            }
        )
```

**Mapper Paths:**
- Quantity names become dictionary keys
- Repeating patterns create lists
- Multi-capture groups create lists of tuples

```python
# Text content:
# Version: 2.0.1
# Energy = -123.456
# Lattice: 1.0 0.0 0.0
# Lattice: 0.0 1.0 0.0
# Lattice: 0.0 0.0 1.0

# Resulting dictionary:
{
    'program_version': '2.0.1',
    'energy': -123.456,  # Auto-converted to float with eV unit
    'lattice_vectors': [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
}

# Mapper paths:
'.program_version'     # → '2.0.1'
'.energy'              # → -123.456 eV
'.lattice_vectors'     # → Array (3, 3)
```

---

### `MetainfoParser`

**Location:** `nomad.parsing.file_parser.mapping_parser.MetainfoParser`

Specialized parser that builds mappers automatically from metainfo annotations, extends `MappingParser`.

**Constructor Parameters:**
- `annotation_key` (str): Annotation key to look for in metainfo
- `section` (Section, optional): Root section to build mapper from
- `**kwargs`: Additional arguments

**Automatic Behavior:**
- Recursively traverses section definitions
- Collects mapping annotations at each level
- Builds nested mapper tree automatically
- No need to manually construct mapper

**Usage Example:**

```python
from nomad.datamodel.metainfo.simulation import Simulation

class MyMetainfoParser(XMLParser, MetainfoParser):
    def __init__(self):
        super().__init__(
            annotation_key='myparser',
            section=Simulation  # Start from Simulation section
        )
```

**How It Works:**

1. Starts at `section` (e.g., `Simulation`)
2. Finds all quantities/subsections with annotations
3. Extracts mapper from `quantity.m_annotations[MAPPING_ANNOTATION_KEY][annotation_key]`
4. Recursively processes subsections
5. Builds nested `MetainfoMapper` tree

**Method:**

```python
def build_mapper(self) -> MetainfoMapper:
    """Build mapper from metainfo annotations.

    Returns:
        Constructed MetainfoMapper tree
    """
```

---

### `Path`

**Location:** `nomad.parsing.file_parser.mapping_parser.Path`

Represents a data extraction/setting path using JMESPath syntax.

**Constructor Parameters:**
- `path` (str): JMESPath expression
- `parent` (Path, optional): Parent path for relative resolution
- `path_parser` (PathParser, optional): Custom path parser

**Properties:**
- `path`: Original path string
- `parent`: Parent Path object
- `relative_path`: Path relative to parent
- `absolute_path`: Fully resolved absolute path
- `reduced_path`: Path with indexing removed
- `parser`: PathParser instance

**Methods:**

```python
def get_data(
    self,
    source: dict,
    parser: MappingParser = None,
    **kwargs
) -> Any:
    """Extract data from source using path.

    Args:
        source: Source data dictionary
        parser: Parser instance for context
        **kwargs: Additional arguments

    Returns:
        Extracted data value
    """

def set_data(
    self,
    target: dict,
    value: Any,
    parser: MappingParser = None
) -> None:
    """Set value in target dictionary at path.

    Args:
        target: Target data dictionary
        value: Value to set
        parser: Parser instance for context
    """
```

**JMESPath Syntax Support:**

```python
# Basic navigation
'.a.b.c'                 # Navigate nested dicts

# Array indexing
'.items[0]'              # First item
'.items[-1]'             # Last item
'.items[1:3]'            # Slice

# Filter expressions
'.items[?@.type==\'A\']' # Filter by attribute
'.items[?value>`10`]'    # Filter by comparison

# Projections
'.items[*].value'        # All values

# Pipes
'.items | [0]'           # First item via pipe

# Alternatives
'.a || .b'               # Fallback to .b if .a is null
```

**Usage Example:**

```python
from nomad.parsing.file_parser.mapping_parser import Path

# Create path
path = Path('.calculation.energies[?"@type"==\'total\'].value | [0]')

# Extract data
data = {'calculation': {'energies': [
    {'@type': 'kinetic', 'value': 100},
    {'@type': 'total', 'value': -123.456}
]}}

result = path.get_data(data)  # → -123.456
```

---

### `Data`

**Location:** `nomad.parsing.file_parser.mapping_parser.Data`

Wrapper combining `Path` with optional `Transformer`.

**Constructor Parameters:**
- `path` (str | Path): Source path
- `transformer` (Transformer, optional): Transformation to apply
- `parent` (Path, optional): Parent path context
- `path_parser` (PathParser, optional): Custom path parser

**Properties:**
- `path`: Path object
- `transformer`: Transformer object (or None)
- `parent`: Parent path
- `path_parser`: PathParser instance

**Methods:**

```python
def get_data(
    self,
    source: dict,
    parser: MappingParser = None,
    **kwargs
) -> Any:
    """Extract and optionally transform data.

    Args:
        source: Source data dictionary
        parser: Parser instance
        **kwargs: Arguments passed to transformer

    Returns:
        Extracted (and transformed) data
    """
```

**Usage Example:**

```python
from nomad.parsing.file_parser.mapping_parser import Data, Transformer

# Without transformer
data = Data(path='.energy')
value = data.get_data(source_dict)

# With transformer
data = Data(
    path='.energy',
    transformer=Transformer(function_name='convert_energy')
)
value = data.get_data(source_dict, parser=my_parser)
# Calls my_parser.convert_energy(extracted_value)
```

---

### `Transformer`

**Location:** `nomad.parsing.file_parser.mapping_parser.Transformer`

Represents a transformation function to apply to data.

**Constructor Parameters:**
- `function_name` (str): Name of method on parser instance
- `cache` (bool): Whether to cache results (default: False)

**Properties:**
- `function_name`: Method name string
- `cache`: Boolean cache flag

**Methods:**

```python
def get_data(
    self,
    source: Any,
    parser: MappingParser,
    **kwargs
) -> Any:
    """Apply transformation function.

    Args:
        source: Input data
        parser: Parser instance (provides the method)
        **kwargs: Additional arguments passed to method

    Returns:
        Transformed data
    """
```

**Method Resolution:**

```python
# Transformer looks up method on parser
method = getattr(parser, self.function_name, None)
if method:
    return method(source, **kwargs)
```

**Usage Example:**

```python
class MyParser(XMLParser):
    def my_transform(self, value: str) -> float:
        return float(value) * 2.0

# Create transformer
transformer = Transformer(function_name='my_transform', cache=True)

# Apply
result = transformer.get_data('123.456', parser=my_parser_instance)
# → 246.912
```

---

### `BaseMapper`

**Location:** `nomad.parsing.file_parser.mapping_parser.BaseMapper`

Abstract base class for all mappers.

**Constructor Parameters:**
- `source` (str | tuple | Data): Source data specification
- `target` (str | Path, optional): Target path in archive
- `indices` (list[int], optional): Filter by indices
- `order` (int): Processing order (default: 0)
- `remove` (bool): Remove from target after processing (default: False)
- `cache` (bool, optional): Enable result caching
- `all_paths` (list[Path]): Additional paths to extract

**Properties:**
- `source`: Data object for source extraction
- `target`: Path object for target location
- `indices`: Index filter list
- `order`: Processing order integer
- `remove`: Removal flag
- `cache`: Cache flag
- `all_paths`: List of Path objects

**Abstract Methods:**

```python
def get_data(
    self,
    source: dict,
    parser: MappingParser,
    **kwargs
) -> Any:
    """Extract and transform data.

    Args:
        source: Source data dictionary
        parser: Parser instance
        **kwargs: Additional arguments

    Returns:
        Processed data
    """
    raise NotImplementedError
```

**Class Method:**

```python
@classmethod
def from_dict(cls, mapper_dict: dict) -> BaseMapper:
    """Construct mapper from dictionary configuration.

    Args:
        mapper_dict: Mapper specification

    Returns:
        Constructed mapper instance
    """
```

**Usage Example:**

```python
# Dictionary specification
mapper_config = {
    'source': '.input.energy',
    'target': 'run.calculation.energy.total.value',
    'cache': True
}

# Construct mapper
mapper = BaseMapper.from_dict(mapper_config)
```

---

### `Mapper`

**Location:** `nomad.parsing.file_parser.mapping_parser.Mapper`

Concrete mapper supporting nested sub-mappers, extends `BaseMapper`.

**Additional Parameters:**
- `mappers` (list[BaseMapper]): List of sub-mappers

**Properties:**
- All `BaseMapper` properties
- `mappers`: List of nested mappers
- `__cache`: Internal cache dictionary (class-level)

**Methods:**

```python
def get_data(
    self,
    source: dict,
    parser: MappingParser,
    **kwargs
) -> Any:
    """Extract data using nested mappers.

    Processes source data through nested mapper hierarchy,
    applying transformations and building result structure.

    Args:
        source: Source data dictionary
        parser: Parser instance
        **kwargs: Additional arguments

    Returns:
        Extracted and transformed data
    """

def sort(self) -> None:
    """Sort nested mappers by processing order."""
```

**Nested Mapper Example:**

```python
from nomad.parsing.file_parser.mapping_parser import Mapper

# Parent mapper for list of atoms
parent_mapper = Mapper(
    source='.atoms.atom',
    mappers=[
        # Child mapper for element
        Mapper(source='.@element', target='element'),
        # Child mapper for position
        Mapper(
            source=('parse_position', ['.@position']),
            target='position'
        )
    ]
)

# Processes:
# 1. Extract list from '.atoms.atom'
# 2. For each item in list:
#    a. Extract '.@element' → 'element'
#    b. Call parse_position('.@position') → 'position'
# 3. Return list of {element: ..., position: ...} dicts
```

---

### `MetainfoMapper`

**Location:** `nomad.parsing.file_parser.mapping_parser.MetainfoMapper`

Specialized mapper for metainfo sections, extends `Mapper`.

**Additional Parameters:**
- `m_def` (Section, optional): Section definition this mapper corresponds to

**Properties:**
- All `Mapper` properties
- `m_def`: Section definition

**Usage:**

Only used internally by `MetainfoParser`. Not typically instantiated directly.

---

## Annotation System

### `MAPPING_ANNOTATION_KEY`

**Location:** `nomad.parsing.file_parser.mapping_parser.MAPPING_ANNOTATION_KEY`

Constant string `'mapping'` used as the key in `m_annotations` dictionary.

**Usage:**

```python
from nomad.parsing.file_parser.mapping_parser import MAPPING_ANNOTATION_KEY

# Access mapping annotations
property.m_annotations[MAPPING_ANNOTATION_KEY]
# → {'xml': MapperAnnotation(...), 'hdf5': MapperAnnotation(...)}
```

---

### `add_mapping_annotation`

**Location:** `nomad_simulations.schema_packages.utils.add_mapping_annotation`

Helper function to add mapping annotations to schema properties.

**Signature:**

```python
def add_mapping_annotation(
    property: Section | Quantity | SubSection,
    annotation_key: str,
    mapper: str | tuple[str, list[str]] | tuple[str, list[str], dict],
    update: bool = True,
    **kwargs
) -> None:
    """Add mapping annotation to schema property.

    Args:
        property: Schema property to annotate
        annotation_key: Format identifier (e.g., 'xml', 'hdf5')
        mapper: Mapper specification (path string or transformer tuple)
        update: Update existing annotation vs. replace (default: True)
        **kwargs: Additional mapper configuration (cache, order, etc.)
    """
```

**Mapper Specification Formats:**

```python
# 1. Simple path string
mapper='.energy.total'

# 2. Transformer tuple (function, args)
mapper=('my_transform', ['.energy'])

# 3. Transformer with kwargs
mapper=('my_transform', ['.energy', '.units'], {'factor': 2.0})
```

**Usage Examples:**

```python
from nomad_simulations.schema_packages.utils import add_mapping_annotation

# Simple path
add_mapping_annotation(
    Program.name,
    annotation_key='myparser',
    mapper='.program.name'
)

# With transformer
add_mapping_annotation(
    TotalEnergy.value,
    annotation_key='myparser',
    mapper=('convert_energy', ['.energy']),
    cache=True
)

# Multiple sources
add_mapping_annotation(
    Forces.value,
    annotation_key='myparser',
    mapper=('combine_forces', ['.atoms', '.forces'])
)

# Additional kwargs
add_mapping_annotation(
    calculation.energy,
    annotation_key='myparser',
    mapper='.energy',
    order=10  # Process after order 0 mappers
)
```

---

### `MapperAnnotation`

**Location:** `nomad.datamodel.metainfo.annotations.MapperAnnotation`

Pydantic model representing a mapper annotation.

**Fields:**
- `mapper` (str | tuple): Mapper specification

**Usage:**

```python
from nomad.datamodel.metainfo.annotations import MapperAnnotation

# Direct annotation
property.m_annotations[MAPPING_ANNOTATION_KEY] = {
    'myparser': MapperAnnotation(mapper='.energy')
}
```

---

## Mapper Configuration Dictionary Format

When using `BaseMapper.from_dict()` or configuring mappers programmatically:

```python
mapper_config = {
    # Source specification (required)
    'source': '.path.to.data',  # or tuple for transformer

    # Target path (optional, inferred from metainfo)
    'target': 'path.in.archive',

    # Transformation caching (optional)
    'cache': True,

    # Processing order (optional, default: 0)
    'order': 10,

    # Index filtering (optional)
    'indices': [0, 2, 4],  # Only process these indices

    # Remove after processing (optional, default: False)
    'remove': False,

    # Nested mappers (optional, for Mapper class)
    'mappers': [
        {'source': '.child.path1', 'target': 'field1'},
        {'source': '.child.path2', 'target': 'field2'}
    ]
}
```

---

## Path Syntax Reference

### Basic Navigation

```python
'.a'           # Root key 'a'
'.a.b'         # Nested: a → b
'.a.b.c'       # Deep nesting: a → b → c
```

### Array Access

```python
'.items[0]'      # First item
'.items[1]'      # Second item
'.items[-1]'     # Last item
'.items[1:3]'    # Slice: items 1-2
'.items[:5]'     # First 5 items
'.items[::2]'    # Every other item
```

### Filters

```python
# Equality
'.items[?"@type"==\'total\']'        # String comparison
'.items[?count==`10`]'               # Numeric comparison

# Comparison operators
'.items[?value>`100`]'               # Greater than
'.items[?value<`50`]'                # Less than
'.items[?value>=`0`]'                # Greater or equal
'.items[?value<=`1000`]'             # Less or equal
'.items[?value!=`0`]'                # Not equal

# Logical operators
'.items[?x>`0` && y<`100`]'          # AND
'.items[?x==`0` || y==`0`]'          # OR

# Existence checks
'.items[?name]'                      # Has 'name' field
```

### Projections

```python
'.items[*].name'           # All names from items
'.data[*].values[0]'       # First value from each data item
```

### Pipes

```python
'.items | [0]'                # Pipe to get first
'.items[?@.type==\'A\'] | [0]' # First matching item
```

### Alternatives (Fallbacks)

```python
'.energy || .total_energy'              # Try energy, fallback to total_energy
'.output.e || .results.e || `0.0`'      # Multiple fallbacks with default
```

### XML-Specific

```python
'.__value'         # Text content of element
'.@attribute'      # Attribute value
'.element.@attr'   # Attribute of nested element
```

### HDF5-Specific

```python
'.dataset'              # Full dataset
'.dataset[0]'           # First element
'.dataset[:, 0]'        # First column
'.group.@attribute'     # Attribute of group or dataset
```

---

## Caching System

### Cache Storage

**Location:** `Mapper.__cache` (line 661 in mapping_parser.py)

Class-level dictionary storing transformation results.

**Structure:**

```python
__cache: dict[str, Any] = {}
```

**Cache Key:** Function name string from `Transformer.function_name`

**Cache Value:** Result returned by the transformation method

### Cache Configuration

**Enable Caching:**

```python
# Via annotation
add_mapping_annotation(
    property,
    annotation_key='myparser',
    mapper=('my_method', ['.data']),
    cache=True  # Enable caching
)

# Via mapper dict
mapper_config = {
    'source': ('my_method', ['.data']),
    'cache': True
}

# Via Transformer
transformer = Transformer(function_name='my_method', cache=True)
```

### Cache Behavior

**Read Flow (line 709-710):**

```python
if mapper.source.transformer and mapper.source.transformer.cache:
    data = self.__cache.get(mapper.source.transformer.function_name)
```

**Write Flow (line 711-716):**

```python
if data is None:
    data = mapper.source.get_data(source_data, parser, **kwargs)
    if mapper.source.transformer and mapper.source.transformer.cache:
        self.__cache.setdefault(
            mapper.source.transformer.function_name, data
        )
```

**Transformer Result Cache (line 740-751):**

```python
value: list[Any] = []
if isinstance(mapper, Transformer) and mapper.cache:
    value = self.__cache.get(mapper.function_name, value)

if not value:
    # Compute value
    for n, d in enumerate(data if isinstance(data, list) else [data]):
        v = mapper.get_data(d, parser, **kwargs)
        if indices and n not in indices:
            continue
        if not is_not_value(v):
            value.append(v)
    # Cache result
    if value and mapper.cache and isinstance(mapper, Transformer):
        self.__cache.setdefault(mapper.function_name, value)
```

### Cache Lifetime

- **Scope:** Per `Mapper` instance
- **Duration:** Lifetime of the `Mapper` object
- **Invalidation:** No automatic invalidation; cache persists until object destroyed
- **Sharing:** All nested mappers share the same `__cache` dict

### Cache Invalidation

Property-based caches (lazy properties) are invalidated when `filepath` is set:

```python
@filepath.setter
def filepath(self, value: str):
    self._filepath = value
    self._data_object = None  # Clear cached file object
    self._data = None         # Clear cached parsed data
    self._open = None         # Clear cached open function
```

---

## Tree Structures

### Mapper Tree

**Root Storage:** `MappingParser._mapper` (BaseMapper instance)

**Nesting:** `Mapper.mappers` list contains child mappers

**Structure Example:**

```python
root_mapper = Mapper(
    source='.calculation',
    mappers=[
        Mapper(source='.program.name', target='program.name'),
        Mapper(source='.program.version', target='program.version'),
        Mapper(
            source='.system.atoms',
            mappers=[
                Mapper(source='.@element', target='element'),
                Mapper(source='.@position', target='position')
            ]
        )
    ]
)
```

**Tree Visualization:**

```
Mapper (root)
├── source: '.calculation'
├── mappers:
    ├── Mapper
    │   ├── source: '.program.name'
    │   └── target: 'program.name'
    ├── Mapper
    │   ├── source: '.program.version'
    │   └── target: 'program.version'
    └── Mapper
        ├── source: '.system.atoms'
        └── mappers:
            ├── Mapper
            │   ├── source: '.@element'
            │   └── target: 'element'
            └── Mapper
                ├── source: '.@position'
                └── target: 'position'
```

### Path Tree

**Parent-Child Relationships:** `Path.parent` links to parent `Path`

**Absolute Resolution:** Computed from parent chain

**Example:**

```python
parent = Path('.calculation')
child = Path('.energy', parent=parent)

print(child.relative_path)   # '.energy'
print(child.absolute_path)   # '.calculation.energy'
```

### TreeInterpreter State

**Traversal Stack:** Maintained during JMESPath evaluation

**Fields:**
- `stack`: List of visited nodes
- `nodes`: All nodes encountered
- `indices`: Index at each level
- `keys`: Keys accessed at each level

**Usage:** Internal to `Path` for complex queries

---

# Explanation

Understanding-oriented discussion of MappingParser concepts and architecture.

## Design Philosophy

The MappingParser embodies several key design principles:

### Declarative over Imperative

Traditional parsing code is imperative:

```python
# Imperative approach
def parse(file, archive):
    data = load_xml(file)
    archive.run[0].program.name = data['calculation']['program']['name']
    archive.run[0].program.version = data['calculation']['program']['version']

    for atom in data['calculation']['system']['atoms']['atom']:
        atom_obj = Atom()
        atom_obj.element = atom['@element']
        atom_obj.position = parse_position(atom['@position'])
        archive.run[0].system[0].atoms.append(atom_obj)
```

MappingParser uses declarative mappings:

```python
# Declarative approach
add_mapping_annotation(Program.name, 'myparser', '.calculation.program.name')
add_mapping_annotation(Program.version, 'myparser', '.calculation.program.version')
add_mapping_annotation(Atom.element, 'myparser', '.@element')
add_mapping_annotation(Atom.position, 'myparser', ('parse_position', ['.@position']))
```

**Benefits:**
- Separation of concerns: data structure vs. extraction logic
- Reusability: same mapper can apply to multiple files
- Maintainability: changes to schema require annotation updates, not code rewrites
- Testability: mapper logic is isolated and unit-testable

### Schema-Driven Parsing

Mappers are attached to schema definitions, not parsers. This inverts control:

**Traditional:** Parser knows about schema
```python
class Parser:
    def parse(self):
        self.archive.program.name = extract_name()
        self.archive.program.version = extract_version()
```

**MappingParser:** Schema knows about sources
```python
# Schema definition
class Program(ArchiveSection):
    name = Quantity(type=str)
    name.m_annotations['mapping'] = {'myparser': '.program.name'}

    version = Quantity(type=str)
    version.m_annotations['mapping'] = {'myparser': '.program.version'}
```

**Benefits:**
- Schema is self-documenting: annotations show data sources
- Multiple formats supported by single schema (different annotation keys)
- Parser implementation becomes generic: traverse annotated schema

### Composition over Inheritance

Mappers are composable building blocks:

```python
# Simple mapper
energy_mapper = Mapper(source='.energy', target='energy.total.value')

# Composed mapper with transformation
energy_mapper = Mapper(
    source=('convert_energy', ['.energy', '.units']),
    target='energy.total.value',
    cache=True
)

# Nested composition
calculation_mapper = Mapper(
    source='.calculation',
    mappers=[energy_mapper, system_mapper, forces_mapper]
)
```

**Benefits:**
- Building blocks: simple mappers combine to handle complexity
- Reusability: same mapper used in different contexts
- Extensibility: add new mapper types without modifying existing code

---

## Architecture Overview

### Layer Structure

```
┌─────────────────────────────────────────────────┐
│         Application Layer                       │
│  (Parser subclasses, custom transformers)       │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│         MappingParser Framework                  │
│  (MappingParser, XMLParser, HDF5Parser, etc.)   │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│         Mapper System                            │
│  (Mapper, BaseMapper, MetainfoMapper)           │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│         Path & Data Extraction                   │
│  (Path, Data, TreeInterpreter)                  │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│         File Handling                            │
│  (xmltodict, h5py, regex, compression)          │
└─────────────────────────────────────────────────┘
```

### Data Flow

**Parse Operation Flow:**

```
1. Load File
   ↓
   MappingParser.load_file()
   → Returns raw file object (ElementTree, h5py.File, string)

2. Convert to Dictionary
   ↓
   MappingParser.to_dict()
   → Returns nested dict representation

3. Build Mapper Tree
   ↓
   MappingParser.build_mapper() or MetainfoParser.build_mapper()
   → Returns BaseMapper tree structure

4. Traverse Schema
   ↓
   MetainfoParser walks section definitions
   → Collects annotated properties

5. Extract Source Data
   ↓
   For each annotation:
     Path.get_data(source_dict)
     → Extracts value using JMESPath

6. Apply Transformation
   ↓
   If transformer present:
     Transformer.get_data(extracted_value, parser)
     → Calls parser method, returns transformed value

7. Set in Archive
   ↓
   Set value at target path in archive
   → archive.run[0].property = value

8. Return
   ↓
   Populated EntryArchive
```

### Mapper Tree Construction

**MetainfoParser Automatic Construction:**

```python
# Given schema with annotations:
class Program(ArchiveSection):
    name = Quantity(type=str)
    name.m_annotations['mapping'] = {'xml': Mapper(mapper='.program.name')}

    version = Quantity(type=str)
    version.m_annotations['mapping'] = {'xml': Mapper(mapper='.program.version')}

class Calculation(ArchiveSection):
    program = SubSection(sub_section=Program)

# MetainfoParser builds:
MetainfoMapper(
    m_def=Calculation,
    mappers=[
        MetainfoMapper(
            m_def=Program,
            mappers=[
                Mapper(source='.program.name', target='program.name'),
                Mapper(source='.program.version', target='program.version')
            ]
        )
    ]
)
```

**Process:**
1. Start at root section (e.g., `Simulation`)
2. Iterate all quantities and subsections
3. Check for mapping annotation with matching key
4. Extract mapper specification
5. Recursively process subsections
6. Build nested `MetainfoMapper` tree

---

## Why Tree Structures?

### Problem: Complex Nested Data

Scientific output files are deeply nested:

```xml
<calculation>
  <system>
    <atoms>
      <atom element="H" position="0 0 0"/>
      <atom element="O" position="1 0 0"/>
      <atom element="H" position="1 1 0"/>
    </atoms>
  </system>
  <results>
    <energy type="total">-123.456</energy>
    <energy type="kinetic">45.678</energy>
    <forces>
      <force atom="0">0.1 0.2 0.3</force>
      <force atom="1">0.4 0.5 0.6</force>
      <force atom="2">0.7 0.8 0.9</force>
    </forces>
  </results>
</calculation>
```

Target archive is also nested:

```python
archive
└── run[0]
    ├── program
    │   ├── name
    │   └── version
    ├── system[0]
    │   └── atoms
    │       ├── [0]
    │       │   ├── element
    │       │   └── position
    │       ├── [1]
    │       └── [2]
    └── calculation[0]
        ├── energy
        │   └── total
        │       └── value
        └── forces
            └── value
```

### Solution: Mirrored Tree Structures

The mapper tree mirrors the structure of both source and target:

```
Mapper (root: '.calculation')
├── Mapper ('.system.atoms.atom')
│   ├── Mapper ('.@element' → 'element')
│   └── Mapper ('.@position' → 'position')
└── Mapper ('.results')
    ├── Mapper ('.energy[?@type=="total"]' → 'energy.total.value')
    └── Mapper ('.forces.force' → 'forces.value')
```

**Benefits:**
- Natural representation: structure matches problem domain
- Automatic iteration: parent mapper extracts list, children process each item
- Context preservation: child mappers have parent context
- Composability: subtrees can be reused

---

## Caching Mechanisms Deep Dive

### Why Caching?

Some transformations are expensive:

1. **Database lookups**: Mapping functional names to libxc IDs
2. **Heavy computation**: FFTs, matrix operations on large arrays
3. **File I/O**: Loading auxiliary data files
4. **Complex parsing**: Regex on large text blocks

If the same transformation is needed multiple times (e.g., XC functional used in multiple schema locations), recomputing wastes time.

### Cache Implementation

**Storage Location:** `Mapper.__cache` (line 661)

This is a **class-level dictionary**, meaning:
- Shared across all instances of `Mapper` (not instance-specific)
- Persists for lifetime of the class
- Accessible via name mangling: `_Mapper__cache`

**Why class-level?** Design choice for simplicity. Could be instance-level, but:
- Transformations typically pure functions (same input → same output)
- Class-level allows cache sharing across mapper instances
- Simpler implementation (no need to pass cache around)

**Trade-off:** Memory persists beyond single parse operation. For long-running processes parsing many files, cache could grow large. In practice, this hasn't been an issue because:
- Cache keys are function names (limited set)
- Parser instances are typically short-lived
- Cache provides significant speedup for complex parsers

### Cache Lookup

**Source Transformer Cache (lines 709-716):**

```python
if mapper.source.transformer and mapper.source.transformer.cache:
    data = self.__cache.get(mapper.source.transformer.function_name)
if data is None:
    data = mapper.source.get_data(source_data, parser, **kwargs)
    if mapper.source.transformer and mapper.source.transformer.cache:
        self.__cache.setdefault(
            mapper.source.transformer.function_name, data
        )
```

**Flow:**
1. Check if source has transformer with caching enabled
2. Attempt cache lookup using function name as key
3. If cache miss (`data is None`), execute transformation
4. Store result in cache with function name key

**Direct Transformer Cache (lines 740-751):**

```python
value: list[Any] = []
if isinstance(mapper, Transformer) and mapper.cache:
    value = self.__cache.get(mapper.function_name, value)

if not value:
    for n, d in enumerate(data if isinstance(data, list) else [data]):
        v = mapper.get_data(d, parser, **kwargs)
        if indices and n not in indices:
            continue
        if not is_not_value(v):
            value.append(v)
    if value and mapper.cache and isinstance(mapper, Transformer):
        self.__cache.setdefault(mapper.function_name, value)
```

**Flow:**
1. Initialize empty result list
2. If mapper is Transformer with caching, attempt cache lookup
3. If cache miss (empty list), execute mapper on all data items
4. Store result if non-empty and caching enabled

### Cache Key Design

**Key:** Function name string (e.g., `'get_xc_functionals'`)

**Why function name?**
- Unique identifier for the transformation
- Simple and readable
- No need to hash complex arguments

**Limitation:** Cannot cache different results for same function with different arguments. Example:

```python
def scale_value(self, value: float, factor: float) -> float:
    return value * factor

# Problem: Both use same function name as cache key
mapper1 = ('scale_value', ['.x'], {'factor': 2.0})  # Cache key: 'scale_value'
mapper2 = ('scale_value', ['.y'], {'factor': 3.0})  # Cache key: 'scale_value' (collision!)
```

**Solution:** Transformers should be deterministic and not depend on configuration. If you need different behavior, use different function names:

```python
def scale_by_two(self, value: float) -> float:
    return value * 2.0

def scale_by_three(self, value: float) -> float:
    return value * 3.0
```

Or don't cache parameterized transformations.

### Property-Level Caching

Separate from mapper caching, `MappingParser` uses property-based lazy initialization:

```python
@property
def data(self):
    """Lines 857-864"""
    if not self._data:
        try:
            self._data = self.to_dict()
        except Exception:
            pass
    return self._data

@property
def mapper(self) -> BaseMapper:
    """Lines 878-882"""
    if self._mapper is None:
        self._mapper = self.build_mapper()
    return self._mapper
```

**Behavior:**
- First access: Compute value, cache in instance attribute
- Subsequent access: Return cached value
- Invalidation: When `filepath` is set, caches are cleared

**Why separate from mapper cache?**
- Different scope: per-parser-instance vs. per-mapper-class
- Different purpose: avoid repeated file I/O vs. avoid repeated transformation
- Different lifetime: tied to parser instance vs. class existence

---

## JMESPath and TreeInterpreter

### Why JMESPath?

JMESPath is a query language for JSON (similar to XPath for XML). Example:

```json
{
  "people": [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25}
  ]
}
```

```python
# JMESPath query
'people[?age>`26`].name'
# Result: ["Alice"]
```

**Benefits for MappingParser:**
- Expressive: Handle complex queries without custom code
- Standard: Well-documented, familiar to many developers
- Powerful: Filters, projections, pipes, functions

### TreeInterpreter Extension

`TreeInterpreter` (lines 52-156) extends `jmespath.visitor.TreeInterpreter` to track traversal state:

```python
class TreeInterpreter(jmespath.visitor.TreeInterpreter):
    def __init__(self, options=None):
        self.stack = []           # Visited nodes
        self._current_node = None # Current node
        self.current_stack = None # Current stack state
        self._parent = None       # Parent node
        self.nodes = []           # All nodes
        self.indices = []         # Index at each level
        self._cache = []          # (Unused)
        self._parent_key = '__parent'
        super().__init__(options)
```

**Why extend?**

Standard JMESPath interpreter evaluates queries but doesn't preserve traversal context. MappingParser needs to know:
- Where in the tree are we? (`stack`)
- What indices were accessed? (`indices`)
- What keys were traversed? (implicit in stack)

This information enables:
1. **Relative path resolution**: Child mappers relative to parent context
2. **Debugging**: Understanding what path was actually taken
3. **Complex transformations**: Custom logic based on traversal state

**Visitor Methods:**

```python
def visit_field(self, node, data):
    """Track field access."""
    # ... implementation

def visit_index(self, node, data):
    """Track array indexing."""
    # ... implementation

def visit_slice(self, node, data):
    """Track array slicing."""
    # ... implementation
```

Each visitor method:
1. Updates traversal state (stack, indices, nodes)
2. Delegates to parent implementation
3. Returns result

### Path Resolution

`Path` uses `TreeInterpreter` to evaluate queries:

```python
def get_data(self, source: dict, parser=None, **kwargs) -> Any:
    # Use JMESPath to extract
    result = jmespath.search(self.absolute_path, source, options=...)
    return result
```

**Absolute Path Computation:**

```python
# Parent path
parent = Path('.calculation.results')

# Child path (relative)
child = Path('.energy', parent=parent)

# Absolute path computation
child.absolute_path  # → '.calculation.results.energy'
```

**Process:**
1. Traverse parent chain to root
2. Concatenate all paths
3. Simplify (remove redundant dots, etc.)
4. Return fully qualified path

---

## MetainfoParser: Annotation-Driven Mapping

### Motivation

Writing mapper trees manually is tedious:

```python
# Manual mapper construction
mapper = Mapper(
    source='.calculation',
    mappers=[
        Mapper(source='.program.name', target='program.name'),
        Mapper(source='.program.version', target='program.version'),
        Mapper(
            source='.system',
            mappers=[
                Mapper(source='.atoms.atom', target='atoms',
                    mappers=[
                        Mapper(source='.@element', target='element'),
                        Mapper(source='.@position', target='position')
                    ]
                )
            ]
        )
    ]
)
```

This is repetitive and error-prone. Instead, annotate the schema:

```python
add_mapping_annotation(Program.name, 'xml', '.program.name')
add_mapping_annotation(Program.version, 'xml', '.program.version')
add_mapping_annotation(Atom.element, 'xml', '.@element')
add_mapping_annotation(Atom.position, 'xml', '.@position')
```

`MetainfoParser` automatically builds the mapper tree by traversing annotated schema.

### Build Process

**Entry Point:** `MetainfoParser.build_mapper()` (lines 1114-1229)

**Algorithm:**

```python
def build_mapper(self) -> MetainfoMapper:
    if self.section is None:
        return None

    # Build mapper for root section
    mapper_dict = self.build_section_mapper(
        section=self.section,
        annotation_key=self.annotation_key
    )

    # Construct MetainfoMapper from dict
    return MetainfoMapper.from_dict(mapper_dict)
```

**Recursive Helper:** `build_section_mapper()` (lines 1138-1229)

**Process:**
1. Initialize mapper dict with section metadata
2. Iterate all quantities in section
3. For each quantity:
   - Check if it has mapping annotation
   - Extract mapper specification
   - Add to mapper dict
4. Iterate all subsections
5. For each subsection:
   - Recursively call `build_section_mapper()`
   - Add nested mapper to mappers list
6. Return mapper dict

**Example:**

```python
# Schema:
class System(ArchiveSection):
    atoms = SubSection(sub_section=Atom, repeats=True)

class Atom(ArchiveSection):
    element = Quantity(type=str)
    element.m_annotations['mapping'] = {'xml': '.@element'}

    position = Quantity(type=np.ndarray)
    position.m_annotations['mapping'] = {'xml': '.@position'}

# build_section_mapper(Atom, 'xml') returns:
{
    'm_def': Atom,
    'mappers': [
        {'source': '.@element', 'target': 'element'},
        {'source': '.@position', 'target': 'position'}
    ]
}

# build_section_mapper(System, 'xml') returns:
{
    'm_def': System,
    'mappers': [
        {
            'source': '.atoms.atom',
            'target': 'atoms',
            'mappers': [
                {'source': '.@element', 'target': 'element'},
                {'source': '.@position', 'target': 'position'}
            ]
        }
    ]
}
```

**Result:** Nested mapper tree matching schema structure, built automatically from annotations.

### Annotation Inheritance

Subsections inherit parent context:

```python
# Parent annotation
add_mapping_annotation(System.atoms, 'xml', '.system.atoms.atom')

# Child annotations (relative paths)
add_mapping_annotation(Atom.element, 'xml', '.@element')
add_mapping_annotation(Atom.position, 'xml', '.@position')

# Resolved paths:
# System.atoms → '.system.atoms.atom'
# Atom.element → '.system.atoms.atom.@element' (relative to parent)
# Atom.position → '.system.atoms.atom.@position' (relative to parent)
```

**How it works:**
1. Parent mapper extracts list from `.system.atoms.atom`
2. For each item in list, child mappers are evaluated
3. Child paths are relative to current item (implicit parent context)

---

## Common Patterns and Best Practices

### Pattern: Unit Conversion

**Problem:** File has values in one unit, archive expects another.

**Solution:** Transform with pint units:

```python
def convert_energy(self, value: float) -> pint.Quantity:
    """Convert energy from Hartree to eV."""
    return value * ureg.hartree

add_mapping_annotation(
    Energy.value,
    'myparser',
    mapper=('convert_energy', ['.energy'])
)
```

**Best Practice:** Always include units in return value. NOMAD handles unit conversion automatically.

### Pattern: Array Reshaping

**Problem:** File stores flat array, archive expects specific shape.

**Solution:** Reshape in transformer:

```python
def reshape_forces(self, flat_forces: list[float]) -> np.ndarray:
    """Reshape flat force list to (n_atoms, 3) array."""
    n_atoms = len(flat_forces) // 3
    return np.array(flat_forces).reshape((n_atoms, 3)) * ureg('eV/angstrom')

add_mapping_annotation(
    Forces.value,
    'myparser',
    mapper=('reshape_forces', ['.forces'])
)
```

**Best Practice:** Validate shapes and include units.

### Pattern: Conditional Extraction

**Problem:** Data location varies by file version or configuration.

**Solution 1:** JMESPath fallback:

```python
mapper='.output.energy || .results.total_energy'
```

**Solution 2:** Transformer with logic:

```python
def get_energy(self, source: dict) -> float | None:
    if 'output' in source:
        return source['output'].get('energy')
    elif 'results' in source:
        return source['results'].get('total_energy')
    return None

mapper=('get_energy', ['.@'])
```

**Best Practice:** Use JMESPath for simple fallbacks, transformers for complex logic.

### Pattern: List Filtering

**Problem:** Extract subset of list based on criteria.

**Solution 1:** JMESPath filter:

```python
mapper='.energies[?"@type"==\'total\']'
```

**Solution 2:** Indices parameter:

```python
add_mapping_annotation(
    property,
    'myparser',
    mapper='.items',
    indices=[0, 2, 4]  # Only first, third, fifth items
)
```

**Solution 3:** Transformer:

```python
def filter_converged(self, calculations: list[dict]) -> list[dict]:
    return [c for c in calculations if c.get('converged', False)]

mapper=('filter_converged', ['.calculations'])
```

**Best Practice:** Use JMESPath for simple filters, transformers for complex logic.

### Pattern: Multiple Sources

**Problem:** Combine data from multiple locations.

**Solution:** Transformer with multiple source paths:

```python
def combine_data(self, atoms: list, forces: list, energies: list) -> dict:
    return {
        'atoms': atoms,
        'forces': forces,
        'energies': energies
    }

mapper=('combine_data', ['.atoms', '.forces', '.energies'])
```

**Best Practice:** Keep transformers focused; avoid doing too much in one function.

### Pattern: Error Handling

**Problem:** Extraction might fail (missing data, malformed file).

**Solution:** Return `None` on error:

```python
def safe_extract(self, source: str) -> float | None:
    try:
        return float(source)
    except (ValueError, TypeError, KeyError):
        return None

mapper=('safe_extract', ['.energy'])
```

**Best Practice:**
- Return `None` for missing/invalid data
- Log warnings for unexpected conditions
- Don't raise exceptions (parser continues with other properties)

### Pattern: Caching Expensive Operations

**Problem:** Database lookup or heavy computation reused multiple times.

**Solution:** Enable caching:

```python
def lookup_functional(self, name: str) -> str:
    # Expensive database query
    return database.get_libxc_id(name)

add_mapping_annotation(
    property,
    'myparser',
    mapper=('lookup_functional', ['.xc_functional']),
    cache=True
)
```

**Best Practice:**
- Only cache pure functions (deterministic, no side effects)
- Cache when transformation is measurably expensive
- Don't cache trivial operations

### Anti-Pattern: Stateful Transformers

**Problem:** Transformer depends on mutable state.

**Bad Example:**

```python
class MyParser(XMLParser):
    def __init__(self):
        super().__init__()
        self.atom_count = 0  # Mutable state

    def process_atom(self, atom: dict) -> dict:
        self.atom_count += 1  # Mutates state
        return {'index': self.atom_count, 'element': atom['@element']}
```

**Why bad:**
- Execution order matters
- Not reusable (state persists)
- Caching breaks (state changes)

**Good Example:**

```python
class MyParser(XMLParser):
    @staticmethod
    def process_atoms(atoms: list[dict]) -> list[dict]:
        return [
            {'index': i, 'element': atom['@element']}
            for i, atom in enumerate(atoms)
        ]

mapper=('process_atoms', ['.atoms.atom'])
```

**Best Practice:** Transformers should be pure functions. If you need state, pass it as argument.

### Anti-Pattern: Overly Complex Transformers

**Problem:** Transformer does too much.

**Bad Example:**

```python
def process_everything(self, source: dict) -> dict:
    # Parse atoms
    atoms = [parse_atom(a) for a in source['atoms']]

    # Parse forces
    forces = reshape_forces(source['forces'])

    # Parse energy
    energy = convert_energy(source['energy'])

    # Build result
    return {'atoms': atoms, 'forces': forces, 'energy': energy}
```

**Why bad:**
- Hard to test
- Not reusable
- Difficult to understand

**Good Example:**

```python
def parse_atoms(self, source: list[dict]) -> list[dict]:
    return [self.parse_atom(a) for a in source]

def reshape_forces(self, forces: list[float]) -> np.ndarray:
    return np.array(forces).reshape(-1, 3)

def convert_energy(self, energy: float) -> pint.Quantity:
    return energy * ureg.eV

# Separate annotations
add_mapping_annotation(System.atoms, 'myparser', ('parse_atoms', ['.atoms']))
add_mapping_annotation(Forces.value, 'myparser', ('reshape_forces', ['.forces']))
add_mapping_annotation(Energy.value, 'myparser', ('convert_energy', ['.energy']))
```

**Best Practice:** One transformer, one responsibility. Compose via multiple annotations.

---

## Performance Considerations

### Parser Performance Profile

**Typical bottlenecks:**

1. **File I/O** (30-50% of time)
   - Loading file from disk
   - Decompression if compressed
   - Solution: Minimize file reads, reuse `data_object`

2. **Dictionary Conversion** (20-30% of time)
   - XML → dict (xmltodict)
   - HDF5 → dict (h5py traversal)
   - Solution: Lazy loading, convert only needed parts

3. **Path Extraction** (10-20% of time)
   - JMESPath query evaluation
   - Tree traversal
   - Solution: Optimize path expressions, use filters

4. **Transformation** (5-40% of time, varies widely)
   - Custom transformer logic
   - Array operations
   - Database lookups
   - Solution: Caching, vectorization, pre-computed lookups

5. **Archive Population** (5-10% of time)
   - Setting values in archive
   - Validation
   - Solution: Minimal (NOMAD core responsibility)

### Optimization Strategies

**1. Enable Caching for Expensive Transformers**

```python
# Before:
add_mapping_annotation(
    XCFunctional.libxc_name,
    'myparser',
    mapper=('lookup_libxc', ['.xc_functional'])
)
# Time: 500ms per call, called 10 times = 5000ms

# After:
add_mapping_annotation(
    XCFunctional.libxc_name,
    'myparser',
    mapper=('lookup_libxc', ['.xc_functional']),
    cache=True
)
# Time: 500ms first call, 0ms subsequent = 500ms total
```

**2. Vectorize Array Operations**

```python
# Slow: Element-wise Python loop
def process_values(self, values: list[float]) -> list[float]:
    return [v * 2.0 + 1.0 for v in values]

# Fast: NumPy vectorization
def process_values(self, values: list[float]) -> np.ndarray:
    arr = np.array(values)
    return arr * 2.0 + 1.0
```

**3. Use Compiled Regex**

```python
# Slow: Recompile every call
def extract_energy(self, text: str) -> float:
    match = re.search(r'Energy:\s*([-\d.]+)', text)
    return float(match.group(1)) if match else None

# Fast: Compile once
ENERGY_PATTERN = re.compile(r'Energy:\s*([-\d.]+)')

def extract_energy(self, text: str) -> float:
    match = self.ENERGY_PATTERN.search(text)
    return float(match.group(1)) if match else None
```

**4. Simplify JMESPath Queries**

```python
# Slow: Multiple filters and projections
'.items[*].values[?@.type==\'A\'][*].data[0]'

# Fast: Combined filter
'.items[*].values[?type==\'A\' && data].data[0]'
```

**5. Lazy Property Access**

```python
# Don't preload all data
def parse(self, filepath, archive, logger):
    # Bad: Load everything upfront
    all_data = self.load_all_data()

    # Good: Load on demand via properties
    if archive.run[0].program.name:
        # Only loads program data when needed
        archive.run[0].program.name = self.program_name
```

### Memory Considerations

**Large File Handling:**

```python
# Problem: Load entire 10GB HDF5 file into memory
def load_file(self) -> dict:
    with h5py.File(self.filepath) as f:
        return dict(f)  # Loads everything

# Solution: Keep file handle, load on demand
def load_file(self) -> h5py.File:
    return h5py.File(self.filepath, 'r')

def get_dataset(self, path: str) -> np.ndarray:
    # Only load requested dataset
    return self.data_object[path][:]
```

**Cache Memory Usage:**

If caching large arrays, monitor memory:

```python
def expensive_transform(self, data: np.ndarray) -> np.ndarray:
    # Returns 1GB array
    result = heavy_computation(data)
    return result

# With cache=True, this 1GB is stored in __cache
# For 100 different functions, that's 100GB!

# Solution: Don't cache huge arrays, or implement cache eviction
```

---

## Integration with NOMAD Pipeline

### Parser Plugin Structure

MappingParser is typically used within a parser plugin:

```python
# In myparser_plugin/parser.py
from nomad.parsing import MatchingParser
from nomad.parsing.file_parser.mapping_parser import XMLParser
from nomad.datamodel import EntryArchive

class MyCodeMainfileParser(MatchingParser):
    """Mainfile parser for MyCode."""

    def __init__(self):
        super().__init__(
            name='parsers/mycode',
            code_name='MyCode',
            code_homepage='https://mycode.org',
            mainfile_contents_re=(
                r'MyCode\s+Version\s+[\d\.]+.*'  # Regex to match mainfile
            ),
        )

    def parse(self, mainfile: str, archive: EntryArchive, logger):
        # Use MappingParser for actual parsing
        xml_parser = MyCodeXMLParser()
        xml_parser.parse(mainfile, archive, logger)

        # Additional post-processing if needed
        self.post_process(archive, logger)
```

**Entry Point:** `nomad.parsing.MatchingParser.parse()`

**Flow:**
1. NOMAD identifies mainfile using `mainfile_contents_re`
2. Instantiates `MyCodeMainfileParser`
3. Calls `parse()` method
4. Parser uses MappingParser to populate archive
5. Returns populated archive to NOMAD

### Schema Plugin Integration

Annotations are typically defined in a schema plugin:

```python
# In mycode_plugin/schema.py
from nomad.datamodel.metainfo.simulation.program import Program
from nomad_simulations.schema_packages.utils import add_mapping_annotation

# Add annotations to standard schema
add_mapping_annotation(
    Program.name,
    annotation_key='mycode',
    mapper='.program.name'
)

add_mapping_annotation(
    Program.version,
    annotation_key='mycode',
    mapper='.program.version'
)

# Define custom schema sections if needed
class MyCodeSpecificData(ArchiveSection):
    custom_property = Quantity(type=str)

add_mapping_annotation(
    MyCodeSpecificData.custom_property,
    annotation_key='mycode',
    mapper='.custom.property'
)
```

**Registration:** Schema plugin is registered in `nomad.yaml` or `pyproject.toml`:

```yaml
# nomad.yaml
plugins:
  include:
    - 'mycode_plugin.schema:mycode_schema'
```

### Multi-File Parsing

Real codes produce multiple output files:

```
calculation/
├── main.out          # Main text output
├── structure.xml     # System geometry
├── trajectory.h5     # MD trajectory
└── bands.dat         # Band structure
```

**Strategy:** Parse each file with appropriate parser:

```python
class MyCodeMainfileParser(MatchingParser):
    def parse(self, mainfile: str, archive: EntryArchive, logger):
        # Parse main output
        main_parser = MyCodeTextParser()
        main_parser.parse(mainfile, archive, logger)

        # Parse structure XML
        struct_file = mainfile.replace('.out', '.xml')
        if os.path.exists(struct_file):
            struct_parser = MyCodeXMLParser()
            struct_parser.parse(struct_file, archive, logger)

        # Parse trajectory HDF5
        traj_file = mainfile.replace('.out', '.h5')
        if os.path.exists(traj_file):
            traj_parser = MyCodeHDF5Parser()
            traj_parser.parse(traj_file, archive, logger)

        # Post-process to resolve cross-references
        self.resolve_references(archive)
```

**Annotation Keys:** Use different keys for different files:

```python
add_mapping_annotation(Program.name, 'mycode_main', '.program.name')
add_mapping_annotation(System.atoms, 'mycode_struct', '.structure.atoms')
add_mapping_annotation(Trajectory.positions, 'mycode_traj', '.positions')
```

---

## Testing MappingParser

### Unit Testing Transformers

```python
import pytest
from myparser import MyParser

def test_transform_energy():
    parser = MyParser()
    result = parser.transform_energy('123.456')

    assert result.units == ureg.eV
    assert result.magnitude == pytest.approx(123.456)

def test_transform_energy_invalid():
    parser = MyParser()
    result = parser.transform_energy('invalid')

    assert result is None  # Should handle gracefully
```

### Testing Path Extraction

```python
from nomad.parsing.file_parser.mapping_parser import Path

def test_path_extraction():
    data = {
        'calculation': {
            'program': {
                'name': 'MyCode',
                'version': '1.2.3'
            }
        }
    }

    path = Path('.calculation.program.name')
    result = path.get_data(data)

    assert result == 'MyCode'

def test_path_with_filter():
    data = {
        'energies': [
            {'type': 'kinetic', 'value': 100},
            {'type': 'total', 'value': -123.456}
        ]
    }

    path = Path('.energies[?type==\'total\'].value | [0]')
    result = path.get_data(data)

    assert result == -123.456
```

### Integration Testing

```python
from nomad.datamodel import EntryArchive
from myparser import MyCodeXMLParser

def test_parse_sample_file():
    parser = MyCodeXMLParser()
    archive = EntryArchive()

    parser.parse('tests/data/sample.xml', archive, logger)

    # Verify archive population
    assert archive.run[0].program.name == 'MyCode'
    assert archive.run[0].program.version == '1.2.3'
    assert len(archive.run[0].system[0].atoms) == 3
    assert archive.run[0].calculation[0].energy.total.value.magnitude == pytest.approx(-123.456)
```

### Test Data

Create minimal test files:

```xml
<!-- tests/data/sample.xml -->
<calculation>
  <program>
    <name>MyCode</name>
    <version>1.2.3</version>
  </program>
  <system>
    <atoms>
      <atom element="H" position="0 0 0"/>
      <atom element="O" position="1 0 0"/>
      <atom element="H" position="1 1 0"/>
    </atoms>
  </system>
  <energy units="eV">-123.456</energy>
</calculation>
```

**Best Practices:**
- One test file per feature
- Minimal content (only what's needed for test)
- Cover edge cases (missing data, malformed input)
- Test both positive and negative cases

---

## Troubleshooting

### Problem: Mapper Not Extracting Data

**Symptoms:** Property in archive is empty/None after parsing.

**Debug Steps:**

1. **Verify annotation exists:**
   ```python
   from nomad.parsing.file_parser.mapping_parser import MAPPING_ANNOTATION_KEY
   annotations = property.m_annotations.get(MAPPING_ANNOTATION_KEY, {})
   print(f"Annotations: {annotations}")
   ```

2. **Inspect parsed dictionary:**
   ```python
   parser = MyParser()
   parser.filepath = 'test.xml'
   print(json.dumps(parser.data, indent=2))
   ```

3. **Test path extraction:**
   ```python
   from nomad.parsing.file_parser.mapping_parser import Path
   path = Path('.calculation.energy')
   result = path.get_data(parser.data)
   print(f"Extracted: {result}")
   ```

4. **Check annotation key match:**
   ```python
   # Parser uses 'myparser'
   parser = MyParser()  # annotation_key='myparser'

   # But annotation uses 'other'
   add_mapping_annotation(property, 'other', '.path')

   # No match! Change to 'myparser'
   add_mapping_annotation(property, 'myparser', '.path')
   ```

### Problem: Transformer Not Called

**Symptoms:** Transformer method never executes.

**Debug Steps:**

1. **Verify method exists:**
   ```python
   parser = MyParser()
   method = getattr(parser, 'my_method', None)
   print(f"Method exists: {method is not None}")
   ```

2. **Check function name spelling:**
   ```python
   # Annotation says 'get_energy'
   mapper=('get_energy', ['.energy'])

   # But method is 'extract_energy'
   def extract_energy(self, value):
       ...

   # Fix: Match names
   def get_energy(self, value):
       ...
   ```

3. **Verify source path extracts data:**
   ```python
   path = Path('.energy')
   data = path.get_data(parser.data)
   print(f"Source data: {data}")  # Should not be None
   ```

### Problem: Wrong Data Extracted

**Symptoms:** Extracted value is not what you expect.

**Debug Steps:**

1. **Test JMESPath query:**
   ```python
   import jmespath
   result = jmespath.search('.calculation.energy', parser.data)
   print(f"JMESPath result: {result}")
   ```

2. **Check XML attributes:**
   ```xml
   <energy units="eV">-123.456</energy>
   ```
   ```python
   # Wrong: tries to get 'energy' key
   mapper='.energy'  # → {'@units': 'eV', '__value': '-123.456'}

   # Correct: get text content
   mapper='.energy.__value'  # → '-123.456'

   # Or attribute
   mapper='.energy.@units'  # → 'eV'
   ```

3. **Check list indexing:**
   ```python
   # Data is list
   data = {'items': [1, 2, 3]}

   # Wrong: gets whole list
   mapper='.items'  # → [1, 2, 3]

   # Correct: get first item
   mapper='.items[0]'  # → 1
   ```

### Problem: Cache Not Working

**Symptoms:** Transformer called multiple times despite `cache=True`.

**Debug Steps:**

1. **Verify cache flag:**
   ```python
   # Check annotation
   annotation = property.m_annotations[MAPPING_ANNOTATION_KEY]['myparser']
   print(f"Cache enabled: {annotation.cache}")
   ```

2. **Check cache contents:**
   ```python
   mapper = parser.mapper
   print(f"Cache: {mapper._Mapper__cache}")  # Name-mangled access
   ```

3. **Verify function name consistent:**
   ```python
   # Each call must use same function name
   # Wrong:
   def method1(self, x):
       return x * 2

   def method2(self, x):
       return x * 2

   mapper1=('method1', ['.x'], cache=True)  # Cache key: 'method1'
   mapper2=('method2', ['.y'], cache=True)  # Cache key: 'method2' (different!)

   # Correct: Same method
   mapper1=('method1', ['.x'], cache=True)
   mapper2=('method1', ['.y'], cache=True)  # Cache hit
   ```

### Problem: File Not Loading

**Symptoms:** `load_file()` fails or returns None.

**Debug Steps:**

1. **Check file exists:**
   ```python
   import os
   print(f"File exists: {os.path.exists(parser.filepath)}")
   ```

2. **Check file permissions:**
   ```python
   print(f"File readable: {os.access(parser.filepath, os.R_OK)}")
   ```

3. **Test file open:**
   ```python
   with parser.open(parser.filepath) as f:
       content = f.read()
       print(f"File content length: {len(content)}")
   ```

4. **Check compression:**
   ```python
   # For .xml.gz, .xml.bz2, etc.
   # MappingParser.open auto-detects compression
   print(f"Open function: {parser.open}")
   ```

### Problem: Schema Not Updating

**Symptoms:** New annotations not reflected in parsing.

**Debug Steps:**

1. **Restart NOMAD:** Schema changes require restart

2. **Check plugin registration:**
   ```yaml
   # nomad.yaml
   plugins:
     include:
       - 'mycode_plugin.schema:mycode_schema'
   ```

3. **Verify annotation runs:**
   ```python
   # At module level, not inside function
   add_mapping_annotation(property, 'myparser', '.path')

   # Not:
   def setup():
       add_mapping_annotation(property, 'myparser', '.path')  # Never called!
   ```

---

## Advanced Topics

### Custom Path Parser

By default, `Path` uses JMESPath. You can provide a custom parser:

```python
from nomad.parsing.file_parser.mapping_parser import PathParser

class MyPathParser(PathParser):
    def parse(self, path: str, data: dict) -> Any:
        # Custom path resolution logic
        keys = path.split('.')
        result = data
        for key in keys:
            result = result.get(key)
        return result

# Use custom parser
path = Path('.a.b.c', path_parser=MyPathParser())
```

### Custom Mapper Types

Extend `BaseMapper` for specialized behavior:

```python
class ConditionalMapper(BaseMapper):
    """Mapper that applies different logic based on condition."""

    condition: str
    true_mapper: BaseMapper
    false_mapper: BaseMapper

    def get_data(self, source, parser, **kwargs):
        # Evaluate condition
        condition_value = Path(self.condition).get_data(source)

        # Apply appropriate mapper
        if condition_value:
            return self.true_mapper.get_data(source, parser, **kwargs)
        else:
            return self.false_mapper.get_data(source, parser, **kwargs)
```

### Dynamic Annotation

Add annotations programmatically based on runtime conditions:

```python
def configure_parser(code_version: str):
    if code_version.startswith('1.'):
        # Version 1.x uses old format
        add_mapping_annotation(Energy.value, 'myparser', '.energy')
    else:
        # Version 2.x uses new format
        add_mapping_annotation(Energy.value, 'myparser', '.results.total_energy')
```

### Pre/Post Processing

Combine MappingParser with custom logic:

```python
class MyParser(XMLParser):
    def parse(self, filepath, archive, logger):
        # Pre-processing
        self.normalize_file(filepath)

        # Standard mapping
        super().parse(filepath, archive, logger)

        # Post-processing
        self.compute_derived_properties(archive)

    def normalize_file(self, filepath: str):
        # Fix malformed XML, add missing namespaces, etc.
        pass

    def compute_derived_properties(self, archive: EntryArchive):
        # Calculate properties not directly in file
        # E.g., lattice constants from vectors
        if archive.run[0].system[0].lattice_vectors:
            vectors = archive.run[0].system[0].lattice_vectors
            archive.run[0].system[0].lattice_constants = np.linalg.norm(vectors, axis=1)
```

---

## Comparison with Imperative Parsing

### Imperative Approach

```python
class ImperativeParser(MatchingParser):
    def parse(self, mainfile, archive, logger):
        # Load and parse XML
        tree = ET.parse(mainfile)
        root = tree.getroot()

        # Extract program info
        program_elem = root.find('./program')
        archive.run[0].program.name = program_elem.find('name').text
        archive.run[0].program.version = program_elem.find('version').text

        # Extract system
        system_elem = root.find('./system')
        atoms_elem = system_elem.find('./atoms')

        for atom_elem in atoms_elem.findall('atom'):
            atom = Atom()
            atom.element = atom_elem.get('element')

            pos_str = atom_elem.get('position')
            pos = [float(x) for x in pos_str.split()]
            atom.position = np.array(pos) * ureg.angstrom

            archive.run[0].system[0].atoms.append(atom)

        # Extract energy
        energy_elem = root.find('./energy')
        energy_value = float(energy_elem.text)
        energy_units = energy_elem.get('units', 'eV')
        archive.run[0].calculation[0].energy.total.value = energy_value * ureg(energy_units)
```

**Characteristics:**
- Explicit control flow
- Direct XML traversal
- Hard-coded paths
- Procedural style

### Declarative Approach (MappingParser)

```python
# Schema annotations
add_mapping_annotation(Program.name, 'myparser', '.program.name')
add_mapping_annotation(Program.version, 'myparser', '.program.version')
add_mapping_annotation(Atom.element, 'myparser', '.@element')
add_mapping_annotation(Atom.position, 'myparser', ('parse_position', ['.@position']))
add_mapping_annotation(Energy.value, 'myparser', ('parse_energy', ['.energy.__value', '.energy.@units']))

# Parser implementation
class DeclarativeParser(XMLParser):
    def __init__(self):
        super().__init__(annotation_key='myparser')

    @staticmethod
    def parse_position(pos_str: str) -> np.ndarray:
        return np.array([float(x) for x in pos_str.split()]) * ureg.angstrom

    @staticmethod
    def parse_energy(value_str: str, units_str: str) -> pint.Quantity:
        return float(value_str) * ureg(units_str)
```

**Characteristics:**
- Declarative mappings
- Schema-driven
- Reusable transformers
- Data-oriented

### Trade-offs

| Aspect | Imperative | Declarative (MappingParser) |
|--------|-----------|------------------------------|
| **Lines of code** | More | Fewer |
| **Flexibility** | High | Medium |
| **Maintainability** | Lower | Higher |
| **Testability** | Harder | Easier |
| **Performance** | Similar | Similar |
| **Learning curve** | Gentle | Steeper |
| **Reusability** | Low | High |
| **Schema coupling** | Loose | Tight |

**When to use Imperative:**
- Very complex parsing logic with many conditionals
- File format is highly irregular
- Need fine-grained control over every step
- One-off parser unlikely to be reused

**When to use MappingParser:**
- Structured file formats (XML, HDF5, JSON)
- Standard schema with many properties
- Parser will be reused across many files
- Want to leverage schema annotations
- Need maintainable, testable code

---

## Future Directions

### Potential Enhancements

1. **Streaming Parsing**: For very large files, parse in chunks rather than loading entirely into memory

2. **Parallel Extraction**: Extract independent properties concurrently for performance

3. **Schema Validation**: Validate extracted data against schema constraints before setting

4. **Mapper Optimization**: Compile mapper trees to optimize traversal

5. **Better Error Messages**: Enhanced diagnostics for mapping failures

6. **Visual Mapper Builder**: GUI tool to build mappers interactively

7. **Mapper Testing Framework**: Specialized testing utilities for mappers

### Known Limitations

1. **JMESPath Limitations**: Some complex queries not expressible in JMESPath; requires transformers

2. **Cache Granularity**: Cache key is function name only, can't cache different results for same function with different args

3. **No Mapper Inheritance**: Can't extend mappers, only replace; no inheritance mechanism

4. **Limited Debugging**: Hard to see why a mapper failed without deep diving

5. **Performance**: For very simple files, imperative parsing might be faster due to MappingParser overhead

---

## Glossary

- **Annotation Key**: String identifier for a file format's mapper annotations (e.g., `'xml'`, `'hdf5'`)
- **Archive**: NOMAD's data structure for storing parsed results (`EntryArchive`)
- **BaseMapper**: Abstract base class for all mapper types
- **Cache**: Storage for expensive transformation results to avoid recomputation
- **Data**: Wrapper combining `Path` and `Transformer` for extraction + transformation
- **Declarative**: Programming style where you declare what you want, not how to get it
- **JMESPath**: JSON query language used for extracting data from dictionaries
- **Mapper**: Object that defines how to extract data from source and where to place it in target
- **Mapping Annotation**: Metainfo annotation that specifies mapper for a property
- **MetainfoParser**: Parser that builds mapper tree automatically from schema annotations
- **Path**: JMESPath expression for extracting data from nested dictionaries
- **Subsection**: Schema property representing nested object (has `sub_section` parameter)
- **Transformer**: Function that converts extracted data before placing in archive
- **Tree Structure**: Hierarchical organization of nested mappers mirroring data structure
- **TreeInterpreter**: Extended JMESPath interpreter that tracks traversal state

---

## Conclusion

The MappingParser provides a powerful, declarative framework for parsing scientific data files into NOMAD archives. By separating data structure (schema) from extraction logic (mappers) and transformation logic (custom methods), it enables maintainable, testable, and reusable parsers.

Key takeaways:

1. **Declarative mappings** reduce code and improve maintainability
2. **Schema annotations** make data sources self-documenting
3. **Composition** of simple mappers handles complex structures
4. **Caching** optimizes expensive transformations
5. **Tree structures** naturally represent nested data
6. **MetainfoParser** automates mapper construction from annotations

For most structured file formats (XML, HDF5, JSON), MappingParser is the recommended approach. It integrates seamlessly with NOMAD's metainfo system and provides a consistent parsing experience across different codes and formats.

When creating a new parser:
1. Start with the tutorial to understand basics
2. Consult how-to guides for specific tasks
3. Reference the API documentation as needed
4. Read the explanation section to deepen understanding
5. Follow best practices and avoid anti-patterns

Happy parsing!

---

## Further Resources

- **NOMAD Documentation**: [https://nomad-lab.eu/docs](https://nomad-lab.eu/docs)
- **JMESPath Tutorial**: [https://jmespath.org/tutorial.html](https://jmespath.org/tutorial.html)
- **Example Parsers**: See `nomad-parser-plugins-simulation` package for real-world implementations
- **Schema Packages**: See `nomad-schema-plugins-simulations` for annotation examples
- **Testing**: See `tests/parsing/test_mapping_parser.py` for comprehensive test suite

---

*Document Version: 1.0*
*Last Updated: 2025-12-05*
*Author: Generated from codebase analysis*
