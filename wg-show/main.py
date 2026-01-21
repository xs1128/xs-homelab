from fastapi import FastAPI
import subprocess
from fastapi.responses import JSONResponse

app = FastAPI(title="WireGuard Status API")

SCRIPT_PATH = "./get_status.sh"  # Your bash script

@app.get("/network-details")
async def network_details():
    try:
        result = subprocess.run(
            [SCRIPT_PATH],
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout
        # Output is already JSON, just return it
        return JSONResponse(content=eval(output))  # safe if output is strictly controlled
    except subprocess.CalledProcessError:
        return JSONResponse(content={"error": "Failed to run WireGuard script"}, status_code=500)

