# MuJoCo lab apparatus

Shared deterministic physics apparatus for research families that need a small,
inspectable 3D world. It is not a standalone research project and makes no
scientific claim by itself.

The first arena contains a planar two-axis agent, four landmarks, three
resource objects, a goal zone, and fixed obstacles. Scripted `explore`,
`acquire`, `construct`, and `recover` policies generate deterministic apparatus
smokes and Blender-readable replays. These policies are fixtures, not learned
agents and not evidence for Voxel Guidance.

The transition calibration runs those fixtures as one continuous mixed-strategy
episode, extracts causal four-second motion windows, and compares them with
motion-only prototypes. It sweeps abstention thresholds and records recognition
latency, coverage, accuracy, false guidance, and guidance frequency. Fixture
annotations and absolute coordinates are deliberately excluded from features.

```bash
uv sync
uv run yurei-mujoco-lab simulate --policy all --output outputs/replays.json
uv run yurei-mujoco-lab calibrate-transitions \
  --output outputs/transition-calibration.json \
  --replay-output outputs/transition-replay.json
uv run pytest
```

Blender export uses the Steam installation directly:

```bash
SDL_AUDIODRIVER=dummy ALSOFT_DRIVERS=null \
  /media/alu52/GSSD/SteamLibrary/steamapps/common/Blender/blender \
  --background --factory-startup \
  --python blender/render_replay.py -- \
  outputs/replays.json outputs/mujoco-lab.blend outputs/mujoco-lab.png
```

MuJoCo is pinned exactly because numerical behavior may change between engine
versions. Generated outputs record the engine version and arena digest.
