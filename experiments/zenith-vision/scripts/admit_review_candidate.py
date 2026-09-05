from pathlib import Path

from zenith_vision import admit_review_candidate

review = Path.home() / ".local/state/zenith-vision/review"
manifest = admit_review_candidate(
    review / "candidate-20260825T001740849501Z.png",
    review / "candidate-20260825T001740849501Z.json",
    Path.home() / ".local/state/zenith-vision/datasets/operator-pilot-v1",
    item_id="operator-00001",
)
print(manifest)
