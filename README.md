# microclimate-sensor-analysis
Analysis of microclimate sensor data from the City of Helsinki (Mäkelänkatu) and 
Regions4climate (R4C, Koivukylä and Laajasalo) IoT sensor networks.

## Objectives

1. Advanced Data Visualization
   - Create effective visualizations (both static and interactive) for time series data
   - Implement spatial data visualization techniques (e.g. choropleth maps)
   - Design interactive dashboards for IoT sensor monitoring
   - Create data quality reports for the sensor data

1. Spatial Analysis
   - Detect and analyze regional differences
   - Understand spatial patterns in sensor networks
   - Study environmental and urban microclimate effects

## Setting up the environment

### Virtual environment

This project uses Python 3.13 and `uv` for dependency management. Follow these steps to set up your development environment:

Install `uv` if you haven't already. You can use brew:

```bash
brew install uv
```

or download the install script:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create a new virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate  # On Windows use: venv\Scripts\activate
uv pip install -e ".[dev,test]"
```

This will install:
- All core dependencies for data analysis and visualization
- Development tools (ruff, pre-commit, jupyter)
- Testing frameworks (pytest with coverage)

### Pre-commit hooks

This project uses pre-commit hooks for linting and code quality checks.

Install the hooks to your local repository:
```bash
pre-commit install
```

## Data sources

### IoT sensor data

Milesight IoT sensors send the data using LoRaWAN. The data is stored in InfluxDB v2.

Downloadable data:
- https://bri3.fvh.io/opendata/r4c/
- https://bri3.fvh.io/opendata/makelankatu/

Consult [data/README.md](data/README.md) for more information on the data
and how to download it.

Dashboards for above data:
- https://iot.fvh.fi/grafana/d/aduw70oqqdon4c/r4c-laajasalo-and-koivukyla?orgId=6&refresh=30m
- https://iot.fvh.fi/grafana/d/bdvh3ukceuneoa/makelankatu?orgId=6&refresh=30m

### FMI weather data

- https://en.ilmatieteenlaitos.fi/open-data-manual

We gather the weather data and store it into InfluxDB v2
from the FMI API using a custom
[fmiapi_v2.py](https://github.com/VekotinVerstas/DataManagementScripts/blob/master/FmiAPI/fmiapi_v2.py)
script once in an hour.


```bash
python fmiapi_v2.py --bbox 24.3,59.9,25.7,60.7 --duration 2h
```

### Sample data

Sample data files are available in the `data/samples` directory:
- [24E124136E140283.geojson](data/samples/24E124136E140283.geojson): Example IoT sensor data file containing:
  - Metadata
  - Temperature and humidity measurements at different resolutions:
    - Raw 10-minute data
    - 3-hour aggregates
    - Daily aggregates
- [fmi_observations_weather_multipointcoverage-hki-area-sample.csv](data/samples/fmi_observations_weather_multipointcoverage-hki-area-sample.csv): Weather observation data from FMI stations in Helsinki metropolitan area, including:
  - Air temperature
  - Dew point temperature
  - Wind speed and direction
  - Gust speed
  - Relative humidity
  - Pressure
  - Visibility
  - Cloud amount
  - Precipitation
  - Snow depth

  Data is provided at 10-minute intervals for multiple weather station locations.
- [r4c_latest.geojson](data/samples/r4c_latest.geojson) - Latest measurements from the R4C IoT sensor network and their metadata.
- [r4c_sample.csv](data/samples/r4c_sample.csv) - Sample of the raw 10-minute data from the R4C IoT sensor network.

### Downloading data

Switch to the `data` directory and run the wget command mentioned
in the [README.md](data/README.md) file in that directory to download the data.

After the data is downloaded, you can use the `merge_data.py` (TODO)
script to merge the data into single geojson and parquet files.

## Combine raw data

```bash
python exploration/combine_raw_data.py \
    --geojson-in $(ls data/raw/*.geojson) \
    --geojson-out data/interim/metadata_all.geojson \
    --parquet-in data/raw/makelankatu-2024.parquet data/raw/r4c_all-2024.parquet \
    --parquet-out data/interim/data_all.parquet
```

## Data analysis

### Automated analysis
Run `python exploration/create_sensor_analysis_reports.py` to generate
data quality profiling and
[exploratory data analysis](https://en.wikipedia.org/wiki/Exploratory_data_analysis)
report for each sensor in the combined raw data Parquet via
[YData Profiling](https://docs.profiling.ydata.ai/latest/features/time_series_datasets/) Python package.
These reports are saved as HTML files under [`reports/`](./reports/) and they
provide insights into the time-series characteristics of the data.

### Streamlit app for interactive data visualizations

```bash
streamlit run exploration/streamlit_dashboard.py
```
