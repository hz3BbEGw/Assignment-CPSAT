import sys
import os
import json
import argparse
import asyncio
import urllib.request
import uvicorn
from fastapi import FastAPI, HTTPException
from .models import ProblemInput, ProblemOutput, DeferredSolveRequest, AckResponse
from .solver import solve_assignment

# Initialize FastAPI app
app = FastAPI(title="Assignment Solver API")

def post_callback(callback_url: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        callback_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()

async def run_solver_and_callback(request: DeferredSolveRequest) -> None:
    try:
        result = await asyncio.to_thread(solve_assignment, request.input)
        payload = {
            "deferredId": request.deferredId,
            "assignments": result.model_dump().get("assignments", []),
            "stats": result.model_dump().get("stats"),
        }
    except Exception as e:
        payload = {"deferredId": request.deferredId, "error": str(e)}

    try:
        await asyncio.to_thread(post_callback, request.callbackUrl, payload)
    except Exception as e:
        print(f"Callback failed: {e}", file=sys.stderr)

@app.post("/solve", response_model=AckResponse)
async def solve_endpoint(input_data: DeferredSolveRequest):
    """
    Accepts student assignment problem input and returns an ack immediately.
    """
    asyncio.create_task(run_solver_and_callback(input_data))
    return AckResponse(acknowledged=True, deferredId=input_data.deferredId)

def main():
    parser = argparse.ArgumentParser(description='Assign students to groups based on criteria.')
    parser.add_argument('input_file', nargs='?', help='Path to the input JSON file (or - for stdin)')
    parser.add_argument('--output', help='Path to the output JSON file', default=None)
    parser.add_argument('--serve', action='store_true', help='Start the REST API server')
    parser.add_argument('--port', type=int, help='Port for the server')
    parser.add_argument('--host', default="0.0.0.0", help='Host for the server')
    
    args = parser.parse_args()
    
    if args.serve:
        port = args.port if args.port is not None else int(os.environ.get("PORT", 8000))
        print(f"Starting server on {args.host}:{port}")
        uvicorn.run(app, host=args.host, port=port)
        return

    if not args.input_file:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.input_file == '-':
            input_data = json.load(sys.stdin)
        else:
            with open(args.input_file, 'r') as f:
                input_data = json.load(f)
                
        problem_input = ProblemInput(**input_data)
        result = solve_assignment(problem_input)
        
        output_json = result.model_dump_json(indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_json)
        else:
            print(output_json)
            
    except Exception as e:
        import traceback
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
