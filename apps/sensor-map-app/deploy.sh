#!/bin/bash

# Sensor Map App Deployment Script
# This script builds and deploys the sensor map Streamlit application

set -e  # Exit on any error

echo "🚀 Starting sensor map app deployment..."

# Check if data files exist
if [ ! -f "../../data/interim/data_1h.parquet" ]; then
    echo "❌ Error: Required data file data_1h.parquet not found!"
    echo "Please ensure data files are processed before deployment."
    exit 1
fi

if [ ! -f "../../data/interim/data_latest.geojson" ]; then
    echo "❌ Error: Required data file data_latest.geojson not found!"
    echo "Please ensure data files are processed before deployment."
    exit 1
fi

echo "✅ Data files found"

# Build and start the application
echo "🏗️ Building Docker image..."
docker-compose build

echo "🚀 Starting application..."
docker-compose up -d

echo "🎉 Deployment complete!"
echo "📍 Application is running at: http://localhost:8501/sensor-map"
echo ""
echo "📊 Useful commands:"
echo "  View logs:    docker-compose logs -f"
echo "  Stop app:     docker-compose down"
echo "  Restart app:  docker-compose restart"
echo "  Check status: docker-compose ps"
echo ""
echo "🔄 To update data and restart daily, add this to your crontab:"
echo "0 2 * * * cd $(pwd) && docker-compose restart"
