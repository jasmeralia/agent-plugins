#!/usr/bin/env python3
"""PreToolUse hook: block commands that retrieve a decrypted secret.

Covers AWS SSM `get-parameter(s)[-by-path] --with-decryption` and Secrets
Manager `get-secret-value`. An agent should not be the one to decrypt a
secret - run the command yourself instead.
"""
import json
import re
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    ssm_decrypt = re.search(r"get-parameters?(-by-path)?\b", command, re.IGNORECASE) and re.search(
        r"--with-decryption\b", command, re.IGNORECASE
    )
    secrets_manager = re.search(r"get-secret-value\b", command, re.IGNORECASE)

    if ssm_decrypt or secrets_manager:
        reason = (
            "Blocked: this command retrieves a decrypted secret "
            "(AWS SSM SecureString via --with-decryption, or Secrets Manager get-secret-value). "
            "Run it yourself with the ! prefix in the prompt instead of having Claude execute it."
        )
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
