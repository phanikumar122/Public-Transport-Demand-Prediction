"""
run_api.py — Start the FastAPI backend server on http://localhost:8000
"""

import uvicorn

if __name__ == "__main__":
    print("Starting Public Transport Demand Prediction API Server on http://localhost:8000...")
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)
