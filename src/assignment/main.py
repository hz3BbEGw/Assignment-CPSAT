import sys
import os
import json
import argparse
import asyncio
import hashlib
import hmac
import uuid
from typing import Any
from urllib import request as urlrequest
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic import ValidationError
from .models import ProblemInput, ProblemOutput
from .solver import solve_assignment

app = FastAPI(title="Assignment Solver API")

@app.post("/solve")
async def solve_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Accepts student assignment problem input and returns the solution.
    Supports deferred execution with callback when deferredId + callbackUrl are provided.
    """
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if isinstance(payload, dict) and "deferredId" in payload and "input" in payload:
        deferred_id = payload.get("deferredId")
        callback_url = payload.get("callbackUrl")
        if not isinstance(deferred_id, str) or not isinstance(callback_url, str):
            raise HTTPException(status_code=400, detail="Missing deferredId or callbackUrl")

        hash_key = os.environ.get("DEFERRED_ASSIGNMENT_HASH_KEY")
        if not hash_key:
            raise HTTPException(status_code=500, detail="Missing DEFERRED_ASSIGNMENT_HASH_KEY")

        try:
            input_data = ProblemInput(**payload.get("input", {}))
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        evaluation_id = str(uuid.uuid4())
        background_tasks.add_task(
            run_deferred_assignment,
            input_data,
            deferred_id,
            evaluation_id,
            callback_url,
            hash_key,
        )
        return {"evaluationId": evaluation_id}

    try:
        input_data = ProblemInput(**payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = await asyncio.to_thread(solve_assignment, input_data)
    return result


def run_deferred_assignment(
    input_data: ProblemInput,
    deferred_id: str,
    evaluation_id: str,
    callback_url: str,
    hash_key: str,
) -> None:
    try:
        result = solve_assignment(input_data)
        data = result.model_dump()
        data_hash = compute_data_hash(hash_key, data)
        payload = {
            "deferredId": deferred_id,
            "evaluationId": evaluation_id,
            "data": data,
            "hash": data_hash,
        }
        post_json(callback_url, payload)
    except Exception as exc:
        print(f"Deferred assignment failed: {exc}", file=sys.stderr)


def post_json(url: str, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=30) as resp:
        resp.read()


def compute_data_hash(secret: str, data: Any) -> str:
    payload = stable_stringify(data).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def stable_stringify(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, (str, int, float, bool)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(stable_stringify(v) for v in value) + "]"
    if isinstance(value, dict):
        items = []
        for key in sorted(value.keys()):
            items.append(f"{json.dumps(key, ensure_ascii=False, separators=(',', ':'))}:{stable_stringify(value[key])}")
        return "{" + ",".join(items) + "}"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

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
