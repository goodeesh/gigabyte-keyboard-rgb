# Contributing to Gigabyte Keyboard RGB Control

Thanks for your interest in contributing! This is a small project and we welcome help — especially from people who have access to Gigabyte/AORUS hardware we haven't been able to test ourselves.

## Code of conduct

Be kind. This is a hobby project maintained in spare time. Patience and clear communication go a long way.

## Ways to contribute

- **Hardware testing** — The single most valuable thing you can do is test the tool on a model not listed in the [tested hardware table](README.md#tested-hardware) and report back (issue or PR with the result and your `lsusb` output).
- **Bug reports** — If something doesn't work, please open an issue with the steps to reproduce, your distro, kernel version, and `lsusb` output.
- **Code improvements** — Per-key custom layouts, new model support, packaging, translations, and CI improvements are all welcome.
- **Documentation** — Typos, clarifications, and new model entries are appreciated.

## Before you start

- The `master` branch is **protected**: no direct pushes, even for maintainers. All changes go through a pull request.
- A GitHub Actions workflow runs the test suite on Python 3.8–3.12 for every PR. Your PR will not merge until CI is green.
- Linear history is enforced — use **squash merge** when merging your PR (GitHub will do this automatically if you click "Squash and merge").

## Setup

```sh
# Fork the repo on GitHub, then:
git clone https://github.com/<your-username>/gigabyte-keyboard-rgb.git
cd gigabyte-keyboard-rgb

# Create a virtual env (optional but recommended)
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with test deps
pip install -e .
pip install pytest

# Run the tests
python -m pytest tests/ -v

# Run the CLI against real hardware (if you have a supported keyboard)
gigabyte-rgb detect
gigabyte-rgb static purple
```

## Making changes

1. Create a branch from `master`:
   ```sh
   git checkout -b fix/short-description
   ```

2. Make your changes. Keep commits focused — one logical change per commit is ideal.

3. Add or update tests in `tests/` if your change touches `protocol.py`, `config.py`, or `cli.py`. The tray app is hard to unit-test (it needs a real display), so we focus tests on the protocol logic.

4. Make sure everything passes locally:
   ```sh
   python -m pytest tests/ -v
   ```

5. Commit and push to your fork:
   ```sh
   git add -A
   git commit -m "Short imperative commit message"
   git push -u origin fix/short-description
   ```

6. Open a pull request:
   ```sh
   gh pr create --base master
   ```
   or use the GitHub web UI.

## Pull request guidelines

- Use the PR template (it'll auto-populate when you create a PR from the GitHub web UI).
- Reference any issues your PR closes (e.g. "Closes #12").
- If your change affects the colour/protocol tables in the README, update the docs in the same PR.
- If your PR adds a new model to the tested-hardware table, please include the `lsusb` output as evidence.

## Branch protection rules (current)

The `master` branch has the following protection enabled:

| Rule | Setting |
|---|---|
| Direct pushes | ❌ Blocked for everyone |
| Pull request required | ✅ Yes |
| Approving reviews | 0 (you can merge your own PR) |
| CI must pass | ✅ All 5 Python versions |
| Branch must be up to date | ✅ Required |
| Force pushes | ❌ Blocked |
| Branch deletion | ❌ Blocked |
| Linear history | ✅ Required (use squash merge) |

## Code style

- Follow the existing style (PEP 8, 4-space indent, snake_case for functions/vars).
- Don't add comments unless the code is genuinely non-obvious.
- Keep functions short and focused.

## Adding support for a new keyboard

If your keyboard isn't recognised by the tool:

1. Run `gigabyte-rgb detect` (or `lsusb | grep -i gigabyte`) to find your VID/PID.
2. Try running the CLI with `--vid` and `--pid` overrides:
   ```sh
   gigabyte-rgb --vid 0x0414 --pid 0xXXXX static purple
   ```
3. If it works, open an issue with:
   - Your exact laptop model and CPU/GPU
   - The full `lsusb` line for the keyboard
   - Which colours and brightness levels you tested
   - Whether the tray app works with your PID (you may need to add it to the udev rule)
4. If you're comfortable editing Python, open a PR adding your PID to the udev rule and any constants that need updating, plus an entry in the tested-hardware table in the README.

## Releasing a new version

(Maintainers only.) Version bumps follow the pattern:

1. Update `__version__` in `src/gigabyte_keyboard_rgb/__init__.py`.
2. Update `version` in `pyproject.toml`.
3. Open a PR with the version bump.
4. After merge, tag the squash commit:
   ```sh
   git tag v0.X.Y <squash-commit-sha>
   git push origin v0.X.Y
   ```
5. GitHub will show the tag on the releases page; create a release with release notes.

## Questions?

Open an issue with the `question` label and we'll get back to you as soon as possible.