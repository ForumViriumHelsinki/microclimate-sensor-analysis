# Sensor Map Application

Interactive Streamlit application for visualizing and comparing environmental sensor data from Helsinki microclimate sensors.

## Features

- 🗺️ Interactive map showing all sensor locations
- 📊 Time series comparison between two sensors  
- 📈 Scatter plot analysis with correlation metrics
- 🎯 Easy sensor selection via map interface
- ⏱️ Flexible time range controls
- 📱 Responsive design

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Data files available in `../../data/interim/`:
  - `data_1h.parquet` (hourly sensor data)
  - `data_latest.geojson` (sensor metadata)

### Deployment

```bash
# Run deployment script
./deploy.sh

# Or manually:
docker-compose up -d
```

The application will be available at: **http://localhost:8501/sensor-map**

### Stopping the Application

```bash
docker-compose down
```

## Configuration

The application runs on `/sensor-map` path by default. Key configuration:

- **Port**: 8501
- **Base URL Path**: `/sensor-map`
- **Data Mount**: `../../data:/app/data:ro` (read-only)
- **Memory Limit**: 1GB
- **CPU Limit**: 0.5 cores

## Data Updates

The application automatically loads data from mounted volumes. To update data:

1. Update data files on the host system
2. Restart the container: `docker-compose restart`

### Automated Daily Restart

Add to your crontab for daily data refresh:

```bash
0 2 * * * cd /path/to/apps/sensor-map-app && docker-compose restart
```

## Development

### Local Development

For local development without Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (adjust data paths in app.py)
streamlit run app.py --server.baseUrlPath=/sensor-map
```

### Building Images

```bash
# Build image
docker-compose build

# View logs
docker-compose logs -f

# Check container status
docker-compose ps
```

## Monitoring

The application includes health checks that verify the Streamlit server is responding correctly on the configured path.

Health check endpoint: `http://localhost:8501/sensor-map/_stcore/health`

## Troubleshooting

### Common Issues

1. **Data files not found**: Ensure data files exist in `../../data/interim/`
2. **Port conflicts**: Change port mapping in `docker-compose.yml`
3. **Memory issues**: Adjust resource limits in `docker-compose.yml`

### Useful Commands

```bash
# View application logs
docker-compose logs -f sensor-map-app

# Check resource usage
docker stats sensor-map-app

# Access container shell
docker-compose exec sensor-map-app /bin/bash
```
