# NOMAD Spectroscopy Plugin

A NOMAD plugin for parsing and managing spectroscopy data including IR, Raman, and UV-Vis spectroscopy.

## Features

- Parse spectroscopy CSV files with wavenumber and absorbance data
- Support for multiple spectroscopy types (IR, Raman, UV-Vis)
- Flexible column name matching
- Robust error handling

## Installation

Add this plugin to your NOMAD installation:

```bash
pip install nomad-plugin-spectroscopy
```

Or in dev mode:

```bash
uv add packages/nomad-plugin-spectroscopy
```

## Usage

### CSV File Format

Upload CSV files with the following columns:

```csv
wavenumber_cm1,absorbance
650.4205,0.006448
652.2841,0.007156
654.1478,0.008152
```

### Supported Column Names

The parser is flexible with column naming:
- Wavenumber: `wavenumber_cm1`, `wavenumber_cm-1`, `wavenumber [cm-1]`
- Absorbance: `absorbance`, `absorbance_au`, `absorbance [a.u.]`

## Schema

### Spectrum

Main entry for spectroscopy data:
- `name`: Name of the spectrum (from filename)
- `spectrum_type`: Detected type (IR, Raman, UV-Vis)
- `num_points`: Number of data points
- `points`: List of SpectrumPoint entries

### SpectrumPoint

Individual spectral data point:
- `wavenumber`: Wavenumber in cm^-1
- `absorbance`: Absorbance value (dimensionless)

## Development

```bash
# Test the parser
uv run python test_spectrum.py

# Run tests
uv run pytest

# Lint code
uv run ruff check .
```
