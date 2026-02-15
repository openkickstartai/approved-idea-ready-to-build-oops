# oops — 你的命令行错误记忆库 🧠

> Never Google the same error twice.

`oops` is a local-first CLI tool that stores error messages and their solutions in a SQLite database on your machine. When you hit the same error again, just `oops search` it.

## Install

```bash
pip install -e .
```

Or run directly:

```bash
python oops_cli.py --help
```

## Usage

### Record an error and its fix

```bash
oops add "ModuleNotFoundError: No module named 'pandas'" "pip install pandas" --tags python,pip
```

### Search your memory bank

```bash
oops search pandas
oops search "No module" --format json
```

### List recent entries

```bash
oops list --limit 5
```

### View statistics

```bash
oops stats
```

### Delete an entry

```bash
oops delete 3
```

### Shell hook (auto-detect failures)

Add to your `~/.zshrc`:

```bash
eval "$(oops shell-hook zsh)"
```

Or `~/.bashrc`:

```bash
eval "$(oops shell-hook bash)"
```

## Configuration

Set `OOPS_DB` environment variable to customize the database path:

```bash
export OOPS_DB=~/my-errors.db
```

Default: `~/.oops.db`

## Performance

- SQLite queries with LIKE on 10k entries: ~2ms (benchmarked on M1 Mac)
- Database size for 10k entries: ~1.5MB
- Zero network calls — everything is local

## License

MIT
