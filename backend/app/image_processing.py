import os
import logging
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from app.models import RunConfig, ImageMetadata, MetricDetail, MatchPoint

logger = logging.getLogger("lunaralign.registration")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

def decode_image_array(file_path: str) -> np.ndarray:
    """Decodes image into numpy array preserving original data type and channels."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Try OpenCV with IMREAD_UNCHANGED
    img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
    if img is not None:
        return img
    
    # Fallback to PIL / tifffile if OpenCV fails on special TIFF formats
    try:
        from PIL import Image
        pil_img = Image.open(file_path)
        return np.array(pil_img)
    except Exception as e:
        raise ValueError(f"Failed to decode image from {file_path}: {str(e)}")

def convert_to_float_grayscale(img: np.ndarray) -> np.ndarray:
    """Converts image to single-channel float64 array using ITU-R BT.601 luminance approximation."""
    if img.ndim == 2:
        return img.astype(np.float64)
    elif img.ndim == 3:
        if img.shape[2] == 3:
            # OpenCV BGR order: I = 0.299R + 0.587G + 0.114B
            # B is channel 0, G is channel 1, R is channel 2
            b = img[:, :, 0].astype(np.float64)
            g = img[:, :, 1].astype(np.float64)
            r = img[:, :, 2].astype(np.float64)
            return 0.299 * r + 0.587 * g + 0.114 * b
        elif img.shape[2] == 4:
            # BGRA
            b = img[:, :, 0].astype(np.float64)
            g = img[:, :, 1].astype(np.float64)
            r = img[:, :, 2].astype(np.float64)
            return 0.299 * r + 0.587 * g + 0.114 * b
        else:
            # First channel if multi-band
            return img[:, :, 0].astype(np.float64)
    raise ValueError(f"Unsupported image array dimensions: {img.shape}")

def find_connected_border_mask(
    gray_array: np.ndarray,
    high_thresh: float = 248.0,
    dilate_px: int = 4
) -> np.ndarray:
    """
    Excludes connected white/near-white border or background collar touching
    the image perimeter (top, bottom, left, right) while preserving real interior
    bright lunar terrain (such as crater rims and central peaks).
    Returns a boolean mask: True for valid terrain pixels, False for excluded border.
    """
    h, w = gray_array.shape[:2]
    # Handle floating or uint8
    if np.issubdtype(gray_array.dtype, np.floating):
        max_val = float(np.nanmax(gray_array)) if gray_array.size > 0 else 1.0
        thresh = (high_thresh / 255.0) if max_val <= 1.0 else high_thresh
        white_binary = (gray_array >= thresh).astype(np.uint8)
    else:
        white_binary = (gray_array >= int(high_thresh)).astype(np.uint8)

    # Perimeter check: only exclude if white collar actually touches the image perimeter
    perimeter = np.concatenate([
        white_binary[0, :],
        white_binary[-1, :],
        white_binary[:, 0],
        white_binary[:, -1]
    ])
    # If perimeter has negligible white pixels (< 2%), no border to exclude
    if np.mean(perimeter) < 0.02:
        return np.ones((h, w), dtype=bool)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(white_binary, connectivity=8)
    perimeter_labels = set(np.unique(np.concatenate([
        labels[0, :],
        labels[-1, :],
        labels[:, 0],
        labels[:, -1]
    ])))
    perimeter_labels.discard(0) # 0 is non-white

    if not perimeter_labels:
        return np.ones((h, w), dtype=bool)

    border_mask = np.zeros((h, w), dtype=np.uint8)
    for lbl in perimeter_labels:
        border_mask[labels == lbl] = 255

    # Dilate border slightly (default 4px) to consume transition/aliasing boundary pixels
    if dilate_px > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (dilate_px * 2 + 1, dilate_px * 2 + 1))
        border_mask = cv2.dilate(border_mask, kernel)

    excluded_count = int(np.sum(border_mask > 0))
    excluded_pct = (excluded_count / border_mask.size) * 100.0
    logger.info(f"Connected border mask: Excluded {excluded_count} border pixels ({excluded_pct:.2f}% of image).")

    return border_mask == 0

def build_valid_mask(
    original: np.ndarray,
    metadata: Optional[ImageMetadata] = None,
    user_mask_path: Optional[str] = None,
    exclude_white_border: bool = True
) -> np.ndarray:
    """Builds boolean valid pixel mask: finite AND not nodata AND user_mask AND alpha > 0 AND not connected white border."""
    h, w = original.shape[:2]
    valid = np.ones((h, w), dtype=bool)

    # 1. Finite check
    if np.issubdtype(original.dtype, np.floating):
        valid &= np.isfinite(original if original.ndim == 2 else original[:, :, 0])

    # 2. Alpha check if 4 channels
    if original.ndim == 3 and original.shape[2] == 4:
        alpha = original[:, :, 3]
        valid &= (alpha > 0)

    # 3. Nodata check if declared
    if metadata and metadata.nodata_value is not None:
        nd = metadata.nodata_value
        if original.ndim == 2:
            valid &= (original != nd)
        else:
            valid &= (original[:, :, 0] != nd)

    # 4. User mask if provided
    if user_mask_path and os.path.exists(user_mask_path):
        u_mask = cv2.imread(user_mask_path, cv2.IMREAD_GRAYSCALE)
        if u_mask is not None and u_mask.shape == (h, w):
            valid &= (u_mask > 0)

    # 5. Connected white border exclusion
    if exclude_white_border:
        gray = convert_to_float_grayscale(original) if original.ndim == 3 else original
        border_valid = find_connected_border_mask(gray, high_thresh=248.0, dilate_px=4)
        valid &= border_valid

    return valid

def compute_preprocessing_metrics(
    raw_array: np.ndarray,
    gray_array: np.ndarray,
    valid_mask: np.ndarray,
    role: str, # "source" | "reference"
    bounds: List[float],
    dark_cutoff: float = 0.1,
    metadata: Optional[ImageMetadata] = None
) -> Tuple[List[MetricDetail], np.ndarray]:
    """
    Computes all 9 preprocessing metric types P1 to P9 for an image.
    Returns list of MetricDetail objects and the normalized matching copy J.
    """
    a, b = bounds[0], bounds[1]
    denom_ab = b - a if b != a else 1.0

    total_pixels = int(valid_mask.size)
    valid_pixels = gray_array[valid_mask]
    n_valid = int(valid_pixels.size)

    if n_valid == 0:
        raise ValueError(f"No valid pixels found in {role} image.")

    # P1: Mean intensity
    mean_val = float(np.mean(valid_pixels))
    p1_index = float(np.clip(100.0 * (mean_val - a) / denom_ab, 0.0, 100.0))
    m_p1 = MetricDetail(
        metric_code="P1",
        name="Mean intensity",
        stage="preprocessing",
        image_role=role,
        raw_value=round(mean_val, 2),
        raw_unit=metadata.intensity_units if metadata and metadata.intensity_units else "DN",
        display_index=round(p1_index, 1),
        index_label="Brightness position index",
        formula_id="P1",
        formula_text="μ = (1/N) Σ I_i; Index = 100(μ - a)/(b - a)",
        substituted_inputs={"N": n_valid, "sum_I": round(float(np.sum(valid_pixels)), 2), "a": a, "b": b},
        numerator=round(mean_val - a, 2),
        denominator=round(denom_ab, 2),
        availability=True,
        provenance="Computed from valid original pixels"
    )

    # P2: Median intensity
    median_val = float(np.median(valid_pixels))
    p2_index = float(np.clip(100.0 * (median_val - a) / denom_ab, 0.0, 100.0))
    m_p2 = MetricDetail(
        metric_code="P2",
        name="Median intensity",
        stage="preprocessing",
        image_role=role,
        raw_value=round(median_val, 2),
        raw_unit=metadata.intensity_units if metadata and metadata.intensity_units else "DN",
        display_index=round(p2_index, 1),
        index_label="Median position index",
        formula_id="P2",
        formula_text="m = median(I); Index = 100(m - a)/(b - a)",
        substituted_inputs={"median": round(median_val, 2), "a": a, "b": b},
        numerator=round(median_val - a, 2),
        denominator=round(denom_ab, 2),
        availability=True,
        provenance="Computed from valid original pixels"
    )

    # P3: Intensity standard deviation (ddof=0)
    std_val = float(np.std(valid_pixels, ddof=0))
    p3_index = float(np.clip(100.0 * (2.0 * std_val) / denom_ab, 0.0, 100.0))
    m_p3 = MetricDetail(
        metric_code="P3",
        name="Intensity standard deviation",
        stage="preprocessing",
        image_role=role,
        raw_value=round(std_val, 2),
        raw_unit=metadata.intensity_units if metadata and metadata.intensity_units else "DN",
        display_index=round(p3_index, 1),
        index_label="Variation index",
        formula_id="P3",
        formula_text="σ = √[(1/N) Σ(I_i - μ)²]; Index = 100 × 2σ/(b - a)",
        substituted_inputs={"std_dev": round(std_val, 2), "a": a, "b": b},
        numerator=round(2.0 * std_val, 2),
        denominator=round(denom_ab, 2),
        availability=True,
        provenance="Population std dev with ddof=0"
    )

    # P4: Intensity histogram (256 bins)
    hist_counts, bin_edges = np.histogram(valid_pixels, bins=256, range=(a, b))
    hist_percentages = (hist_counts / n_valid * 100.0).tolist()
    m_p4 = MetricDetail(
        metric_code="P4",
        name="Intensity histogram",
        stage="preprocessing",
        image_role=role,
        raw_value=256.0,
        raw_unit="bins",
        display_index=100.0,
        index_label="Total percentage sum",
        formula_id="P4",
        formula_text="h_j = count(I ∈ bin_j); bin_pct = 100 h_j / N; sum = 100%",
        substituted_inputs={"bins": 256, "total_count": n_valid, "a": a, "b": b},
        availability=True,
        provenance="256 uniform bins in [a, b]",
        extra_data={
            "counts": hist_counts.tolist(),
            "percentages": [round(p, 3) for p in hist_percentages],
            "bin_edges": [round(float(e), 2) for e in bin_edges]
        }
    )

    # P5: Intensity percentiles (Q0.01, Q0.50, Q0.99)
    q01, q50, q99 = np.quantile(valid_pixels, [0.01, 0.50, 0.99], method="linear")
    q01, q50, q99 = float(q01), float(q50), float(q99)
    q01_idx = float(np.clip(100.0 * (q01 - a) / denom_ab, 0.0, 100.0))
    q50_idx = float(np.clip(100.0 * (q50 - a) / denom_ab, 0.0, 100.0))
    q99_idx = float(np.clip(100.0 * (q99 - a) / denom_ab, 0.0, 100.0))
    m_p5 = MetricDetail(
        metric_code="P5",
        name="Intensity percentiles",
        stage="preprocessing",
        image_role=role,
        raw_value=round(q50, 2),
        raw_unit=metadata.intensity_units if metadata and metadata.intensity_units else "DN",
        display_index=round(q50_idx, 1),
        index_label="Q0.50 intensity position index",
        formula_id="P5",
        formula_text="Q_q = quantile(I, q); Index_q = 100(Q_q - a)/(b - a)",
        substituted_inputs={
            "Q0.01": round(q01, 2), "Q0.50": round(q50, 2), "Q0.99": round(q99, 2),
            "Index0.01": round(q01_idx, 1), "Index0.50": round(q50_idx, 1), "Index0.99": round(q99_idx, 1)
        },
        availability=True,
        provenance="Linear quantile interpolation",
        extra_data={"Q0.01": q01, "Q0.50": q50, "Q0.99": q99, "indices": [q01_idx, q50_idx, q99_idx]}
    )

    # Normalize copy for matching: J = clip((I - L) / (U - L), 0, 1)
    lower_bound = q01
    upper_bound = q99
    if upper_bound <= lower_bound:
        lower_bound = float(np.min(valid_pixels))
        upper_bound = float(np.max(valid_pixels))
    span_norm = upper_bound - lower_bound if upper_bound > lower_bound else 1.0

    j_norm = np.zeros_like(gray_array, dtype=np.float64)
    j_norm[valid_mask] = np.clip((gray_array[valid_mask] - lower_bound) / span_norm, 0.0, 1.0)

    # P6: Valid pixel fraction
    f_valid = float(100.0 * n_valid / total_pixels)
    m_p6 = MetricDetail(
        metric_code="P6",
        name="Valid pixel fraction",
        stage="preprocessing",
        image_role=role,
        raw_value=round(f_valid, 2),
        raw_unit="%",
        display_index=round(f_valid, 1),
        index_label="Valid-data index",
        formula_id="P6",
        formula_text="f_valid = 100 N / P; Index = f_valid",
        substituted_inputs={"N_valid": n_valid, "P_total": total_pixels},
        numerator=float(n_valid),
        denominator=float(total_pixels),
        availability=True,
        provenance="Ratio of unmasked to total raster cells"
    )

    # P7: Dark pixel fraction on J
    dark_mask = (j_norm < dark_cutoff) & valid_mask
    n_dark = int(np.sum(dark_mask))
    f_dark = float(100.0 * n_dark / n_valid)
    m_p7 = MetricDetail(
        metric_code="P7",
        name="Dark pixel fraction",
        stage="preprocessing",
        image_role=role,
        raw_value=round(f_dark, 2),
        raw_unit="%",
        display_index=round(f_dark, 1),
        index_label="Dark-pixel fraction",
        formula_id="P7",
        formula_text="f_dark = 100 count(J_i < t_dark)/N; Index = f_dark",
        substituted_inputs={"n_dark": n_dark, "n_valid": n_valid, "t_dark": dark_cutoff},
        numerator=float(n_dark),
        denominator=float(n_valid),
        availability=True,
        provenance=f"Normalized intensities with cutoff {dark_cutoff}",
        extra_data={"bright_support_index": round(100.0 - f_dark, 1)}
    )

    # P8: Endpoint or saturation fraction
    # Count maximum stored values (e.g. 255 if uint8, or max of declared domain b)
    endpoint_target = 255.0 if raw_array.dtype == np.uint8 else b
    n_endpoint = int(np.sum((valid_pixels >= endpoint_target)))
    f_endpoint = float(100.0 * n_endpoint / n_valid)
    m_p8 = MetricDetail(
        metric_code="P8",
        name="Endpoint or saturation fraction",
        stage="preprocessing",
        image_role=role,
        raw_value=round(f_endpoint, 2),
        raw_unit="%",
        display_index=round(f_endpoint, 1),
        index_label="Endpoint fraction",
        formula_id="P8",
        formula_text="f_endpoint = 100 N_endpoint / N_eval; Index = f_endpoint",
        substituted_inputs={"N_endpoint": n_endpoint, "N_eval": n_valid, "target_endpoint": endpoint_target},
        numerator=float(n_endpoint),
        denominator=float(n_valid),
        availability=True,
        provenance=f"Count of valid pixels at or above endpoint {endpoint_target}",
        extra_data={"nonclipped_index": round(100.0 - f_endpoint, 1)}
    )

    # P9: Intensity range
    i_min = float(np.min(valid_pixels))
    i_max = float(np.max(valid_pixels))
    span = i_max - i_min
    range_util_idx = float(np.clip(100.0 * span / denom_ab, 0.0, 100.0))
    m_p9 = MetricDetail(
        metric_code="P9",
        name="Intensity range",
        stage="preprocessing",
        image_role=role,
        raw_value=round(span, 2),
        raw_unit=metadata.intensity_units if metadata and metadata.intensity_units else "DN",
        display_index=round(range_util_idx, 1),
        index_label="Range utilization index",
        formula_id="P9",
        formula_text="span = I_max - I_min; Index = 100 × span/(b - a)",
        substituted_inputs={"min": round(i_min, 2), "max": round(i_max, 2), "span": round(span, 2), "a": a, "b": b},
        numerator=round(span, 2),
        denominator=round(denom_ab, 2),
        availability=True,
        provenance="Minimum, maximum and span of valid original intensities",
        extra_data={"min": i_min, "max": i_max, "min_pos_idx": round(100.0 * (i_min - a) / denom_ab, 1), "max_pos_idx": round(100.0 * (i_max - a) / denom_ab, 1)}
    )

    metrics_list = [m_p1, m_p2, m_p3, m_p4, m_p5, m_p6, m_p7, m_p8, m_p9]
    return metrics_list, j_norm

def extract_features_and_match(
    src_j: np.ndarray,
    ref_j: np.ndarray,
    src_mask: np.ndarray,
    ref_mask: np.ndarray,
    config: RunConfig
) -> Tuple[List[cv2.KeyPoint], np.ndarray, List[cv2.KeyPoint], np.ndarray, List[Dict[str, Any]], int, int]:
    """
    Extracts SIFT features and finds 1-to-1 candidate matches using L2 distance & ratio filter.
    Returns:
    src_kps, src_desc, ref_kps, ref_desc, candidate_matches, Ns, Nr
    """
    # Convert J to uint8 [0, 255] for SIFT
    src_u8 = np.round(src_j * 255.0).astype(np.uint8)
    ref_u8 = np.round(ref_j * 255.0).astype(np.uint8)

    src_mask_u8 = src_mask.astype(np.uint8) * 255
    ref_mask_u8 = ref_mask.astype(np.uint8) * 255

    if config.clahe_enabled:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        src_u8 = clahe.apply(src_u8)
        ref_u8 = clahe.apply(ref_u8)

    sift = cv2.SIFT_create(nfeatures=config.sift_nfeatures)
    src_kps, src_desc = sift.detectAndCompute(src_u8, mask=src_mask_u8)
    ref_kps, ref_desc = sift.detectAndCompute(ref_u8, mask=ref_mask_u8)

    Ns = len(src_kps) if src_kps is not None else 0
    Nr = len(ref_kps) if ref_kps is not None else 0

    if Ns < 3 or Nr < 3 or src_desc is None or ref_desc is None:
        return src_kps or [], src_desc, ref_kps or [], ref_desc, [], Ns, Nr

    # Bidirectional 2-NN matching with ratio test
    bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

    # 1. Source to Reference
    knn_src_to_ref = bf.knnMatch(src_desc, ref_desc, k=2)
    src_best = {}
    for match_pair in knn_src_to_ref:
        if len(match_pair) == 2:
            m, n = match_pair
            ratio = m.distance / n.distance if n.distance > 0 else 1.0
            if ratio < config.match_ratio_thresh:
                src_best[m.queryIdx] = (m.trainIdx, m.distance, ratio)

    # 2. Reference to Source (for mutual consistency check)
    knn_ref_to_src = bf.knnMatch(ref_desc, src_desc, k=2)
    ref_best = {}
    for match_pair in knn_ref_to_src:
        if len(match_pair) == 2:
            m, n = match_pair
            ratio = m.distance / n.distance if n.distance > 0 else 1.0
            if ratio < config.match_ratio_thresh:
                ref_best[m.queryIdx] = m.trainIdx

    # 3. Filter mutual 1-to-1 matches
    candidates = []
    match_idx = 0
    for s_idx, (r_idx, dist, ratio) in src_best.items():
        if ref_best.get(r_idx) == s_idx:
            sp = src_kps[s_idx].pt
            rp = ref_kps[r_idx].pt
            candidates.append({
                "match_index": match_idx,
                "src_idx": s_idx,
                "ref_idx": r_idx,
                "source_x": float(sp[0]),
                "source_y": float(sp[1]),
                "ref_x": float(rp[0]),
                "ref_y": float(rp[1]),
                "distance": float(dist),
                "ambiguity_ratio": float(ratio),
                "is_inlier": False,
                "residual": None,
                "rejection_reason": None
            })
            match_idx += 1

    return src_kps, src_desc, ref_kps, ref_desc, candidates, Ns, Nr

def fit_robust_transformation(
    candidates: List[Dict[str, Any]],
    config: RunConfig,
    src_dims: Optional[Tuple[int, int]] = None,
    ref_dims: Optional[Tuple[int, int]] = None
) -> Tuple[Optional[np.ndarray], List[Dict[str, Any]], int, Optional[float], Optional[Dict[str, Any]], List[str]]:
    """
    Fits robust affine transform using RANSAC with strict configurable support gates.
    Does NOT treat mathematical minimum of 3 affine point pairs as proof of a reliable match.
    Evaluates:
      - Support Gate 1: Inlier count >= config.min_inliers (default >= 6)
      - Support Gate 2: Spatial spread ratio >= config.min_spatial_spread_ratio (prevents degenerate collinearity/clustering)
      - Support Gate 3: Affine determinant > 0 (prevents reflections/inversions)
      - Support Gate 4: Singular value condition number <= config.max_affine_condition (prevents extreme shear/tilt)
      - Support Gate 5: Scale factor within [config.min_affine_scale, config.max_affine_scale]
    Returns:
      affine_matrix (2x3 or None), updated candidates with residuals, nin, median_residual, affine_params, gate_warnings
    """
    gate_warnings: List[str] = []
    affine_params: Optional[Dict[str, Any]] = None

    logger.info("================ ROBUST REGISTRATION EVALUATION ================")
    logger.info(f"Total candidate matches submitted: {len(candidates)}")
    for i, c in enumerate(candidates):
        logger.info(
            f"  Candidate {i}: Src=({c['source_x']:.2f}, {c['source_y']:.2f}) -> "
            f"Ref=({c['ref_x']:.2f}, {c['ref_y']:.2f}) | "
            f"dist={c['distance']:.2f}, ratio={c['ambiguity_ratio']:.3f}"
        )

    # Pre-check: if candidate count is below min_inliers, alignment is immediately inconclusive
    if len(candidates) < config.min_inliers:
        msg = f"Insufficient candidate matches ({len(candidates)} < support gate minimum of {config.min_inliers})."
        logger.warning(f"Registration Gate FAILED: {msg} Inconclusive — insufficient reliable matches.")
        gate_warnings.append(f"Inconclusive — insufficient reliable matches: Only {len(candidates)} candidate match(es) found (support gate requires at least {config.min_inliers}).")
        for c in candidates:
            c["rejection_reason"] = f"Candidate support below gate minimum ({len(candidates)} < {config.min_inliers})"
            c["is_inlier"] = False
        return None, candidates, 0, None, None, gate_warnings

    src_pts = np.float32([[c["source_x"], c["source_y"]] for c in candidates])
    ref_pts = np.float32([[c["ref_x"], c["ref_y"]] for c in candidates])

    # Initial RANSAC estimation
    affine_mat, inlier_mask = cv2.estimateAffine2D(
        src_pts,
        ref_pts,
        method=cv2.RANSAC,
        ransacReprojThreshold=config.ransac_reproj_thresh,
        maxIters=2000,
        confidence=0.99
    )

    if affine_mat is None or inlier_mask is None:
        msg = "RANSAC affine estimation failed to find a consistent geometric model."
        logger.warning(f"Registration Gate FAILED: {msg}")
        gate_warnings.append(f"Inconclusive — insufficient reliable matches: {msg}")
        for c in candidates:
            c["rejection_reason"] = "RANSAC model estimation failed"
            c["is_inlier"] = False
        return None, candidates, 0, None, None, gate_warnings

    inlier_mask = inlier_mask.ravel().astype(bool)
    nin = int(np.sum(inlier_mask))
    logger.info(f"RANSAC candidate evaluation: {nin} inliers from {len(candidates)} candidates.")

    # Calculate provisional residuals for all candidates to log and inspect
    ones = np.ones((len(candidates), 1), dtype=np.float32)
    src_homo = np.hstack([src_pts, ones])
    pred_ref = (src_homo @ affine_mat.T)
    residuals = np.linalg.norm(ref_pts - pred_ref, axis=1)

    inlier_residuals = []
    for i, c in enumerate(candidates):
        res = float(residuals[i])
        c["pred_ref_x"] = float(pred_ref[i, 0])
        c["pred_ref_y"] = float(pred_ref[i, 1])
        c["residual"] = round(res, 2)
        if inlier_mask[i]:
            c["is_inlier"] = True
            c["rejection_reason"] = None
            inlier_residuals.append(res)
        else:
            c["is_inlier"] = False
            c["rejection_reason"] = f"Geometric residual {res:.2f} px exceeded cutoff"

    med_res = float(np.median(inlier_residuals)) if inlier_residuals else None
    logger.info(f"RANSAC residual distribution: min={min(inlier_residuals):.2f} px, median={med_res:.2f} px, max={max(inlier_residuals):.2f} px" if inlier_residuals else "No inliers")

    # Decompose provisional affine matrix for logging & gating
    A = affine_mat[:2, :2]
    det_A = float(A[0, 0] * A[1, 1] - A[0, 1] * A[1, 0])
    u, s, vt = np.linalg.svd(A)
    cond_num = float(s[0] / s[1]) if s[1] > 1e-6 else 9999.0
    scale_x = float(np.hypot(A[0, 0], A[1, 0]))
    scale_y = float(np.hypot(A[0, 1], A[1, 1]))
    rotation_deg = float(np.degrees(np.arctan2(A[1, 0], A[0, 0])))

    # Compute spatial spread
    spread_ratio = 1.0
    span_x = 0.0
    span_y = 0.0
    if nin >= 2:
        inlier_ref_pts = ref_pts[inlier_mask]
        span_x = float(np.ptp(inlier_ref_pts[:, 0]))
        span_y = float(np.ptp(inlier_ref_pts[:, 1]))
        if ref_dims and ref_dims[0] > 0 and ref_dims[1] > 0:
            spread_ratio = (span_x * span_y) / float(ref_dims[0] * ref_dims[1])
        else:
            spread_ratio = 1.0
        logger.info(f"Inlier spatial spread: ref span=({span_x:.1f} x {span_y:.1f}) px, spread_ratio={spread_ratio:.4f} (gate min={config.min_spatial_spread_ratio})")

    affine_params = {
        "det": round(det_A, 4),
        "singular_values": [round(float(s[0]), 4), round(float(s[1]), 4)],
        "condition_number": round(cond_num, 2),
        "scale_x": round(scale_x, 3),
        "scale_y": round(scale_y, 3),
        "rotation_deg": round(rotation_deg, 2),
        "spread_ratio": round(spread_ratio, 4),
        "matrix": [[round(float(v), 5) for v in row] for row in affine_mat]
    }

    logger.info(f"Affine Matrix parameters:\n{affine_mat}")
    logger.info(f"Decomposition: det={det_A:.4f}, singular_values=[{s[0]:.3f}, {s[1]:.3f}], condition={cond_num:.2f}, scale=({scale_x:.3f}, {scale_y:.3f}), rot={rotation_deg:.2f}°")

    # SUPPORT GATES EVALUATION
    # Gate 1: Inlier count
    if nin < config.min_inliers:
        msg = f"Support Gate Failed: Inlier count ({nin}) is below minimum requirement ({config.min_inliers}). Inconclusive — insufficient reliable matches."
        logger.warning(msg)
        gate_warnings.append(f"Inconclusive — insufficient reliable matches: Only {nin} verified inlier(s) found (support gate requires at least {config.min_inliers}).")
        for c in candidates:
            if c["is_inlier"]:
                c["rejection_reason"] = f"Support gate failed: Inlier count ({nin}) < required ({config.min_inliers})"
        return None, candidates, nin, med_res, affine_params, gate_warnings

    # Gate 2: Spatial spread (prevents degenerate collinearity/clustering)
    min_span_px = 12.0
    if span_x < min_span_px or span_y < min_span_px or spread_ratio < config.min_spatial_spread_ratio:
        msg = f"Support Gate Failed: Spatial spread ratio ({spread_ratio:.4f}) or span ({span_x:.1f}x{span_y:.1f}px) is below minimum (ratio={config.min_spatial_spread_ratio}, span={min_span_px}px). Inliers are clustered or collinear."
        logger.warning(msg)
        gate_warnings.append(f"Inconclusive — insufficient reliable matches: Inlier spatial spread ({spread_ratio:.4f}) is too narrow to constrain 2D affine geometry.")
        return None, candidates, nin, med_res, affine_params, gate_warnings

    # Gate 3: Determinant
    if det_A <= 0:
        msg = f"Support Gate Failed: Affine determinant ({det_A:.4f}) is non-positive, representing an invalid geometric reflection/inversion."
        logger.warning(msg)
        gate_warnings.append(f"Inconclusive — insufficient reliable matches: Affine model produced negative determinant ({det_A:.4f}).")
        return None, candidates, nin, med_res, affine_params, gate_warnings

    # Gate 4: Condition number
    if cond_num > config.max_affine_condition:
        msg = f"Support Gate Failed: Condition number ({cond_num:.2f}) exceeds threshold ({config.max_affine_condition:.2f}), indicating extreme shear or tilted distortion."
        logger.warning(msg)
        gate_warnings.append(f"Inconclusive — insufficient reliable matches: Model condition number ({cond_num:.2f}) exceeds threshold ({config.max_affine_condition:.2f}), preventing tilted warp.")
        return None, candidates, nin, med_res, affine_params, gate_warnings

    # Gate 5: Scale bounds
    if s[1] < config.min_affine_scale or s[0] > config.max_affine_scale:
        msg = f"Support Gate Failed: Scale factors [{s[1]:.2f}, {s[0]:.2f}] outside realistic bounds [{config.min_affine_scale}, {config.max_affine_scale}]."
        logger.warning(msg)
        gate_warnings.append(f"Inconclusive — insufficient reliable matches: Scale factor outside valid range [{config.min_affine_scale}, {config.max_affine_scale}].")
        return None, candidates, nin, med_res, affine_params, gate_warnings

    # Refine on inliers using LMEDS if support gates all passed
    refined_mat, _ = cv2.estimateAffine2D(
        src_pts[inlier_mask],
        ref_pts[inlier_mask],
        method=cv2.LMEDS
    )
    if refined_mat is not None:
        affine_mat = refined_mat

    logger.info(">>> ALL SUPPORT GATES PASSED: Valid registration established. <<<")
    return affine_mat, candidates, nin, med_res, affine_params, gate_warnings

def compute_comparison_metrics(
    src_dims: Tuple[int, int], # (h, w)
    ref_dims: Tuple[int, int], # (h, w)
    src_valid_mask: np.ndarray,
    ref_valid_mask: np.ndarray,
    affine_mat: Optional[np.ndarray],
    candidates: List[Dict[str, Any]],
    nin: int,
    med_res: Optional[float],
    Ns: int,
    Nr: int,
    config: RunConfig,
    checkpoints: Optional[List[Dict[str, Any]]] = None,
    src_meta: Optional[ImageMetadata] = None,
    ref_meta: Optional[ImageMetadata] = None
) -> Tuple[List[MetricDetail], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Computes all 11 comparison metrics C1 to C11.
    Also returns warped_source_mask and usable_overlap_mask.
    """
    h_s, w_s = src_dims
    h_r, w_r = ref_dims
    M = len(candidates)
    min_ns_nr = min(Ns, Nr) if min(Ns, Nr) > 0 else 1

    e0 = config.error_scale_e0
    r0 = config.error_scale_r0

    metrics: List[MetricDetail] = []
    warped_src_mask = None
    usable_overlap = None

    # Determine if alignment was successful using configurable support gate
    is_aligned = (affine_mat is not None and nin >= config.min_inliers)

    # C1: Overlap percentage
    # C2: Usable overlap fraction
    overlap_bbox = None
    if is_aligned:
        # Transform source footprint corners [0,0], [w_s,0], [w_s,h_s], [0,h_s]
        src_corners = np.float32([[0, 0], [w_s, 0], [w_s, h_s], [0, h_s]]).reshape(-1, 1, 2)
        trans_corners = cv2.transform(src_corners, affine_mat).reshape(-1, 2)

        # Warp full source bounds mask (geometric support)
        full_src_mask = np.ones((h_s, w_s), dtype=np.uint8) * 255
        warped_geom_support = cv2.warpAffine(full_src_mask, affine_mat, (w_r, h_r), flags=cv2.INTER_NEAREST) > 0

        # Warp valid mask
        warped_src_mask = cv2.warpAffine(
            src_valid_mask.astype(np.uint8) * 255,
            affine_mat,
            (w_r, h_r),
            flags=cv2.INTER_NEAREST
        ) > 0

        # Shared geometric support = warped_geom_support inside ref raster bounds
        area_fs_inter_fr = float(np.sum(warped_geom_support))
        det_A = abs(affine_mat[0, 0] * affine_mat[1, 1] - affine_mat[0, 1] * affine_mat[1, 0])
        area_fs_in_ref = float(h_s * w_s * det_A) if det_A > 0 else float(h_s * w_s)
        overlap_pct = float(np.clip(100.0 * area_fs_inter_fr / area_fs_in_ref, 0.0, 100.0))

        # Usable overlap = shared valid support / shared geometric support
        usable_overlap = warped_src_mask & ref_valid_mask
        area_shared_valid = float(np.sum(usable_overlap))
        usable_frac = float(100.0 * area_shared_valid / area_fs_inter_fr) if area_fs_inter_fr > 0 else 0.0

        if area_shared_valid > 0:
            ys, xs = np.where(usable_overlap)
            overlap_bbox = [int(np.min(xs)), int(np.min(ys)), int(np.max(xs)), int(np.max(ys))]

        m_c1 = MetricDetail(
            metric_code="C1",
            name="Overlap percentage",
            stage="comparison",
            image_role="pair",
            raw_value=round(overlap_pct, 1),
            raw_unit="%",
            display_index=round(overlap_pct, 1),
            index_label="Overlap index",
            formula_id="C1",
            formula_text="O = 100 × Area(F_s ∩ F_r) / Area(F_s); Index = O",
            substituted_inputs={"Area_intersect": area_fs_inter_fr, "Area_source": round(area_fs_in_ref, 1)},
            numerator=area_fs_inter_fr,
            denominator=round(area_fs_in_ref, 1),
            availability=True,
            provenance="Transformed source support intersected with reference image grid"
        )

        m_c2 = MetricDetail(
            metric_code="C2",
            name="Usable overlap fraction",
            stage="comparison",
            image_role="pair",
            raw_value=round(usable_frac, 1),
            raw_unit="%",
            display_index=round(usable_frac, 1),
            index_label="Usable-support index",
            formula_id="C2",
            formula_text="U = 100 × Area(shared valid) / Area(shared geometric); Index = U",
            substituted_inputs={"shared_valid_pixels": int(area_shared_valid), "geometric_overlap_pixels": int(area_fs_inter_fr)},
            numerator=area_shared_valid,
            denominator=area_fs_inter_fr,
            availability=True,
            provenance="Intersection of warped source valid mask with reference valid mask"
        )
    else:
        m_c1 = MetricDetail(
            metric_code="C1",
            name="Overlap percentage",
            stage="comparison",
            image_role="pair",
            raw_value=None,
            raw_unit="%",
            display_index=None,
            index_label="Overlap index",
            formula_id="C1",
            formula_text="O = 100 × Area(F_s ∩ F_r) / Area(F_s)",
            availability=False,
            unavailable_reason="Inconclusive alignment: cannot transform source footprint",
            provenance="Image-space bounds"
        )
        m_c2 = MetricDetail(
            metric_code="C2",
            name="Usable overlap fraction",
            stage="comparison",
            image_role="pair",
            raw_value=None,
            raw_unit="%",
            display_index=None,
            index_label="Usable-support index",
            formula_id="C2",
            formula_text="U = 100 × Area(shared valid) / Area(shared geometric)",
            availability=False,
            unavailable_reason="Inconclusive alignment: no geometric overlap defined",
            provenance="Mask intersection"
        )

    # C3: Candidate match count
    c3_idx = float(np.clip(100.0 * M / min_ns_nr, 0.0, 100.0)) if min_ns_nr > 0 else 0.0
    m_c3 = MetricDetail(
        metric_code="C3",
        name="Candidate match count",
        stage="comparison",
        image_role="pair",
        raw_value=float(M),
        raw_unit="pairs",
        display_index=round(c3_idx, 1),
        index_label="Candidate-utilization index",
        formula_id="C3",
        formula_text="M = count(candidates); Index = 100 M / min(N_s, N_r)",
        substituted_inputs={"M": M, "N_s": Ns, "N_r": Nr, "min(N_s, N_r)": min_ns_nr},
        numerator=float(M),
        denominator=float(min_ns_nr),
        availability=True,
        provenance="Unique one-to-one pairs passing descriptor ratio filter"
    )

    # C4: Inlier count
    c4_idx = float(np.clip(100.0 * nin / min_ns_nr, 0.0, 100.0)) if min_ns_nr > 0 else 0.0
    m_c4 = MetricDetail(
        metric_code="C4",
        name="Inlier count",
        stage="comparison",
        image_role="pair",
        raw_value=float(nin),
        raw_unit="inliers",
        display_index=round(c4_idx, 1),
        index_label="Verified-feature utilization index",
        formula_id="C4",
        formula_text="N_in = count(accepted inliers); Index = 100 N_in / min(N_s, N_r)",
        substituted_inputs={"N_in": nin, "min(N_s, N_r)": min_ns_nr},
        numerator=float(nin),
        denominator=float(min_ns_nr),
        availability=True,
        provenance="Pairs accepted by robust geometric verification"
    )

    # C5: Inlier ratio
    c5_val = float(100.0 * nin / M) if M > 0 else 0.0
    m_c5 = MetricDetail(
        metric_code="C5",
        name="Inlier ratio",
        stage="comparison",
        image_role="pair",
        raw_value=round(c5_val, 1) if M > 0 else None,
        raw_unit="%" if M > 0 else "",
        display_index=round(c5_val, 1) if M > 0 else None,
        index_label="Inlier-agreement index",
        formula_id="C5",
        formula_text="R_in = 100 N_in / M; Index = R_in",
        substituted_inputs={"N_in": nin, "M": M},
        numerator=float(nin),
        denominator=float(M) if M > 0 else None,
        availability=(M > 0),
        unavailable_reason=None if M > 0 else "Zero candidate pairs (M=0)",
        provenance="Geometric agreement among proposed candidate pairs"
    )

    # C6: Inlier spatial coverage
    if is_aligned and usable_overlap is not None and np.sum(usable_overlap) > 0:
        gr, gc = config.grid_rows, config.grid_cols
        cell_h = h_r / gr
        cell_w = w_r / gc
        eligible_cells = 0
        occupied_cells = 0

        # Accepted inlier points in reference coordinates
        inlier_ref_pts = [(c["ref_x"], c["ref_y"]) for c in candidates if c["is_inlier"]]

        for r in range(gr):
            for col in range(gc):
                y0, y1 = int(r * cell_h), int((r + 1) * cell_h)
                x0, x1 = int(col * cell_w), int((col + 1) * cell_w)
                cell_overlap = usable_overlap[y0:y1, x0:x1]
                if np.sum(cell_overlap) > 0:
                    eligible_cells += 1
                    # Check if any inlier falls inside this cell
                    has_point = any(x0 <= pt[0] < x1 and y0 <= pt[1] < y1 for pt in inlier_ref_pts)
                    if has_point:
                        occupied_cells += 1

        coverage_pct = float(100.0 * occupied_cells / eligible_cells) if eligible_cells > 0 else 0.0
        m_c6 = MetricDetail(
            metric_code="C6",
            name="Inlier spatial coverage",
            stage="comparison",
            image_role="pair",
            raw_value=round(coverage_pct, 1),
            raw_unit="%",
            display_index=round(coverage_pct, 1),
            index_label="Coverage index",
            formula_id="C6",
            formula_text="Coverage = 100 N_occupied / N_eligible; Index = Coverage",
            substituted_inputs={"N_occupied": occupied_cells, "N_eligible": eligible_cells, "grid": f"{gr}x{gc}"},
            numerator=float(occupied_cells),
            denominator=float(eligible_cells),
            availability=True,
            provenance=f"Uniform {gr}x{gc} grid partitioned over reference coordinates"
        )
    else:
        m_c6 = MetricDetail(
            metric_code="C6",
            name="Inlier spatial coverage",
            stage="comparison",
            image_role="pair",
            raw_value=None,
            raw_unit="%",
            display_index=None,
            index_label="Coverage index",
            formula_id="C6",
            formula_text="Coverage = 100 N_occupied / N_eligible",
            availability=False,
            unavailable_reason="No usable overlap grid cells defined",
            provenance="Grid cell occupancy"
        )

    # C7: Median geometric residual
    if med_res is not None:
        c7_idx = float(np.clip(100.0 / (1.0 + med_res / e0), 0.0, 100.0))
        m_c7 = MetricDetail(
            metric_code="C7",
            name="Median geometric residual",
            stage="comparison",
            image_role="pair",
            raw_value=round(med_res, 2),
            raw_unit="ref pixels",
            display_index=round(c7_idx, 1),
            index_label="Residual consistency index",
            formula_id="C7",
            formula_text="E_med = median(e_i); Index = 100 / (1 + E_med / e0)",
            substituted_inputs={"E_med": round(med_res, 2), "e0_anchor": e0},
            numerator=100.0,
            denominator=round(1.0 + med_res / e0, 3),
            availability=True,
            provenance=f"Median Euclidean error of accepted inliers using anchor e0={e0} px"
        )
    else:
        m_c7 = MetricDetail(
            metric_code="C7",
            name="Median geometric residual",
            stage="comparison",
            image_role="pair",
            raw_value=None,
            raw_unit="ref pixels",
            display_index=None,
            index_label="Residual consistency index",
            formula_id="C7",
            formula_text="Index = 100 / (1 + E_med / e0)",
            availability=False,
            unavailable_reason="Inconclusive alignment: no accepted inliers",
            provenance="Fitting consistency"
        )

    # C8: Independent checkpoint RMSE
    if is_aligned and checkpoints and len(checkpoints) > 0:
        cp_errors = []
        for cp in checkpoints:
            sp = np.array([cp["source_x"], cp["source_y"], 1.0])
            pred_q = affine_mat @ sp
            res = float(np.linalg.norm(np.array([cp["ref_x"], cp["ref_y"]]) - pred_q))
            cp["pred_ref_x"] = float(pred_q[0])
            cp["pred_ref_y"] = float(pred_q[1])
            cp["residual"] = round(res, 2)
            cp_errors.append(res ** 2)

        rmse = float(np.sqrt(np.mean(cp_errors)))
        c8_idx = float(np.clip(100.0 / (1.0 + rmse / r0), 0.0, 100.0))
        m_c8 = MetricDetail(
            metric_code="C8",
            name="Independent checkpoint RMSE",
            stage="comparison",
            image_role="pair",
            raw_value=round(rmse, 2),
            raw_unit="ref pixels",
            display_index=round(c8_idx, 1),
            index_label="Checkpoint error index",
            formula_id="C8",
            formula_text="RMSE = √[(1/K) Σ c_j²]; Index = 100 / (1 + RMSE / r0)",
            substituted_inputs={"K_checkpoints": len(checkpoints), "RMSE": round(rmse, 2), "r0_anchor": r0},
            numerator=100.0,
            denominator=round(1.0 + rmse / r0, 3),
            availability=True,
            provenance=f"Calculated on {len(checkpoints)} withheld independent checkpoints"
        )
    else:
        m_c8 = MetricDetail(
            metric_code="C8",
            name="Independent checkpoint RMSE",
            stage="comparison",
            image_role="pair",
            raw_value=None,
            raw_unit="ref pixels",
            display_index=None,
            index_label="Checkpoint error index",
            formula_id="C8",
            formula_text="Index = 100 / (1 + RMSE / r0)",
            availability=False,
            unavailable_reason="Not independently verified (no trusted checkpoints provided)",
            provenance="Withheld checkpoint pairs"
        )

    # C9: Sun direction difference
    if (src_meta and src_meta.sun_vector and len(src_meta.sun_vector) == 3 and
        ref_meta and ref_meta.sun_vector and len(ref_meta.sun_vector) == 3):
        v_s = np.array(src_meta.sun_vector, dtype=float)
        v_r = np.array(ref_meta.sun_vector, dtype=float)
        norm_s = np.linalg.norm(v_s)
        norm_r = np.linalg.norm(v_r)
        if norm_s > 0 and norm_r > 0:
            u_s = v_s / norm_s
            u_r = v_r / norm_r
            dot_prod = float(np.clip(np.dot(u_s, u_r), -1.0, 1.0))
            delta_s_deg = float(np.arccos(dot_prod) * 180.0 / np.pi)
            c9_idx = float(np.clip(100.0 * (1.0 - delta_s_deg / 180.0), 0.0, 100.0))
            m_c9 = MetricDetail(
                metric_code="C9",
                name="Sun direction difference",
                stage="comparison",
                image_role="pair",
                raw_value=round(delta_s_deg, 1),
                raw_unit="deg",
                display_index=round(c9_idx, 1),
                index_label="Solar-direction similarity index",
                formula_id="C9",
                formula_text="ΔS = acos(s_s · s_r) × 180/π; Index = 100(1 - ΔS/180)",
                substituted_inputs={"ΔS": round(delta_s_deg, 1), "dot_product": round(dot_prod, 4)},
                numerator=round(180.0 - delta_s_deg, 1),
                denominator=180.0,
                availability=True,
                provenance="Unit Sun vectors from supplied observation metadata"
            )
        else:
            m_c9 = MetricDetail(
                metric_code="C9",
                name="Sun direction difference",
                stage="comparison",
                image_role="pair",
                raw_value=None,
                raw_unit="deg",
                display_index=None,
                index_label="Solar-direction similarity index",
                formula_id="C9",
                formula_text="Index = 100(1 - ΔS/180)",
                availability=False,
                unavailable_reason="Invalid Sun vector magnitude in metadata",
                provenance="Observation metadata"
            )
    else:
        m_c9 = MetricDetail(
            metric_code="C9",
            name="Sun direction difference",
            stage="comparison",
            image_role="pair",
            raw_value=None,
            raw_unit="deg",
            display_index=None,
            index_label="Solar-direction similarity index",
            formula_id="C9",
            formula_text="Index = 100(1 - ΔS/180)",
            availability=False,
            unavailable_reason="Metadata not supplied: requires 3D solar vectors",
            provenance="Observation metadata"
        )

    # C10: Sun elevation difference
    if (src_meta and src_meta.solar_elevation_deg is not None and
        ref_meta and ref_meta.solar_elevation_deg is not None):
        e_s = src_meta.solar_elevation_deg
        e_r = ref_meta.solar_elevation_deg
        delta_e = abs(e_s - e_r)
        c10_idx = float(np.clip(100.0 * (1.0 - delta_e / 180.0), 0.0, 100.0))
        m_c10 = MetricDetail(
            metric_code="C10",
            name="Sun elevation difference",
            stage="comparison",
            image_role="pair",
            raw_value=round(delta_e, 1),
            raw_unit="deg",
            display_index=round(c10_idx, 1),
            index_label="Solar-elevation similarity index",
            formula_id="C10",
            formula_text="ΔE = |E_s - E_r|; Index = 100(1 - ΔE/180)",
            substituted_inputs={"E_s": e_s, "E_r": e_r, "ΔE": round(delta_e, 1)},
            numerator=round(180.0 - delta_e, 1),
            denominator=180.0,
            availability=True,
            provenance="Solar elevation angles from supplied observation metadata"
        )
    else:
        m_c10 = MetricDetail(
            metric_code="C10",
            name="Sun elevation difference",
            stage="comparison",
            image_role="pair",
            raw_value=None,
            raw_unit="deg",
            display_index=None,
            index_label="Solar-elevation similarity index",
            formula_id="C10",
            formula_text="Index = 100(1 - ΔE/180)",
            availability=False,
            unavailable_reason="Metadata not supplied: requires solar elevation angles",
            provenance="Observation metadata"
        )

    # C11: Sampling ratio
    if (src_meta and src_meta.gsd_m and src_meta.gsd_m > 0 and
        ref_meta and ref_meta.gsd_m and ref_meta.gsd_m > 0):
        gsd_s = src_meta.gsd_m
        gsd_r = ref_meta.gsd_m
        r_ratio = max(gsd_s, gsd_r) / min(gsd_s, gsd_r)
        c11_idx = float(np.clip(100.0 / r_ratio, 0.0, 100.0))
        m_c11 = MetricDetail(
            metric_code="C11",
            name="Sampling ratio",
            stage="comparison",
            image_role="pair",
            raw_value=round(r_ratio, 2),
            raw_unit="ratio",
            display_index=round(c11_idx, 1),
            index_label="Sampling compatibility index",
            formula_id="C11",
            formula_text="R = max(GSD_s, GSD_r) / min(GSD_s, GSD_r); Index = 100 / R",
            substituted_inputs={"GSD_s": gsd_s, "GSD_r": gsd_r, "R": round(r_ratio, 2)},
            numerator=100.0,
            denominator=round(r_ratio, 2),
            availability=True,
            provenance="Ground sampling distances from observation metadata"
        )
    else:
        m_c11 = MetricDetail(
            metric_code="C11",
            name="Sampling ratio",
            stage="comparison",
            image_role="pair",
            raw_value=None,
            raw_unit="ratio",
            display_index=None,
            index_label="Sampling compatibility index",
            formula_id="C11",
            formula_text="Index = 100 / R",
            availability=False,
            unavailable_reason="Metadata not supplied: requires verified ground sampling distances (GSD)",
            provenance="Observation metadata"
        )

    metrics = [m_c1, m_c2, m_c3, m_c4, m_c5, m_c6, m_c7, m_c8, m_c9, m_c10, m_c11]
    return metrics, warped_src_mask, usable_overlap, overlap_bbox

def render_visual_assets(
    run_dir: str,
    src_gray: np.ndarray,
    ref_gray: np.ndarray,
    src_j: np.ndarray,
    ref_j: np.ndarray,
    src_mask: np.ndarray,
    ref_mask: np.ndarray,
    affine_mat: Optional[np.ndarray],
    candidates: List[Dict[str, Any]],
    usable_overlap: Optional[np.ndarray]
) -> Dict[str, str]:
    """Generates all visual assets and maps file paths relative to assets endpoint."""
    os.makedirs(run_dir, exist_ok=True)
    assets = {}

    h_s, w_s = src_gray.shape[:2]
    h_r, w_r = ref_gray.shape[:2]

    # Preprocessed images
    src_prep_path = os.path.join(run_dir, "source_preprocessed.png")
    ref_prep_path = os.path.join(run_dir, "reference_preprocessed.png")
    cv2.imwrite(src_prep_path, np.round(src_j * 255.0).astype(np.uint8))
    cv2.imwrite(ref_prep_path, np.round(ref_j * 255.0).astype(np.uint8))
    assets["source_preprocessed"] = "source_preprocessed.png"
    assets["reference_preprocessed"] = "reference_preprocessed.png"

    # Masks
    src_mask_path = os.path.join(run_dir, "source_mask.png")
    ref_mask_path = os.path.join(run_dir, "reference_mask.png")
    cv2.imwrite(src_mask_path, (src_mask.astype(np.uint8) * 255))
    cv2.imwrite(ref_mask_path, (ref_mask.astype(np.uint8) * 255))
    assets["source_mask"] = "source_mask.png"
    assets["reference_mask"] = "reference_mask.png"

    # Warped Source and Registered Comparisons (Fixed Reference, Warped OHRC)
    if affine_mat is not None:
        # Warp source valid mask to determine exact valid pixels in reference grid
        warped_src_mask = cv2.warpAffine(
            src_mask.astype(np.uint8) * 255,
            affine_mat,
            (w_r, h_r),
            flags=cv2.INTER_NEAREST
        ) > 0

        # Warp OHRC source into reference coordinate grid exactly once (LRO NAC stays fixed)
        warped_src = cv2.warpAffine(src_gray, affine_mat, (w_r, h_r), flags=cv2.INTER_LINEAR)
        warped_src_norm = np.clip(np.round(warped_src), 0, 255).astype(np.uint8)

        # Create 4-channel BGRA PNG with alpha=0 on invalid warp areas
        alpha_channel = (warped_src_mask.astype(np.uint8) * 255)
        warped_bgra = cv2.merge([warped_src_norm, warped_src_norm, warped_src_norm, alpha_channel])
        warped_src_path = os.path.join(run_dir, "warped_source.png")
        cv2.imwrite(warped_src_path, warped_bgra)
        assets["warped_source"] = "warped_source.png"

        # Zoomed comparison to usable overlap region
        if usable_overlap is not None and np.sum(usable_overlap) > 0:
            ys, xs = np.where(usable_overlap)
            y0, y1 = int(np.min(ys)), int(np.max(ys))
            x0, x1 = int(np.min(xs)), int(np.max(xs))
            pad_x = max(16, int((x1 - x0) * 0.08))
            pad_y = max(16, int((y1 - y0) * 0.08))
            bx0 = max(0, x0 - pad_x)
            bx1 = min(w_r, x1 + pad_x)
            by0 = max(0, y0 - pad_y)
            by1 = min(h_r, y1 + pad_y)

            ref_u8 = np.round(ref_j * 255.0).astype(np.uint8)
            ref_zoomed = ref_u8[by0:by1, bx0:bx1]
            warped_zoomed = warped_bgra[by0:by1, bx0:bx1]

            cv2.imwrite(os.path.join(run_dir, "reference_zoomed.png"), ref_zoomed)
            cv2.imwrite(os.path.join(run_dir, "warped_source_zoomed.png"), warped_zoomed)
            assets["reference_zoomed"] = "reference_zoomed.png"
            assets["warped_source_zoomed"] = "warped_source_zoomed.png"

        # Warped J
        warped_j = cv2.warpAffine(src_j, affine_mat, (w_r, h_r), flags=cv2.INTER_LINEAR)

        # Appearance Difference Map: |ref_j - warped_j| in usable overlap
        diff = np.abs(ref_j - warped_j)
        if usable_overlap is not None:
            diff = diff * usable_overlap.astype(np.float64)
        diff_u8 = np.clip(diff * 255.0 * 2.0, 0, 255).astype(np.uint8)
        diff_color = cv2.applyColorMap(diff_u8, cv2.COLORMAP_INFERNO)
        if usable_overlap is not None:
            diff_color[~usable_overlap] = [18, 18, 24] # dark background
        diff_path = os.path.join(run_dir, "appearance_diff.png")
        cv2.imwrite(diff_path, diff_color)
        assets["appearance_diff"] = "appearance_diff.png"
    else:
        # Inconclusive model: clean up any stale warped or difference files from prior runs
        for stale in ["warped_source.png", "appearance_diff.png", "reference_zoomed.png", "warped_source_zoomed.png"]:
            p = os.path.join(run_dir, stale)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    # Side-by-side Match Lines: Candidates (Red) & Inliers (Green)
    max_h = max(h_s, h_r)
    canvas_w = w_s + w_r
    match_canvas = np.zeros((max_h, canvas_w, 3), dtype=np.uint8)

    src_rgb = cv2.cvtColor(np.round(src_j * 255.0).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    ref_rgb = cv2.cvtColor(np.round(ref_j * 255.0).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    match_canvas[:h_s, :w_s] = src_rgb
    match_canvas[:h_r, w_s:canvas_w] = ref_rgb

    # Draw rejected candidates in red, inliers in lime green
    for c in candidates:
        pt_s = (int(round(c["source_x"])), int(round(c["source_y"])))
        pt_r = (int(round(c["ref_x"] + w_s)), int(round(c["ref_y"])))
        if c["is_inlier"]:
            cv2.line(match_canvas, pt_s, pt_r, (46, 213, 115), 1, cv2.LINE_AA) # vibrant green
            cv2.circle(match_canvas, pt_s, 3, (46, 213, 115), -1)
            cv2.circle(match_canvas, pt_r, 3, (46, 213, 115), -1)
        else:
            cv2.line(match_canvas, pt_s, pt_r, (255, 71, 87), 1, cv2.LINE_AA) # coral red
            cv2.circle(match_canvas, pt_s, 2, (255, 71, 87), -1)
            cv2.circle(match_canvas, pt_r, 2, (255, 71, 87), -1)

    matches_path = os.path.join(run_dir, "matches_visualization.png")
    cv2.imwrite(matches_path, match_canvas)
    assets["matches_visualization"] = "matches_visualization.png"

    # Residual Displacement Map over Reference
    res_canvas = cv2.cvtColor(np.round(ref_j * 255.0).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    for c in candidates:
        if c["is_inlier"] and c.get("pred_ref_x") is not None:
            observed = (int(round(c["ref_x"])), int(round(c["ref_y"])))
            predicted = (int(round(c["pred_ref_x"])), int(round(c["pred_ref_y"])))
            dx = (observed[0] - predicted[0]) * 3
            dy = (observed[1] - predicted[1]) * 3
            target = (predicted[0] + dx, predicted[1] + dy)
            cv2.arrowedLine(res_canvas, predicted, target, (0, 210, 255), 1, tipLength=0.3)
            cv2.circle(res_canvas, observed, 2, (46, 213, 115), -1)

    residuals_path = os.path.join(run_dir, "residuals_map.png")
    cv2.imwrite(residuals_path, res_canvas)
    assets["residuals_map"] = "residuals_map.png"

    return assets
