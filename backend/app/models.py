from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class RunConfig(BaseModel):
    intensity_bounds_source: List[float] = Field(default=[0.0, 255.0])
    intensity_bounds_reference: List[float] = Field(default=[0.0, 255.0])
    dark_cutoff: float = Field(default=0.1, description="Normalized dark diagnostic cutoff J < t_dark")
    sift_nfeatures: int = Field(default=2000)
    match_ratio_thresh: float = Field(default=0.75, description="L2 2-NN ambiguity ratio filter threshold")
    ransac_reproj_thresh: float = Field(default=3.0, description="RANSAC geometric residual threshold in pixels")
    grid_rows: int = Field(default=4, description="Spatial coverage grid rows")
    grid_cols: int = Field(default=4, description="Spatial coverage grid cols")
    error_scale_e0: float = Field(default=1.0, description="Declared error anchor e0 for C7 residual consistency")
    error_scale_r0: float = Field(default=1.0, description="Declared error anchor r0 for C8 checkpoint error")
    clahe_enabled: bool = Field(default=False, description="CLAHE experimental branch (disabled by default)")
    min_inliers: int = Field(default=6, description="Configurable support gate: minimum inlier count required for valid alignment (>=4, default 6)")
    min_spatial_spread_ratio: float = Field(default=0.01, description="Configurable support gate: minimum inlier bounding box area ratio relative to image bounds")
    max_affine_condition: float = Field(default=4.0, description="Configurable support gate: maximum singular value ratio (condition number) to prevent extreme shear/tilt")
    min_affine_scale: float = Field(default=0.25, description="Configurable support gate: minimum singular value / scale factor")
    max_affine_scale: float = Field(default=4.0, description="Configurable support gate: maximum singular value / scale factor")

class ImageMetadata(BaseModel):
    product_id: Optional[str] = None
    acquisition_date: Optional[str] = None
    nodata_value: Optional[float] = None
    intensity_scale: Optional[float] = 1.0
    intensity_offset: Optional[float] = 0.0
    intensity_units: Optional[str] = "DN"
    intensity_domain: Optional[List[float]] = None
    gsd_m: Optional[float] = None
    solar_elevation_deg: Optional[float] = None
    sun_vector: Optional[List[float]] = None
    vector_frame: Optional[str] = None
    provenance: Optional[str] = None

class MetricDetail(BaseModel):
    metric_code: str # P1..P9, C1..C11
    name: str
    stage: str # preprocessing | comparison
    image_role: str # source | reference | pair
    raw_value: Optional[float] = None
    raw_unit: str = ""
    display_index: Optional[float] = None
    index_label: str = ""
    formula_id: str = ""
    formula_text: str = ""
    substituted_inputs: Dict[str, Any] = {}
    numerator: Optional[float] = None
    denominator: Optional[float] = None
    availability: bool = True
    unavailable_reason: Optional[str] = None
    provenance: str = "computed"
    extra_data: Optional[Dict[str, Any]] = None # histogram, percentiles, multi-values

class MatchPoint(BaseModel):
    match_index: int
    source_x: float
    source_y: float
    ref_x: float
    ref_y: float
    pred_ref_x: Optional[float] = None
    pred_ref_y: Optional[float] = None
    distance: float
    ambiguity_ratio: float
    is_inlier: bool
    residual: Optional[float] = None
    rejection_reason: Optional[str] = None

class RunSummary(BaseModel):
    id: str
    created_at: str
    status: str # queued, validating, preprocessing, matching, fitting, registering, evaluating, saving, completed, failed, cancelled
    stage_message: str
    timing_ms: Dict[str, float] = {}
    source_filename: str
    reference_filename: str
    source_dims: Optional[List[int]] = None # [height, width]
    ref_dims: Optional[List[int]] = None
    modes: List[str] = ["image"]
    warnings: List[str] = []
    inlier_count: Optional[int] = None
    candidate_count: Optional[int] = None
    median_residual: Optional[float] = None
    overlap_bbox: Optional[List[int]] = None # [x0, y0, x1, y1]
    affine_params: Optional[Dict[str, Any]] = None # scale_x, scale_y, rotation_deg, condition_number
    failure_reason: Optional[str] = None
    config: RunConfig = RunConfig()

class RunFullResponse(BaseModel):
    summary: RunSummary
    metrics: List[MetricDetail] = []
    assets: Dict[str, str] = {}
