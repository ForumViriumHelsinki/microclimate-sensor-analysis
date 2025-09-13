# Data

## samples

[data/samples](./samples) contains sample data files for testing,
development and AI assistant.

## raw

data/raw contains raw data, downloaded from the web server.
To update it, run these commands in this directory:

```
wget -r -np -nd -N -A "*.geojson,*.parquet" https://bri3.fvh.io/opendata/microclimate/ -P ./raw/
wget -r -np -nd -N -A "fmi*.parquet"  https://bri3.fvh.io/opendata/r4c/ -P ./raw/
```

## interim

data/interim contains data that has been preprocessed,
but not yet ready for analysis.

To merge the raw data into a single file, run the
[combine_raw_data.py](../exploration/combine_raw_data.py)
script in the root of this project:

```
python exploration/combine_raw_data.py --geojson-in data/raw/kymp-r4c_latest.geojson  --geojson-out data/interim/data_latest.geojson --parquet-in data/raw/kymp-r4c*.parquet --parquet-out data/interim/data.parquet --fmi-in data/raw/fmi_observations_weather_multipointcoverage-hki-area-202* --fmi-out data/interim/fmi.parquet
```
