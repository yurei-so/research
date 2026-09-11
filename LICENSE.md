# Licensing

Yurei Research uses established licenses with path-specific scopes. There is
no single repository-wide license.

## AGPL-3.0-only — research software

The following software is licensed under the GNU Affero General Public License
version 3.0 only, whose complete text is in
[`LICENSES/AGPL-3.0-only.txt`](LICENSES/AGPL-3.0-only.txt):

- the generated research-library implementation in `site/`, `scripts/`, and
  `tests/`, plus its root package manifests and Pages workflow;
- software source, tests, and build files in `experiments/narrative-steering/`;
- software source, tests, and build files in `experiments/voxel-guidance/`.

This license permits commercial use and paid managed hosting. Its network
source provisions preserve a practical path to inspect, self-host, modify, and
fork covered research software, including modified versions offered over a
network.

## MIT — general apparatus and reusable infrastructure

The following directories retain or now carry the MIT License found in their
own `LICENSE` files:

- `apparatus/composition-review/`
- `apparatus/mujoco-lab/`
- `apparatus/state-encoding/`
- `demos/prosody-demo/`
- `experiments/composition-pipeline/`
- `experiments/conversation-prosody-pipeline/`
- `experiments/zenith-vision/`

Those permissive grants intentionally allow commercial use and incorporation
into larger proprietary products, subject to the MIT notice requirement.

## Research content is separate

Unless a file or containing directory states otherwise, no software license is
granted for research writing, labnotes, datasets, recorded observations,
frozen experimental inputs, generated artifacts, images, or other research
content. These materials remain copyright-protected while their eventual
content/data licensing is considered separately.

In mixed experiment directories, the AGPL grant applies to executable source,
tests, and build/configuration files; it does not automatically license files
under `docs/` or `artifacts/`, recorded datasets, model outputs, or frozen
protocol/result data.

The Yurei name and visual identity are not licensed as software merely because
they appear beside licensed code.

When a file carries an SPDX identifier, that identifier controls. Otherwise,
use this path policy and the nearest containing `LICENSE` file. If neither
assigns a license, assume no permission has been granted.
