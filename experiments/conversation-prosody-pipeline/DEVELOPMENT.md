# Development

This project is early and intentionally small. The goal is to keep the first
implementation easy to inspect while the metadata shape is still being tested.

## Requirements

- Python 3.11 or newer
- Bash
- Python `venv` support

On Debian or Ubuntu, `python3 -m venv` may require an extra package:

```bash
sudo apt install python3-venv
```

For versioned Python installs, the package may be versioned too:

```bash
sudo apt install python3.13-venv
```

## Virtualenv Workflow

Use the repository helper from the project root:

```bash
scripts/venv create
scripts/venv install
```

Activate the environment:

```bash
source .venv/bin/activate
```

Run commands inside the environment without activating it:

```bash
scripts/venv run python examples/minimal_turn.py
scripts/venv run python -m unittest discover -s tests
```

Other helper commands:

```bash
scripts/venv recreate
scripts/venv remove
scripts/venv python
scripts/venv help
```

The helper also accepts:

- `VENV_DIR` to choose a different virtualenv path.
- `PYTHON_BIN` to choose the Python used to create the virtualenv.

Example:

```bash
PYTHON_BIN=python3.12 VENV_DIR=.venv312 scripts/venv create
```

## VS Code Tasks

VS Code users can run the same commands with `Tasks: Run Task`:

```text
venv: create
venv: install
venv: recreate
venv: remove
example: minimal turn
test: unittest
```

`test: unittest` is registered as the default test task.

## Running Tests

The current test suite uses the Python standard library:

```bash
scripts/venv run python -m unittest discover -s tests
```

If a virtualenv cannot be created, check that your Python installation includes
`venv` and `ensurepip`.

GitHub Actions runs the test suite on supported Python versions and builds wheel
and source distribution artifacts for inspection. Publishing to PyPI is
intentionally not configured yet.

## Running The Example

```bash
scripts/venv run python examples/minimal_turn.py
```

The example prints JSON metadata for a turn compared against the conversation
baseline.

## Project Shape

```text
src/conversation_prosody_pipeline/
  baseline.py   Conversation-local running baselines
  pipeline.py   Turn-by-turn metadata builder
  types.py      Typed feature and metadata objects

examples/
  minimal_turn.py

tests/
  test_pipeline.py
```

## Design Boundaries

Keep the core pipeline focused on measurements:

- Prefer observable features over inferred states.
- Do not emit emotion labels.
- Do not add persistent speaker identity, voiceprints, or biometric profiles.
- Keep baselines scoped to the active conversation unless a privacy review says
  otherwise.
- Keep downstream interpretation outside the pipeline.

Good metadata says what changed. It does not claim what the speaker feels.

## Dependency Notes

The core package currently has no runtime dependencies. Add dependencies only
when they clearly buy back complexity or are needed for audio or speech-recognition
integration.

If dev tooling is added later, prefer documenting it here and wiring it through
`scripts/venv` or VS Code tasks so the workflow stays discoverable.
