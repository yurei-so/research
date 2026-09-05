from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PIL import Image

from zenith_vision import BoundingBox, OcrFailure, OcrScan, OcrToken, OcrUnavailable, TesseractOcr, assess_text_safety, mask_ocr_tokens, parse_tesseract_tsv

HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"


class OcrSafetyTests(unittest.TestCase):
    def test_parses_tesseract_tokens_and_confidence(self) -> None:
        scan = parse_tesseract_tsv(HEADER + "5\t1\t1\t1\t1\t1\t0\t0\t10\t5\t96.5\tDodge\n")
        self.assertEqual(scan.tokens, (OcrToken("Dodge", 0.965),))

    def test_parses_normalized_token_geometry(self) -> None:
        scan = parse_tesseract_tsv(HEADER + "5\t1\t1\t1\t1\t1\t10\t20\t30\t40\t96\tDodge\n",
                                   image_size=(100, 200))
        self.assertEqual(scan.tokens[0].box, BoundingBox(0.1, 0.1, 0.3, 0.2))

    def test_rejects_unapproved_or_ambiguous_text(self) -> None:
        unknown = assess_text_safety(OcrScan((OcrToken("Account.1234", 0.99),), "fake", True))
        ambiguous = assess_text_safety(OcrScan((OcrToken("blur", 0.50),), "fake", True), allowed_text=["blur"])
        self.assertEqual(unknown.reason, "unapproved_text")
        self.assertEqual(ambiguous.reason, "ambiguous_text")
        self.assertFalse(unknown.safe_to_reveal)
        self.assertFalse(ambiguous.safe_to_reveal)

    def test_accepts_only_complete_confident_allowlist(self) -> None:
        scan = OcrScan((OcrToken("Dodge", 0.99), OcrToken("Heal", 0.95)), "fake", True)
        decision = assess_text_safety(scan, allowed_text=["dodge", "heal"])
        self.assertTrue(decision.safe_to_reveal)
        self.assertEqual(decision.reason, "ocr_clean")

    def test_empty_complete_scan_is_clean_but_not_a_region_classification(self) -> None:
        decision = assess_text_safety(OcrScan((), "fake", True))
        self.assertTrue(decision.safe_to_reveal)
        self.assertEqual(decision.token_count, 0)

    def test_incomplete_scan_fails_closed(self) -> None:
        decision = assess_text_safety(OcrScan((), "fake", False))
        self.assertFalse(decision.safe_to_reveal)
        self.assertEqual(decision.reason, "ocr_incomplete")

    def test_missing_executable_is_explicit(self) -> None:
        with patch("zenith_vision.ocr.shutil.which", return_value=None):
            with self.assertRaises(OcrUnavailable):
                TesseractOcr()

    def test_rejects_unsupported_page_segmentation_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "segmentation"):
            TesseractOcr(page_segmentation_mode=3)

    def test_malformed_tsv_fails_closed(self) -> None:
        with self.assertRaises(OcrFailure):
            parse_tesseract_tsv("not\ta\tvalid\theader\n")

    def test_masks_token_geometry_with_padding(self) -> None:
        image = Image.new("RGB", (100, 100), "white")
        scan = OcrScan((OcrToken("private", 0.99, BoundingBox(0.2, 0.3, 0.2, 0.1)),), "fake", True)
        masked = mask_ocr_tokens(image, scan, padding_pixels=2)
        self.assertEqual(masked.getpixel((20, 30)), (0, 0, 0))
        self.assertEqual(masked.getpixel((50, 50)), (255, 255, 255))

    def test_masking_without_geometry_fails_closed(self) -> None:
        with self.assertRaisesRegex(OcrFailure, "geometry"):
            mask_ocr_tokens(Image.new("RGB", (10, 10)), OcrScan((OcrToken("x", 1.0),), "fake", True))


if __name__ == "__main__":
    unittest.main()
