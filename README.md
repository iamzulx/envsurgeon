# envsurgeon

**Diagnose missing, unused, and leaked environment variables before they bite you.**

Every dev knows the pain: a fresh clone, `npm run dev`, and a cryptic crash because
`.env.example` is missing three variables someone added six months ago. Or worse —
a real API key hardcoded in a file that's about to be pushed.

`envsurgeon doctor` gives your project a one-shot diagnosis:

- **Missing** — variables your code reads but your env file never declares (the
  #1 cause of "works on my machine")
- **Unused** — variables declared but read nowhere (stale config, confusing setup)
- **Leaked** — hardcoded secrets: AWS keys, GitHub tokens, Stripe keys, JWTs,
  private keys, and generic `API_KEY = "..."` patterns
- **Unguarded** — a `.env` file not covered by `.gitignore`

Zero dependencies. One command. Works in CI.

## What it looks like

```
$ envsurgeon doctor .

scanning /home/me/api · env file: .env.example

✘ 2 variable(s) used but never declared
    API_URL  used at src/server.js:2
    STRIPE_SECRET  used at src/app.py:3
  → add them to your env file, or new devs will hit a wall

✘ 1 potential secret leak(s)
    AWS Access Key  src/config.py:1  AKIA…MPLE

! 1 variable(s) declared but never used
    OLD_FEATURE_FLAG

! .env is not covered by .gitignore
  → add a `.env` line before you commit anything

envsurgeon: ✘ 3 problem(s), 2 warning(s)
```

## Install

```bash
pipx install envsurgeon     # recommended
# or
pip install envsurgeon
```

## Usage

```bash
envsurgeon doctor .            # full diagnosis
envsurgeon doctor . --strict   # fail on warnings too (unused vars, leaks)
envsurgeon doctor . --json     # machine-readable, for CI pipelines
envsurgeon scan .              # only scan for hardcoded secrets
envsurgeon usage .             # list every env var your code reads + where
```

Exit codes: `0` healthy · `1` findings · `2` bad invocation — so it drops
straight into any CI step:

```yaml
- run: pipx run envsurgeon doctor . --strict
```

## What it understands

Python (`os.environ`, `os.getenv`), JavaScript/TypeScript (`process.env`,
`import.meta.env`), Go (`os.Getenv`), Ruby (`ENV[...]`), PHP (`getenv`),
shell/Docker/Compose/CI YAML (`${VAR}` syntax), plus `Dockerfile`,
`docker-compose.yml`, and `Makefile`.

## Why it's different

Most env tools check that your *local* env matches a schema. `envsurgeon` checks
the thing that actually breaks teams: **what the code reads vs. what the repo
declares** — statically, no runtime needed, no config to write first.

## Development

```bash
git clone https://github.com/iamzulx/envsurgeon
cd envsurgeon
python -m venv .venv && source .venv/bin/activate
pip install -e . pytest
pytest -q
```

## License

MIT
