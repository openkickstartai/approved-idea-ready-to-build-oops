#!/usr/bin/env python3
"""oops - your command-line error memory bank."""
import click
import sqlite3
import os
import re
import json
import sys
from datetime import datetime


def db_path():
    return os.environ.get("OOPS_DB", os.path.join(os.path.expanduser("~"), ".oops.db"))


def get_db():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS errors ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, error_text TEXT NOT NULL,"
        "solution TEXT NOT NULL, tags TEXT DEFAULT '',"
        "created_at TEXT NOT NULL, hit_count INTEGER DEFAULT 0)"
    )
    conn.commit()
    return conn


def tokenize(text):
    """Split text into lowercase tokens on whitespace and punctuation."""
    tokens = re.split(r'[\s\W_]+', text.lower())
    return set(t for t in tokens if t)


def jaccard_similarity(set_a, set_b):
    """Compute Jaccard similarity between two token sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


@click.group()
def cli():
    """oops - never Google the same error twice."""


@cli.command()
@click.argument("error_text")
@click.argument("solution")
@click.option("--tags", default="", help="Comma-separated tags")
def add(error_text, solution, tags):
    """Record an error and its solution."""
    db = get_db()
    db.execute(
        "INSERT INTO errors (error_text,solution,tags,created_at) VALUES (?,?,?,?)",
        (error_text, solution, tags, datetime.now().isoformat()),
    )
    db.commit()
    click.echo("Recorded! You won't forget this one.")


@cli.command()
@click.argument("query")
@click.option("--limit", default=5, help="Maximum number of results to display")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def search(query, limit, fmt):
    """Fuzzy search your error memory bank with relevance ranking."""
    db = get_db()

    # Check if the database has any entries at all
    total = db.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
    if total == 0:
        click.echo("Your error memory bank is empty. Add some errors first with 'oops add'.")
        sys.exit(1)

    # Tokenize query for similarity scoring
    query_tokens = tokenize(query)

    # SQLite LIKE pre-filter: match rows containing any query token
    conditions = []
    params = []
    for token in query_tokens:
        like_pat = f"%{token}%"
        conditions.append("(error_text LIKE ? OR solution LIKE ? OR tags LIKE ?)")
        params.extend([like_pat, like_pat, like_pat])

    if conditions:
        where_clause = " OR ".join(conditions)
        rows = db.execute(
            f"SELECT * FROM errors WHERE {where_clause}", params
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM errors").fetchall()

    if not rows:
        click.echo("No matching errors found. Time to Google it!")
        return

    # Score each row using Jaccard similarity
    scored = []
    for row in rows:
        combined = f"{row['error_text']} {row['solution']} {row['tags']}"
        row_tokens = tokenize(combined)
        score = jaccard_similarity(query_tokens, row_tokens)
        if score > 0:
            scored.append((score, row))

    if not scored:
        click.echo("No matching errors found. Time to Google it!")
        return

    # Sort descending by similarity, take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    scored = scored[:limit]

    # Increment hit_count for matched entries
    for _score, row in scored:
        db.execute(
            "UPDATE errors SET hit_count = hit_count + 1 WHERE id = ?",
            (row['id'],),
        )
    db.commit()

    if fmt == "json":
        results = []
        for score, row in scored:
            results.append({
                "id": row["id"],
                "similarity": round(score * 100, 1),
                "error_text": row["error_text"],
                "solution": row["solution"],
                "tags": row["tags"],
                "hit_count": row["hit_count"] + 1,
            })
        click.echo(json.dumps(results, indent=2))
    else:
        for score, row in scored:
            pct = round(score * 100, 1)
            snippet = row["error_text"][:120]
            solution_preview = row["solution"][:120]
            hits = row["hit_count"] + 1
            click.echo(f"[{pct}% match] (ID: {row['id']})")
            click.echo(f"  Error:    {snippet}")
            click.echo(f"  Solution: {solution_preview}")
            click.echo(f"  Searched: {hits} time(s)")
            click.echo()


@cli.command(name="list")
@click.option("--limit", default=10, help="Max entries to show")
def list_entries(limit):
    """List recent error entries."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM errors ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    if not rows:
        click.echo("No entries yet.")
        return
    for r in rows:
        click.echo(f"[{r['id']}] {r['error_text'][:80]}")
        click.echo(f"    Fix: {r['solution'][:80]}")
        if r["tags"]:
            click.echo(f"    Tags: {r['tags']}")
        click.echo()


@cli.command()
def stats():
    """Show statistics about your error memory bank."""
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
    hits = db.execute("SELECT SUM(hit_count) FROM errors").fetchone()[0] or 0
    click.echo(f"Total errors recorded: {total}")
    click.echo(f"Total lookups: {hits} hits")


@cli.command()
@click.argument("entry_id", type=int)
def delete(entry_id):
    """Delete an error entry by ID."""
    db = get_db()
    cur = db.execute("DELETE FROM errors WHERE id = ?", (entry_id,))
    db.commit()
    if cur.rowcount:
        click.echo(f"Deleted entry {entry_id}.")
    else:
        click.echo(f"Entry {entry_id} not found.")


@cli.command(name="shell-hook")
@click.argument("shell", type=click.Choice(["bash", "zsh"]))
def shell_hook(shell):
    """Generate shell hook for auto-detecting command failures."""
    if shell == "bash":
        click.echo(
            'oops_hook() { local rc=$?; if [ $rc -ne 0 ]; then '
            'echo "Command failed (exit $rc). Run: oops add \\"<error>\\" \\"<fix>\\""; fi; }; '
            "PROMPT_COMMAND='oops_hook'"
        )
    else:
        click.echo(
            'oops_hook() { local rc=$?; if [ $rc -ne 0 ]; then '
            'echo "Command failed (exit $rc). Run: oops add \\"<error>\\" \\"<fix>\\""; fi; }; '
            "precmd_functions+=(oops_hook)"
        )


if __name__ == "__main__":
    cli()
