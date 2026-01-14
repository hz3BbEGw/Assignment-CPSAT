import sys
import json
import argparse
import uvicorn
from fastapi import FastAPI, HTTPException
from .models import ProblemInput, ProblemOutput
from .solver import solve_assignment

# Initialize FastAPI app
app = FastAPI(title="Assignment Solver API")

@app.post("/solve", response_model=ProblemOutput)
async def solve_endpoint(input_data: ProblemInput):
    """
    Accepts student assignment problem input and returns the optimal assignment.
    """
    try:
        result = solve_assignment(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def main():
    parser = argparse.ArgumentParser(description='Assign students to groups based on criteria.')
    parser.add_argument('input_file', nargs='?', help='Path to the input JSON file (or - for stdin)')
    parser.add_argument('--output', help='Path to the output JSON file', default=None)
    parser.add_argument('--serve', action='store_true', help='Start the REST API server')
    parser.add_argument('--port', type=int, default=8000, help='Port for the server')
    parser.add_argument('--host', default="0.0.0.0", help='Host for the server')
    
    args = parser.parse_args()
    
    if args.serve:
        print(f"Starting server on {args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
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
