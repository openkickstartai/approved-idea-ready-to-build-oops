#!/usr/bin/env python3
"""oops - your command-line error memory bank."""
import click
import sqlite3
import os
import json
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
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def search(query, fmt):
    """Search your error memory bank."""
    db = get_db()
    q = f"%{query}%"
    rows = db.execute(
        "SELECT * FROM errors WHERE error_text LIKE ? OR solution LIKE ? "
        "OR tags LIKE ? ORDER BY hit_count DESC, created_at DESC",
        (q, q, q),
    ).fetchall()
    if not rows:
        click.echo("No matching errors found. Time to Google it!")
        return
    for r in rows:
        db.execute("UPDATE errors SET hit_count=hit_count+1 WHERE id=?", (r["id"],))
    db.commit()
    if fmt == "json":
        click.echo(json.dumps([dict(r) for r in rows], indent=2, ensure_ascii=False))
    else:
        for r in rows:
            click.echo(f"\n{'='*50}")
            click.echo(f"Error: {r['error_text']}")
            click.echo(f"Fix:   {r['solution']}")
            if r["tags"]:
                click.echo(f"Tags:  {r['tags']}")
            click.echo(f"Looked up {r['hit_count']+1} time(s)")


@cli.command(name="list")
@click.option("--limit", default=10, help="Max entries to show")
def list_errors(limit):
    """List recent error entries."""
    db = get_db()
    rows = db.execute("SELECT * FROM errors ORDER BY created_at DESC LIMIT ?", (limit,))
    for r in rows:
        click.echo(f"[{r['id']}] {r['error_text'][:60]:<60} (hits:{r['hit_count']})")


@cli.command()
def stats():
    """Show error bank statistics."""
    db = get_db()
    total = db.execute("SELECT COUNT(*) c FROM errors").fetchone()["c"]
    click.echo(f"Total errors recorded: {total}")
    if total:
        click.echo("Most looked up:")
        for r in db.execute(
            "SELECT error_text,hit_count FROM errors ORDER BY hit_count DESC LIMIT 5"
        ):
            click.echo(f"  [{r['hit_count']} hits] {r['error_text'][:60]}")


@cli.command()
@click.argument("error_id", type=int)
def delete(error_id):
    """Delete an error entry by ID."""
    db = get_db()
    cur = db.execute("DELETE FROM errors WHERE id=?", (error_id,))
    db.commit()
    if cur.rowcount:
        click.echo(f"Deleted entry {error_id}")
    else:
        click.echo(f"Entry {error_id} not found")


@cli.command(name="shell-hook")
@click.argument("shell", type=click.Choice(["bash", "zsh"]))
def shell_hook(shell):
    """Print shell hook code for automatic error detection."""
    hook = (
        'oops_trap(){ local ec=$?; local cmd=$(fc -ln -1);'
        ' [ $ec -ne 0 ] && echo "oops: exit $ec. Run: oops search \\"$cmd\\""; }'
    )
    if shell == "zsh":
        click.echo(f"{hook}\nprecmd_functions+=(oops_trap)")
    else:
        click.echo(f'{hook}\nPROMPT_COMMAND="oops_trap;$PROMPT_COMMAND"')


if __name__ == "__main__":
    cli()
