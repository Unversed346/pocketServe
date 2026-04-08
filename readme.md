# pocketServe
Run websites-ish on your phone, tablet and smart fridge.

## What does it do?
pocketServe is a lightweight HTTP server designed to run on basically anything —
built for Android via Termux but works on any device with Python installed.

## Requirements
- Python 3
- Termux (if on Android)

## Installation
```bash
git clone https://github.com/Unversed346/pocketServe.git
cd pocketserve
```

## Usage
```bash
python localserver.py --port 8000 --dir .
```

## Options
| Flag | Description | Default |
|------|-------------|---------|
| `--port` | Port to listen on | 8000 |
| `--dir` | Directory to serve | Current directory |
| `--auto-port` | Auto-select a free port if the chosen one is busy | Off |

I dont know how to do screenshots for this.

The index.html in this project is a test of the app. 
