import asyncio
from api_layer.dual_routes import _handle_scan_analysis
from schemas.data_models import PersonaType
import os
import json

async def main():
    resp = await _handle_scan_analysis("where should invest to handle which vulnerabilty explain", "test-id", PersonaType.BUSINESS, {})
    print("Formatted output:", resp.formatted_output[:100])

if __name__ == "__main__":
    asyncio.run(main())
