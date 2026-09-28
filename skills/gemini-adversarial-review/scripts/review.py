#!/usr/bin/env python3
"""Prepare a bounded Git review snapshot and run agy in a read-only sandbox."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile


MAX_BYTES = 400_000
DEFAULT_TIMEOUT = 180
AUTH = Path.home() / ".gemini/antigravity-cli/antigravity-oauth-token"
RUBRIC = Path(__file__).resolve().parent.parent / "references/rubric.md"


class ReviewError(Exception):
    pass


def command(args, cwd, timeout=20):
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReviewError(f"command failed: {args[0]}: {exc}") from exc
    if p.returncode:
        raise ReviewError(f"{args[0]} failed: {p.stderr.decode(errors='replace').strip()}")
    return p.stdout


def git(root, *args):
    return command(["git", "-c", "core.quotePath=false", *args], root)


def paths_nul(data):
    return [p.decode("utf-8", "surrogateescape") for p in data.split(b"\0") if p]


def safe_relative(path):
    try:
        path.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ReviewError(f"non-UTF-8 path is unsupported: {path!r}") from exc
    p = PurePosixPath(path)
    if p.is_absolute() or not path or any(c in ("", ".", "..") for c in p.parts):
        raise ReviewError(f"unsafe path: {path!r}")
    return p


def checked_path(root, name, allow_dir=False):
    rel = safe_relative(name)
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ReviewError(f"symlink is outside the supported review boundary: {name}")
    if current.exists() and not (current.is_file() or (allow_dir and current.is_dir())):
        raise ReviewError(f"not a regular file: {name}")
    return current


def revision(root, value):
    if value.startswith("-") or "\0" in value:
        raise ReviewError("invalid revision")
    return git(root, "rev-parse", "--verify", "--end-of-options", f"{value}^{{commit}}").decode().strip()


def target_blob(root, rev, path):
    entries = git(root, "ls-tree", "-z", rev, "--", path).split(b"\0")
    entries = [e for e in entries if e]
    exact = [e for e in entries if e.split(b"\t", 1)[1].decode("utf-8", "surrogateescape") == path]
    if not exact:
        return None
    mode, kind, oid = exact[0].split(b"\t", 1)[0].split(b" ")
    if kind != b"blob" or mode not in (b"100644", b"100755"):
        raise ReviewError(f"symlink or submodule is unsupported: {path}")
    return command(["git", "cat-file", "blob", oid.decode()], root)


def select(root, scope, branch, rev_range, path_filter, include_untracked, context_paths):
    filters = []
    if path_filter:
        selected = checked_path(root, path_filter, allow_dir=True)
        if not selected.exists():
            raise ReviewError(f"selected path does not exist: {path_filter}")
        filters = [path_filter]
    if scope == "branch":
        other = revision(root, branch)
        head = revision(root, "HEAD")
        base = git(root, "merge-base", head, other).decode().strip()
        left, right = base, head
        label = f"merge-base({branch}, HEAD)..HEAD"
    elif scope == "range":
        if rev_range.count("..") != 1:
            raise ReviewError("range must be A..B")
        a, b = rev_range.split("..")
        left, right = revision(root, a), revision(root, b)
        label = rev_range
    else:
        left, right = "HEAD", None
        label = "HEAD..working tree (staged and unstaged)"
    diff_args = ["diff", "--no-ext-diff", "--no-textconv", "--binary", left]
    if right:
        diff_args.append(right)
    diff_args.extend(["--", *filters])
    patch = git(root, *diff_args)
    names_args = ["diff", "--no-ext-diff", "--name-only", "-z", left]
    if right:
        names_args.append(right)
    names_args.extend(["--", *filters])
    names = paths_nul(git(root, *names_args))
    untracked = []
    if include_untracked:
        if scope != "worktree":
            raise ReviewError("untracked files are supported only for worktree reviews")
        untracked = paths_nul(git(root, "ls-files", "--others", "--exclude-standard", "-z", "--", *filters))
    if not names and not untracked:
        raise ReviewError("empty diff: no selected changes to review")
    files = {}
    for name in sorted(set(names + untracked)):
        safe_relative(name)
        if right:
            data = target_blob(root, right, name)
        else:
            file = checked_path(root, name)
            data = file.read_bytes() if file.exists() else None
        if data is not None:
            files[name] = data
    contexts = []
    for name in context_paths:
        file = checked_path(root, name)
        if not file.exists():
            raise ReviewError(f"context path does not exist: {name}")
        if name not in files:
            files[name] = file.read_bytes()
            contexts.append(name)
    if untracked:
        for name in untracked:
            patch += b"\n\n=== UNTRACKED FILE: " + name.encode("utf-8", "surrogateescape") + b" ===\n"
            patch += files[name] + b"\n"
    if re.search(rb"(?m)^(?:new file mode|deleted file mode) 160000$|^index [0-9a-f]+\.\.[0-9a-f]+ 160000$", patch):
        raise ReviewError("submodule changes are unsupported; narrow the selection")
    if b"GIT binary patch" in patch or any(b"\0" in data for data in files.values()):
        raise ReviewError("binary content is unsupported; narrow the selection")
    try:
        patch.decode("utf-8")
        for data in files.values():
            data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReviewError("non-UTF-8 content is unsupported; narrow the selection") from exc
    total = len(patch) + sum(len(data) for data in files.values())
    if total > MAX_BYTES:
        raise ReviewError(f"selection is {total} bytes, above {MAX_BYTES}; narrow the selection")
    return {"scope": label, "changed_paths": sorted(set(names + untracked)),
            "untracked_paths": sorted(untracked), "context_paths": sorted(contexts),
            "files": files, "patch": patch, "bytes": total}


def selection_digest(selection):
    digest = hashlib.sha256()
    digest.update(selection["patch"])
    for name, data in sorted(selection["files"].items()):
        name_bytes = name.encode("utf-8", "surrogateescape")
        digest.update(len(name_bytes).to_bytes(8, "big"))
        digest.update(name_bytes)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def available_model(agy, requested):
    output = command([agy, "models"], Path("/tmp"), timeout=30).decode(errors="replace")
    models = {line.split("\t", 1)[0] for line in output.splitlines() if "\t" in line}
    if requested:
        if requested not in models:
            raise ReviewError(f"requested model is unavailable: {requested}")
        return requested
    pro = [m for m in models if re.fullmatch(r"gemini-\d+(?:\.\d+)*-pro-high", m)]
    low = [m for m in models if re.fullmatch(r"gemini-\d+(?:\.\d+)*-pro-low", m)]
    choices = pro or low
    if not choices:
        raise ReviewError("no Gemini Pro reasoning model is available")
    return sorted(choices, key=lambda m: tuple(map(int, re.findall(r"\d+", m))), reverse=True)[0]


def write_snapshot(snapshot, selection):
    review = snapshot / "review"
    files = review / "files"
    files.mkdir(parents=True)
    (review / "diff.patch").write_bytes(selection["patch"])
    for name, data in selection["files"].items():
        target = files / safe_relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return review


def sandbox_args(snapshot, agy):
    home = snapshot / "home"
    state = home / ".gemini/antigravity-cli"
    state.mkdir(parents=True)
    if not AUTH.is_file() or AUTH.is_symlink():
        raise ReviewError("Antigravity OAuth token is missing or unsafe")
    shutil.copyfile(AUTH, state / AUTH.name)
    (state / AUTH.name).chmod(stat.S_IRUSR | stat.S_IWUSR)
    cache = state / "cache"
    cache.mkdir()
    project = AUTH.parent / "cache/default_project_id.txt"
    if project.is_file() and not project.is_symlink():
        shutil.copyfile(project, cache / project.name)
    args = ["bwrap", "--die-with-parent", "--new-session", "--clearenv", "--unshare-pid",
            "--unshare-ipc", "--ro-bind", "/usr", "/usr",
            "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib64", "/lib64", "--ro-bind", "/etc", "/etc",
            "--dev-bind", "/dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
            "--dir", "/home", "--bind", str(home), "/home/morgan",
            "--ro-bind", str(snapshot / "review"), "/review", "--ro-bind", agy, "/agy",
            "--setenv", "HOME", "/home/morgan", "--setenv", "PATH", "/usr/bin:/bin",
            "--setenv", "XDG_CONFIG_HOME", "/home/morgan/.config", "--setenv", "XDG_CACHE_HOME", "/home/morgan/.cache",
            "--chdir", "/review"]
    resolver = Path("/etc/resolv.conf").resolve()
    if str(resolver).startswith("/run/"):
        args.extend(["--ro-bind", str(resolver.parent), str(resolver.parent)])
    return args + ["--"]


def run_review(selection, model, timeout, agy, deep):
    with tempfile.TemporaryDirectory(prefix="gemini-review-") as tmp:
        snapshot = Path(tmp)
        write_snapshot(snapshot, selection)
        prompt = RUBRIC.read_text() + "\n\n"
        prompt += f"Scope: {selection['scope']}\nChanged paths: {selection['changed_paths']}\n"
        prompt += "The review input is in /review/diff.patch and /review/files. Inspect it. "
        if deep:
            prompt += "Inspect surrounding call sites, tests, contracts, and error paths in the provided files. "
        prompt += "Your accessible repository snapshot is limited to the listed files. Do not infer unseen code.\n\n"
        prompt += selection["patch"].decode("utf-8")
        for name, data in selection["files"].items():
            prompt += f"\n\n=== FILE: {name} ===\n" + data.decode("utf-8")
        args = sandbox_args(snapshot, agy) + ["/agy", "--print", prompt, "--model", model,
                "--effort", "high", "--mode", "plan", "--output-format", "json",
                "--print-timeout", f"{timeout}s", "--disable-slash-commands"]
        try:
            p = subprocess.run(args, cwd="/tmp", capture_output=True, text=True, timeout=timeout + 15)
        except subprocess.TimeoutExpired as exc:
            raise ReviewError(f"review timed out after {timeout + 15}s") from exc
        if p.returncode:
            raise ReviewError(f"agy failed ({p.returncode}): {(p.stderr or p.stdout).strip()[:1000]}")
        try:
            result = json.loads(p.stdout)
        except json.JSONDecodeError as exc:
            raise ReviewError(f"agy returned invalid JSON: {p.stdout[:500]!r}") from exc
        if result.get("status") != "SUCCESS" or not str(result.get("response", "")).strip():
            raise ReviewError(f"agy did not return a review: {str(result.get('error') or result)[:1000]}")
        if re.match(r"\s*(?:error:\s*)?(?:quota exceeded|rate limit exceeded|unauthori[sz]ed|authentication failed|login required|eligibility check failed)\b",
                    result["response"], re.I):
            raise ReviewError(f"agy returned a possible quota/auth failure: {result['response'][:500]}")
        return {"status": "success", "model_requested": model, "scope": selection["scope"],
                "changed_paths": selection["changed_paths"], "untracked_paths": selection["untracked_paths"],
                "context_paths": selection["context_paths"], "input_bytes": selection["bytes"],
                "agy_status": result["status"], "conversation_id": result.get("conversation_id"),
                "usage": result.get("usage"), "raw_review": result["response"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--branch", help="compare HEAD with merge base of this branch")
    group.add_argument("--range", dest="rev_range", help="compare A..B")
    parser.add_argument("--path", help="limit changes to a selected file")
    parser.add_argument("--include-untracked", action="store_true")
    parser.add_argument("--context-path", action="append", default=[], help="add an explicit file for context")
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--model", help="available model ID; default latest Gemini Pro High")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--run", action="store_true", help="send the displayed selection to Antigravity")
    parser.add_argument("--expect-sha256", help="required with --run; hash from the preview")
    args = parser.parse_args()
    try:
        root = Path(git(Path(args.repo), "rev-parse", "--show-toplevel").decode().strip()).resolve()
        if args.timeout < 1 or args.timeout > 1800:
            raise ReviewError("timeout must be 1..1800 seconds")
        scope = "branch" if args.branch else "range" if args.rev_range else "worktree"
        selection = select(root, scope, args.branch, args.rev_range, args.path,
                           args.include_untracked, args.context_path)
        manifest = {k: selection[k] for k in ("scope", "changed_paths", "untracked_paths", "context_paths", "bytes")}
        manifest["sha256"] = selection_digest(selection)
        if not args.run:
            print(json.dumps({"status": "preview", **manifest}, indent=2))
            return 0
        if not args.expect_sha256 or args.expect_sha256 != manifest["sha256"]:
            raise ReviewError("selection changed or no matching --expect-sha256 supplied; preview again")
        agy = shutil.which("agy")
        if not agy or not shutil.which("bwrap"):
            raise ReviewError("agy and bwrap must be installed")
        model = available_model(agy, args.model)
        print(json.dumps({"sending_to_google": manifest, "model_requested": model}), file=sys.stderr)
        print(json.dumps(run_review(selection, model, args.timeout, agy, args.deep), indent=2))
        return 0
    except ReviewError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
