# Student Group Assignment with CP-SAT

This project provides a tool to assign students to groups based on various criteria using Google's CP-SAT solver.

## Features

- **Hard Constraints**: Ensure a minimum ratio of students meeting a criterion (e.g., language skills).
- **Maximize/Minimize**: Optimize group averages for specific criteria (e.g., GPA, workload).
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

You can access the API documentation at `http://localhost:8000/docs`. You can test the endpoint using `curl`:

```bash
curl -X POST http://localhost:8000/solve \
     -H "Content-Type: application/json" \
     -d @examples/sample_input.json
```

### Criteria Types

1. **`constraint`**: Requires `min_ratio` (0.0 to 1.0).
2. **`minimize`**: Requires `target`. Minimizes the squared penalty for exceeding the target average.
3. **`maximize`**: Requires `target`. Minimizes the squared penalty for falling below the target average.

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
        "french": { "type": "constraint", "min_ratio": 0.4 }
      }
    }
  ],
  "students": [
    {
      "id": 0,
      "possible_groups": [0, 1],
      "values": { "french": 1.0, "gpa": 0.9 }
    }
  ]
}
```
