#!/bin/bash
echo "Installing Node dependencies..."
#npm install

echo "Setting up Python Backend Environment..."
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv venv || /usr/bin/python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "Starting Flask Python Backend on port 3000..."
python backend.py &

echo "Starting Vite Frontend on port 5173..."
npm run dev
