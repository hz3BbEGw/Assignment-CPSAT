FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy the source code
COPY src/ ./src/

# Expose the port
EXPOSE 8000

# Run the server
CMD ["uv", "run", "python", "-m", "src.assignment.main", "--serve", "--host", "0.0.0.0", "--port", "8000"]
