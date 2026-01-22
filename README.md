# Student Group Assignment with CP-SAT

This project provides a tool to assign students to groups based on various criteria using Google's CP-SAT solver.

## Features

- **Prerequisites**: Ensure a minimum requirement is met by all members or by a required count.
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

### REST API

The `/solve` endpoint accepts a problem input and returns the solution directly (including stats when available).

Request shape:

```json
{
  "num_students": 10,
  "num_groups": 2,
  "groups": [],
  "students": [],
  "exclude": []
}
```

Response:

```json
{
  "assignments": [ { "student_id": 0, "group_id": 1 } ],
  "status": "OPTIMAL",
  "stats": { "minimize": { "Leadership": { "max_group_avg_diff": 0.2, "max_group_global_diff": 0.1 } } }
}
```

Example curl:

```bash
curl -X POST http://localhost:8000/solve \
     -H "Content-Type: application/json" \
     -d @- <<JSON
$(cat examples/sample_input.json)
JSON
```

### Criteria Types

1. **`prerequisite`**: Requires `min_ratio` (0.0 to 1.0). If `required_amount` is unset, all members must meet it; otherwise at least `required_amount` members must.
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
        "french": { "type": "prerequisite", "min_ratio": 0.4, "required_amount": 3 }
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
