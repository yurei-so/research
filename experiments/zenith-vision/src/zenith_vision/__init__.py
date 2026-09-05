"""Public experiment boundary for Zenith Vision."""

from .fusion import fuse_observations
from .dataset import DatasetItem, DatasetManifest, ManifestError
from .models import BoundingBox, FusedObservation, MumbleSnapshot, VisionObservation
from .layout import (
    UI_PROFILE_REGION_BOXES, RegionLabel, RegionMetrics, RegionProposal,
    evaluate_regions, propose_default_regions, propose_profile_regions,
)
from .redaction import RedactionReceipt, RevealDecision, mask_regions, reverse_reveal
from .ocr import (
    OcrFailure, OcrScan, OcrToken, OcrUnavailable, TesseractOcr,
    TextSafetyDecision, assess_text_safety, mask_ocr_tokens, parse_tesseract_tsv,
)
from .capture import (
    CaptureUnavailable, WindowIdentity, WindowSelectionError, XWindowCapture,
    parse_wm_class, select_exact_window,
)
from .synthetic import generate_synthetic_corpus
from .review import ReviewCandidateReceipt, save_review_candidate
from .admission import admit_review_batch, admit_review_candidate
from .annotation import (
    VISIBLE_HUD_LABELS, approve_annotation_batch, approve_annotation_proposal,
    create_annotation_proposal,
)
from .collection import (
    create_contact_sheet, difference_hash, hamming_distance, is_distinct,
    save_batch_manifest, structural_privacy_regions,
)
from .blind_annotation import BLIND_LAYER_NAMES, create_blind_openraster, extract_blind_boxes
from .crop_runtime import PROMOTED_UI_PROFILES, CropArtifact, CropReceipt, persist_profile_crops
from .objectives import (
    ObjectiveTextObservation, interpret_objectives_crop, objective_text_to_vision,
    save_objective_observation,
)
from .panels import PANEL_TITLES, PanelObservation, recognize_panel_titles, scan_panel_tiles, scan_panel_titles
from .ui_state import (
    UiStateBaseline, UiStateExample, UiStateFeatures, UiStateRecognition,
    extract_ui_state_features,
)
from .panel_collection import (
    PanelTileArtifact, artifacts_to_dict, extract_panel_search_tiles,
    persist_panel_sample, write_panel_batch_manifest,
)
from .hybrid import HybridPanelDecision, combine_panel_evidence

__all__ = [
    "BLIND_LAYER_NAMES", "BoundingBox", "CropArtifact", "CropReceipt", "DatasetItem",
    "DatasetManifest", "FusedObservation",
    "CaptureUnavailable", "ManifestError", "MumbleSnapshot", "OcrFailure", "OcrScan", "OcrToken",
    "ObjectiveTextObservation", "OcrUnavailable", "PROMOTED_UI_PROFILES", "RedactionReceipt", "RegionLabel",
    "RegionMetrics", "RegionProposal",
    "HybridPanelDecision", "PANEL_TITLES", "PanelObservation", "PanelTileArtifact", "ReviewCandidateReceipt",
    "RevealDecision", "TesseractOcr", "TextSafetyDecision", "UI_PROFILE_REGION_BOXES",
    "VISIBLE_HUD_LABELS",
    "VisionObservation", "WindowIdentity",
    "WindowSelectionError", "XWindowCapture",
    "admit_review_batch", "admit_review_candidate", "approve_annotation_batch",
    "approve_annotation_proposal", "assess_text_safety",
    "artifacts_to_dict", "combine_panel_evidence", "create_annotation_proposal", "create_blind_openraster", "create_contact_sheet",
    "difference_hash", "evaluate_regions", "extract_blind_boxes", "extract_panel_search_tiles",
    "fuse_observations", "generate_synthetic_corpus",
    "hamming_distance", "interpret_objectives_crop", "is_distinct", "mask_ocr_tokens", "mask_regions",
    "objective_text_to_vision",
    "parse_tesseract_tsv",
    "parse_wm_class", "persist_panel_sample", "persist_profile_crops", "propose_default_regions", "propose_profile_regions",
    "recognize_panel_titles", "reverse_reveal", "save_objective_observation", "save_review_candidate",
    "save_batch_manifest", "scan_panel_tiles", "scan_panel_titles", "select_exact_window", "structural_privacy_regions",
    "UiStateBaseline", "UiStateExample", "UiStateFeatures", "UiStateRecognition",
    "extract_ui_state_features", "write_panel_batch_manifest",
]
