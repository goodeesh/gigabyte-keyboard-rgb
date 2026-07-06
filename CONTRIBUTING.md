# Contributing to Gigabyte Keyboard RGB Control

Thanks for your interest in contributing! This is a small project and we welcome help — especially from people who have access to Gigabyte/AORUS hardware we haven't been able to test ourselves.

## Code of conduct

Be kind. This is a hobby project maintained in spare time. Patience and clear communication go a long way.

## Ways to contribute

- **Hardware testing** — Run `gigabyte-rgb detect` and `--calibrate` on a model not in the [hardware table](README.md#tested-hardware), then [submit the resulting JSON](#adding-a-new-model) as a profile.
- **Bug reports** — If something doesn't work, please open an issue with the steps to reproduce, your distro, kernel version, and `lsusb` output.
- **Code improvements** — Per-key custom layouts, packaging, translations, and CI improvements are all welcome.
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

## Adding a new model

The tool has a **calibration system** that lets you add support for any
Gigabyte USB keyboard without writing code.

### For users (no code needed)

1. **Install** the tool as described in the [README](README.md#installation)
2. **Run detection**:
   ```sh
   gigabyte-rgb detect
   ```
3. **Run calibration** (interactive, ~5 minutes):
   ```sh
   gigabyte-rgb --calibrate
   ```
   You will be prompted to name colours as the keyboard cycles through
   `(byte5, byte4)` sample points. The tool saves a JSON profile to
   `~/.config/gigabyte-keyboard-rgb/profiles/{VID}_{PID}.json`.
4. **Use the profile**: Click **Reload profiles** in the tray menu, or
   restart the service: `systemctl --user restart gigabyte-keyboard-rgb.service`
5. **Share your work**: Open a
   [GitHub issue](https://github.com/goodeesh/gigabyte-keyboard-rgb/issues/new)
   and attach the JSON file. We'll add it to the built-in set.

### For contributors (adding a built-in profile)

If you have calibration JSON from a tested laptop, you can add it as a
built-in profile in a PR:

1. Copy the JSON to `src/gigabyte_keyboard_rgb/profile_data/{VID}_{PID}.json`
2. Ensure the file follows the schema (see any existing file as a template)
3. Run the tests: `python -m pytest tests/ -v`
4. Open a PR as described in [Making changes](#making-changes)

### Profile JSON schema

```json
{
  "name": "Gigabyte Aorus 15BKF",
  "vid": "0x0414",
  "pid": "0x7A43",
  "interfaces": [1, 3],
  "control_interface": 3,
  "colour_map": {
    "red":   {"0": [1, 0],   "1": [1, 25],  "2": [1, 100]},
    "green": {"0": [2, 0],   "1": [2, 25],  "2": [2, 100]}
  }
}
```

| Field | Description |
|---|---|
| `name` | Human-readable model name |
| `vid` / `pid` | USB VID and PID as hex strings |
| `interfaces` | USB interfaces to detach (typically `[1, 3]`) |
| `control_interface` | Interface for `ctrl_transfer` (typically `3`) |
| `colour_map` | Map of colour name → brightness level `"0"/"1"/"2"` → `[byte5, byte4]` |

Profile JSON files in `~/.config/gigabyte-keyboard-rgb/profiles/` override
built-in files with the same `(VID, PID)`, so users can customise without
modifying the package.

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