"""Tests for oops CLI."""
import os
import tempfile
from click.testing import CliRunner
from oops_cli import cli


def make_runner():
    tmp = tempfile.mktemp(suffix=".db")
    return CliRunner(env={"OOPS_DB": tmp}), tmp


def cleanup(db):
    if os.path.exists(db):
        os.unlink(db)


def test_add_and_search():
    runner, db = make_runner()
    res = runner.invoke(cli, ["add", "ModuleNotFoundError: pandas", "pip install pandas", "--tags", "python"])
    assert res.exit_code == 0
    assert "Recorded" in res.output
    res = runner.invoke(cli, ["search", "pandas"])
    assert res.exit_code == 0
    assert "pip install pandas" in res.output
    assert "1 time(s)" in res.output
    cleanup(db)


def test_search_no_results():
    runner, db = make_runner()
    runner.invoke(cli, ["add", "some random error", "some fix"])
    res = runner.invoke(cli, ["search", "nonexistent_xyz"])
    assert res.exit_code == 0
    assert "No matching" in res.output
    cleanup(db)



def test_list_entries():
    runner, db = make_runner()
    runner.invoke(cli, ["add", "err_alpha", "fix_alpha"])
    runner.invoke(cli, ["add", "err_beta", "fix_beta"])
    res = runner.invoke(cli, ["list"])
    assert res.exit_code == 0
    assert "err_alpha" in res.output
    assert "err_beta" in res.output
    cleanup(db)


def test_stats():
    runner, db = make_runner()
    runner.invoke(cli, ["add", "KeyError: 'name'", "check dict keys"])
    runner.invoke(cli, ["search", "KeyError"])
    res = runner.invoke(cli, ["stats"])
    assert res.exit_code == 0
    assert "Total errors recorded: 1" in res.output
    assert "1 hits" in res.output
    cleanup(db)


def test_delete():
    runner, db = make_runner()
    runner.invoke(cli, ["add", "test_err", "test_fix"])
    res = runner.invoke(cli, ["delete", "1"])
    assert res.exit_code == 0
    assert "Deleted" in res.output
    res = runner.invoke(cli, ["delete", "999"])
    assert "not found" in res.output
    cleanup(db)


def test_search_json_format():
    runner, db = make_runner()
    runner.invoke(cli, ["add", "ValueError: invalid", "cast to int", "--tags", "python"])
    res = runner.invoke(cli, ["search", "ValueError", "--format", "json"])
    assert res.exit_code == 0
    assert '"error_text"' in res.output
    assert "cast to int" in res.output
    cleanup(db)


def test_shell_hook_zsh():
    runner, db = make_runner()
    res = runner.invoke(cli, ["shell-hook", "zsh"])
    assert res.exit_code == 0
    assert "precmd_functions" in res.output
    cleanup(db)


def test_shell_hook_bash():
    runner, db = make_runner()
    res = runner.invoke(cli, ["shell-hook", "bash"])
    assert res.exit_code == 0
    assert "PROMPT_COMMAND" in res.output
    cleanup(db)


# --- Fuzzy search tests ---

def test_fuzzy_search_empty_db():
    """Searching an empty DB should print a friendly message and exit code 1."""
    runner, db = make_runner()
    res = runner.invoke(cli, ["search", "anything"])
    assert res.exit_code == 1
    assert "empty" in res.output.lower()
    cleanup(db)


def test_fuzzy_search_partial_match():
    """Fuzzy search finds entries even with a partial/similar query."""
    runner, db = make_runner()
    runner.invoke(
        cli,
        ["add", "ModuleNotFoundError: No module named 'pandas'",
         "pip install pandas", "--tags", "python,pip"],
    )
    runner.invoke(
        cli,
        ["add", "ImportError: cannot import name 'foo'", "check import path"],
    )
    res = runner.invoke(cli, ["search", "ModuleNotFoundError pandas"])
    assert res.exit_code == 0
    assert "% match" in res.output
    assert "pip install pandas" in res.output
    assert "ID:" in res.output
    cleanup(db)


def test_fuzzy_search_limit():
    """--limit flag restricts the number of results shown."""
    runner, db = make_runner()
    for i in range(10):
        runner.invoke(cli, ["add", f"error_{i} common_token", f"fix_{i}"])
    res = runner.invoke(cli, ["search", "common_token", "--limit", "3"])
    assert res.exit_code == 0
    matches = res.output.count("% match")
    assert matches == 3
    cleanup(db)


def test_fuzzy_search_ranking():
    """Results are ranked by similarity score descending."""
    runner, db = make_runner()
    # Entry with lower similarity (fewer matching tokens)
    runner.invoke(
        cli,
        ["add", "KeyError happened somewhere", "try except block"],
    )
    # Entry with higher similarity (more matching tokens from query)
    runner.invoke(
        cli,
        ["add", "KeyError: missing key name in dict", "use dict.get with default"],
    )
    res = runner.invoke(cli, ["search", "KeyError missing key name"])
    assert res.exit_code == 0
    output = res.output
    # Higher-similarity result (dict.get) should appear before lower one (try except)
    pos_high = output.find("use dict.get")
    pos_low = output.find("try except")
    assert pos_high != -1 and pos_low != -1, "Both entries should appear in results"
    assert pos_high < pos_low, "Higher similarity result should be listed first"
    cleanup(db)
