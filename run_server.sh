#!/bin/bash

# Flask Server Startup Script for Sustainability Agent

echo "🚀 Starting Sustainability Agent Flask Server..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import flask; import flask_cors" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Installing required dependencies..."
    pip install flask flask-cors werkzeug
else
    echo "✅ All dependencies are installed"
fi

# Run the Flask app
echo ""
echo "🌐 Server starting on http://localhost:5000"
echo "📝 Press Ctrl+C to stop the server"
echo ""

python3 server.py
