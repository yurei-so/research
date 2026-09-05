# Licensing and dependency boundaries

## Project code

Conversation Prosody Pipeline's source code is licensed under the MIT License. See
the repository's root [LICENSE](../LICENSE) file for the full terms. The package
metadata in `pyproject.toml` also identifies the project license as MIT.

The license covers this project's code and documentation. Media datasets, model
files, and generated experiment artifacts are not part of the source distribution;
see the [data and artifact policy](data-policy.md).

## Core package and experiment tools

The core Python package is intentionally dependency-free. Tools used only to
prepare or run experiments stay outside the package's runtime dependencies and
must not be added to `project.dependencies` merely to reproduce an experiment.

For example:

- `faster-whisper` may be installed in a separate experiment environment for
  speech-to-text evaluation.
- FFmpeg may be installed as a system command for inspecting or converting
  media.

These tools are optional: they are not installed with Conversation Prosody
Pipeline and are not required to use the core package. Experiment notes should
record the tools and versions they used so that the setup can be reproduced
without changing the package dependency boundary.

Third-party libraries, command-line tools, models, and datasets retain their own
licenses and terms. The project's MIT License does not replace or extend those
terms. Users are responsible for checking that their use and redistribution of
third-party materials is permitted.

This document is provided for project guidance and is not legal advice.
