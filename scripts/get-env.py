#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: get-env.py <aws-secret-id>", file=sys.stderr)
        return 1

    secret_id = sys.argv[1]
    result = subprocess.run(
        [
            "aws",
            "secretsmanager",
            "get-secret-value",
            "--secret-id",
            secret_id,
            "--query",
            "SecretString",
            "--output",
            "text",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    github_env = os.environ.get("GITHUB_ENV")
    if not github_env:
        print("GITHUB_ENV is not set; nothing to write.", file=sys.stderr)
        return 1

    with Path(github_env).open("a", encoding="utf-8") as fh:
        for key, value in payload.items():
            if isinstance(value, (list, dict)):
                formatted_value = json.dumps(value)
            else:
                formatted_value = str(value)
            fh.write(f"{key}={formatted_value}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
