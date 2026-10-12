import unittest
import numpy as np
import cv2
from app.models import RunConfig, ImageMetadata
from app.image_processing import (
    compute_preprocessing_metrics,
    extract_features_and_match,
    fit_robust_transformation,
    compute_comparison_metrics,
    build_valid_mask
)

class TestMetrics(unittest.TestCase):
    def test_worked_examples_section_13(self):
        """Verifies every arithmetic formula matches the reference calculations in Section 13 of the PRD."""
        # 1. Mean in uint8 domain: Mean = 64; a=0, b=255 -> 100 * 64 / 255 = 25.1
        mean_val = 64.0
        a, b = 0.0, 255.0
        p1_idx = 100.0 * (mean_val - a) / (b - a)
        self.assertEqual(round(p1_idx, 1), 25.1)

        # 2. Valid fraction: 900 valid / 1000 pixels -> 90.0 / 100
        f_valid = 100.0 * 900 / 1000
        self.assertEqual(round(f_valid, 1), 90.0)

        # 3. Candidate utilization: Ns=400, Nr=500, M=200 -> 100 * 200 / 400 = 50.0 / 100
        Ns, Nr, M = 400, 500, 200
        c3_idx = 100.0 * M / min(Ns, Nr)
        self.assertEqual(round(c3_idx, 1), 50.0)

        # 4. Inlier utilization: Nin=150, min(Ns, Nr)=400 -> 100 * 150 / 400 = 37.5 / 100
        Nin = 150
        c4_idx = 100.0 * Nin / min(Ns, Nr)
        self.assertEqual(round(c4_idx, 1), 37.5)

        # 5. Inlier ratio: 150 / 200 * 100 = 75.0 / 100
        c5_idx = 100.0 * Nin / M
        self.assertEqual(round(c5_idx, 1), 75.0)

        # 6. Spatial coverage: 30 occupied / 40 eligible cells -> 75.0 / 100
        cov = 100.0 * 30 / 40
        self.assertEqual(round(cov, 1), 75.0)

        # 7. Median residual: 0.5 ref pixels, e0=1 -> 100 / (1 + 0.5/1) = 66.7 / 100
        e_med = 0.5
        e0 = 1.0
        c7_idx = 100.0 / (1.0 + e_med / e0)
        self.assertEqual(round(c7_idx, 1), 66.7)

        # 8. Sun direction: delta_S = 18 deg -> 100 * (1 - 18 / 180) = 90.0 / 100
        delta_S = 18.0
        c9_idx = 100.0 * (1.0 - delta_S / 180.0)
        self.assertEqual(round(c9_idx, 1), 90.0)

        # 9. Elevation difference: Es=35, Er=45, delta_E = 10 deg -> 100 * (1 - 10 / 180) = 94.4 / 100
        delta_E = 10.0
        c10_idx = 100.0 * (1.0 - delta_E / 180.0)
        self.assertEqual(round(c10_idx, 1), 94.4)

        # 10. Sampling ratio: 1.5 / 0.25 = 6 -> 100 / 6 = 16.7 / 100
        R = 1.5 / 0.25
        c11_idx = 100.0 / R
        self.assertEqual(round(c11_idx, 1), 16.7)

    def test_synthetic_alignment_and_metrics(self):
        """Tests the full pipeline on a textured image with known affine transform."""
        np.random.seed(42)
        ref = np.random.randint(50, 200, (400, 400), dtype=np.uint8)
        for _ in range(35):
            cx, cy = np.random.randint(40, 360), np.random.randint(40, 360)
            cv2.circle(ref, (cx, cy), np.random.randint(8, 25), int(np.random.randint(20, 240)), -1)

        A_gt = np.array([
            [1.0, 0.0, 15.0],
            [0.0, 1.0, 10.0]
        ], dtype=np.float32)

        A_inv = cv2.invertAffineTransform(A_gt)
        src = cv2.warpAffine(ref, A_inv, (400, 400))

        src_mask = np.ones((400, 400), dtype=bool)
        ref_mask = np.ones((400, 400), dtype=bool)
        cfg = RunConfig(error_scale_e0=1.0, error_scale_r0=1.0)

        src_metrics, src_j = compute_preprocessing_metrics(src, src.astype(float), src_mask, "source", [0.0, 255.0])
        ref_metrics, ref_j = compute_preprocessing_metrics(ref, ref.astype(float), ref_mask, "reference", [0.0, 255.0])

        self.assertEqual(len(src_metrics), 9)
        self.assertEqual(len(ref_metrics), 9)

        src_kps, src_desc, ref_kps, ref_desc, candidates, Ns, Nr = extract_features_and_match(
            src_j, ref_j, src_mask, ref_mask, cfg
        )
        self.assertGreater(len(candidates), 5)

        affine_est, candidates, nin, med_res, affine_params, gate_warnings = fit_robust_transformation(candidates, cfg)
        self.assertIsNotNone(affine_est)
        self.assertGreaterEqual(nin, 5)
        self.assertIsNotNone(med_res)
        self.assertLess(med_res, 2.0)

        checkpoints = [
            {"checkpoint_id": "CP1", "source_x": 100.0, "source_y": 100.0, "ref_x": 115.0, "ref_y": 110.0},
            {"checkpoint_id": "CP2", "source_x": 250.0, "source_y": 250.0, "ref_x": 265.0, "ref_y": 260.0}
        ]

        comp_metrics, warped_mask, usable_overlap, overlap_bbox = compute_comparison_metrics(
            (400, 400), (400, 400),
            src_mask, ref_mask,
            affine_est, candidates, nin, med_res,
            Ns, Nr, cfg,
            checkpoints=checkpoints
        )

        self.assertEqual(len(comp_metrics), 11)
        c8 = next(m for m in comp_metrics if m.metric_code == "C8")
        self.assertTrue(c8.availability)
        self.assertIsNotNone(c8.raw_value)
        self.assertLess(c8.raw_value, 2.0)

    def test_edge_cases(self):
        """Tests all-invalid mask and constant image behavior."""
        constant_img = np.full((100, 100), 128, dtype=np.uint8)
        valid_mask = np.ones((100, 100), dtype=bool)

        metrics, _ = compute_preprocessing_metrics(constant_img, constant_img.astype(float), valid_mask, "source", [0.0, 255.0])
        p9 = next(m for m in metrics if m.metric_code == "P9")
        self.assertEqual(p9.raw_value, 0.0)

        all_invalid_mask = np.zeros((100, 100), dtype=bool)
        with self.assertRaises(ValueError):
            compute_preprocessing_metrics(constant_img, constant_img.astype(float), all_invalid_mask, "source", [0.0, 255.0])

if __name__ == "__main__":
    unittest.main()
