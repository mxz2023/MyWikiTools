# Third-party notices

## Mi Fitness API signing (MIT)

Portions of `mi_fitness/signing.py` are adapted from:

- [Mi-Fitness-Sync](https://github.com/kevinkwee/Mi-Fitness-Sync) (`src/mi_fitness_sync/activity/crypto.py`)
- [mifit](https://pypi.org/project/mifit/) (same upstream)

Copyright (c) 2026 Michael Elian Kevin — MIT License.

Cloud login and transport use the `mifit` Python package (MIT) at runtime; session files are stored under `~/.config/mi-fitness/` for this CLI.

`mi_fitness/signing.py` is kept only for regression tests of the RC4/signature algorithm (not imported by the CLI at runtime).
