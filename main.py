# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from parser import IndianAddressParser
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Indian Address Parser API")

# Allow CORS for local frontend testing if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init parser once (heavy operation)
parser = IndianAddressParser()

# Request schema
class AddressRequest(BaseModel):
    address: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the Indian Address Parser API!"}

@app.post("/parse")
def parse_address(request: AddressRequest):
    parsed = parser.parse_address(request.address)
    return {"original": request.address, "parsed": parsed.to_dict()}

@app.get("/parse-all")
def parse_all_addresses():
    results = parser.parse_all_addresses()
    parser.export_results_json(results)
    return JSONResponse(content={"message": "All addresses parsed and saved to parsed_output.json", "total": len(results)})
