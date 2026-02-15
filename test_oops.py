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
