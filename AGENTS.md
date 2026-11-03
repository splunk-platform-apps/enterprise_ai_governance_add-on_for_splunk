# AGENTS.md — Enterprise AI Governance Add-on for Splunk

Repository-specific instructions for coding agents

## Commands

Run commands from the repository root. Prefer existing `make` targets and use `make help` to see the current supported workflows

- Build the add-on into `output/`: `make build`
- Perform setup, build, and package: `make package`
- Start the Docker development environment after building: `make run`


## Testing

- Run the default unit suite: `make test`
- Run UCC modular-input functional tests: `make modinput-test`


## Git Workflow

- Commit messages: follow [Conventional Commits](https://www.conventionalcommits.org/) (feat:, fix:, chore:, docs:, etc.)
- Pre-commit hooks must pass before committing. Run `pre-commit run --all-files` to check


## Code Style

- Use the hooks configured in `.pre-commit-config.yaml`; do not copy tool versions or hook inventories into this file
- Do not modify files consumed by `.pre-commit-config.yaml`
- New and updated unit tests must use pytest. Do not introduce new `unittest.TestCase`-based tests


## Boundaries

- Do not edit the shared, template-enforced `Makefile`
- `globalConfig.json` drives UCC-generated UI and input configuration; rebuild after changing it
- Do not edit or commit files under `output/`
- Do not commit, print, or expose values from `.env`, keys, OAuth credentials or credential-bearing environment variables
- Update `docs/` when changing user-facing behavior
- Do not edit `README.md`, `.github/`
- Never skip pre-commit hooks, or route around by adding `# noqa`, or equivalent suppressions to silence a rule you would otherwise want to disable in config
- Never introduce a nested or lower-precedence override file (e.g. a new `.eslintrc.yml` in a subdirectory, or an eslintConfig key in `package.json`)
