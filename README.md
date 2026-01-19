# Student Group Assignment with CP-SAT

This project provides a tool to assign students to groups based on various criteria using Google's CP-SAT solver.

## Features

- **Prerequisites**: Ensure all group members meet a minimum requirement (e.g., language skills).
- **Minimize**: Balance group averages for specific criteria (e.g., GPA, workload).
- **Pull**: Maximize the total sum of member values for a criterion.
- **Rankings**: Maximize total student preference for groups.
- **Flexible Assignment**: Specify which groups each student is eligible for.
- **Student Exclusion**: Forbid specific pairs of students from being in the same group.
- **Group Size**: Strict enforcement of group sizes.

## Requirements

- [uv](https://github.com/astral-sh/uv)

## Installation

```bash
uv sync
```

## Usage

### Command Line Interface

Create a JSON file (see `examples/sample_input.json`) and run:

```bash
uv run python -m src.assignment.main path/to/input.json
```

### REST API Server

Start the server with:

```bash
uv run python -m src.assignment.main --serve
```

You can access the API documentation at `http://localhost:8000/docs`.

### Async REST API

The `/solve` endpoint now accepts a deferred request and returns an immediate acknowledgement. The solver runs in the background and POSTs results (including stats) to your callback URL.

Request shape:

```json
{
  "deferredId": "uuid-string",
  "callbackUrl": "http://localhost:9000/callback",
  "input": { "num_students": 10, "num_groups": 2, "groups": [], "students": [], "exclude": [] }
}
```

Ack response:

```json
{ "acknowledged": true, "deferredId": "uuid-string" }
```

Callback payload:

```json
{
  "deferredId": "uuid-string",
  "assignments": [ { "student_id": 0, "group_id": 1 } ],
  "stats": { "minimize": { "Leadership": { "max_group_avg_diff": 0.2, "max_group_global_diff": 0.1 } } }
}
```

Example curl (requires a callback server):

```bash
curl -X POST http://localhost:8000/solve \
     -H "Content-Type: application/json" \
     -d @- <<JSON
{
  "deferredId": "00000000-0000-0000-0000-000000000000",
  "callbackUrl": "http://localhost:9000/callback",
  "input": $(cat examples/sample_input.json)
}
JSON
```

### Criteria Types

1. **`prerequisite`**: Requires `min_ratio` (0.0 to 1.0). All members of the group must meet it.
2. **`minimize`**: Balances group averages against the global mean for that criterion.
3. **`pull`**: Maximizes the total sum of member values for that criterion.

## Input Format

```json
{
  "num_students": 10,
  "num_groups": 2,
  "exclude": [[0, 1]],
  "groups": [
    {
      "id": 0,
      "size": 5,
      "criteria": {
        "french": { "type": "prerequisite", "min_ratio": 0.4 }
      }
    }
  ],
  "students": [
    {
      "id": 0,
      "possible_groups": [0, 1],
      "values": { "french": 1.0, "gpa": 0.9 },
      "rankings": { "0": 0.7, "1": 0.3 }
    }
  ]
}
```
