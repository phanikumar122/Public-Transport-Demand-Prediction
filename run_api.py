"""
run_api.py — Start the FastAPI backend & unified server
"""

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting Public Transport Demand Prediction API Server on http://{host}:{port}...")
    uvicorn.run("src.api.main:app", host=host, port=port, reload=False)

