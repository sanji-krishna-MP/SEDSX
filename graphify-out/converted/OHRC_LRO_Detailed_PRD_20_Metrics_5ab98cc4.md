<!-- converted from OHRC_LRO_Detailed_PRD_20_Metrics.docx -->

OHRC and LRO Image Comparison Product Requirements
Detailed Antigravity implementation specification
Version 2.0   |   12 October 2026   |   User uploaded source and reference
## Product objective
Build a working local web application in which the user uploads a source image and a reference image from their computer. The application reads real image pixels, calculates nine preprocessing metric types for each image, prepares matching copies, establishes terrain correspondences and calculates eleven comparison metric types. It stores the results and displays the original images, registered comparison, metric working and normalized indicators out of 100.
## Authoritative metric scope
This document uses the user’s latest ten-metric comparison table and adds inlier count, giving eleven comparison metrics. Earlier longer lists are superseded. Sun azimuth, elevation, incidence, emission and phase may appear as supporting metadata in the observation panel; they are not additional scored comparison metric types. There are twenty metric types in total, with source and reference values for each preprocessing type.
| Preprocessing metrics 9 | Comparison metrics 11 |
| --- | --- |
| Mean; median; standard deviation | Overlap percentage; usable overlap fraction |
| Histogram; intensity percentiles | Candidate-match count; inlier count; inlier ratio |
| Valid-pixel fraction; dark-pixel fraction | Inlier spatial coverage; median geometric residual |
| Endpoint or saturation fraction; intensity range | Independent checkpoint RMSE |
| Compute separately for each observation | Sun-direction difference; Sun-elevation difference; sampling ratio |

## Interpretation of results out of 100
Always show the original measured value and its unit. Add an explicitly labelled display index out of 100 using the formulas in Sections 7 and 8. Some indices describe brightness position or a fraction, while others describe geometric consistency or illumination similarity. They are not interchangeable and must never be labelled accuracy percentages or probabilities of correct registration. No overall average of all twenty metrics is required.
Missing data produces Not available, never an invented score. Independent checkpoint accuracy is available only with trusted points excluded from fitting. Pixel intensity statistics and individual Sun angles have no universal good value. Matching controls are configurable algorithm parameters, not fixed scientific acceptance standards.
# 1 User journey and input requirements
## Upload page
Provide two distinct upload boxes: Source OHRC and Reference LRO NAC. Each accepts a local file and shows filename, dimensions, dtype and preview after validation. Allow replacement and role swapping before processing. The Run comparison button requires two valid inputs. Explain that any two pictures are accepted technically, but meaningful alignment requires shared terrain and sufficient visible features.
| Input | Required use |
| --- | --- |
| Source and reference images | Mandatory. PNG/JPEG or supported single-band TIFF/GeoTIFF. Preserve original pixels and channels; create matching copies separately. |
| Optional metadata JSON per image | Product ID, date, nodata, intensity scale/offset/units, GSD, solar elevation, Sun vector, vector frame and provenance. A structured manual entry form can supply verified values. |
| Optional masks or crop | Boolean valid mask or selected crop per image. Exclude annotations, borders and declared nodata without discarding genuine black terrain automatically. |
| Optional checkpoints CSV | checkpoint_id, source_x, source_y, reference_x, reference_y, provenance and uncertainty. Coordinates use original un-cropped images. |
| Optional geographic support | Compatible lunar footprint/CRS information or already mapprojected rasters. Unprojected scientific products need a separate camera-model/DEM adapter. |

## Supported modes
Image mode is mandatory: registration occurs in image coordinates and errors are reported in original reference pixels. Solar fields and GSD remain unavailable unless verified metadata is supplied. Geospatial mode is an extension that verifies lunar frames, map projection and scale. Uploading two images alone must not trigger a fictional DEM operation or invent scientific geometry.
## Validation
Check file signature, supported band layout, readable array, dimensions, alpha/mask shape and valid finite values. Configure decoded-pixel and memory limits on the server. All-invalid arrays fail validation; constant arrays return insufficient evidence. A JPG screenshot is not a calibrated scientific raster. Keep missing metadata warnings nonblocking for image-space processing.
# 2 Complete processing workflow

1 Validate uploads. 2 Decode arrays and build masks. 3 Calculate original statistics. 4 Normalize matching copies. 5 Extract features. 6 Generate and filter candidate pairs. 7 Fit and refine a robust transformation. 8 Warp source and masks. 9 Calculate comparison metrics and optional checkpoint error. 10 Compute display indices. 11 Persist results. 12 Present the dashboard.
Background job states: queued, validating, preprocessing, matching, fitting, registering, evaluating, saving and completed. Record timing and stage messages. Failed or cancelled runs retain their available diagnostics. These timings are operational logs, not additional metrics in the twenty-metric scope.
# 3 How the software extracts image data
## Pixels are numbers in an array
Decode the image into a NumPy array using OpenCV IMREAD_UNCHANGED or an appropriate TIFF reader. Grayscale arrays have shape height × width; colour arrays have channels as a third dimension. For an 8-bit grayscale file a stored value commonly lies between 0 and 255. Other dtypes have different ranges. Read the actual dtype; do not force all scientific data to 8-bit.
## Colour conversion
I = 0.299R + 0.587G + 0.114B
For ordinary colour previews, convert to grayscale using this defined approximation. OpenCV decodes BGR order; use the proper conversion. A single-band scientific image bypasses colour conversion.
## Mask and valid intensities
Build valid = finite(image) AND not declared nodata AND user mask AND alpha > 0 where available. For grayscale data, apply nodata in its stored-value domain before scale and offset. Do not interpret zero as invalid unless the product or user declares it. Keep saturation flags separate so saturated fractions can use a documented evaluated-pixel denominator.
original = cv2.imread(path, cv2.IMREAD_UNCHANGED)
# Validate successful decoding and channel layout first.
gray = convert_to_float_grayscale(original)
valid = build_mask(original, metadata, user_mask)
pixels = gray[valid].astype(np.float64)
if pixels.size == 0:
    raise ValueError("No valid pixels")
mean = pixels.mean()
median = np.median(pixels)
std = pixels.std(ddof=0)
q01, q99 = np.quantile(pixels, [0.01, 0.99], method="linear")
hist, edges = np.histogram(pixels, bins=256, range=(a, b))
convert_to_float_grayscale and build_mask above are implementation helpers that must be written with the specified conversion and mask rules. Variables a and b are defined intensity bounds. If scale/offset is present, I_physical = stored × scale + offset, and statistics must state the chosen intensity domain and units.
## What is extracted versus supplied
Image-derived: intensities, masks, histogram, percentiles, feature coordinates and descriptors. Software-derived: candidate pairs, transformation, inlier flags, residuals, usable overlap and coverage. Metadata-derived: Sun geometry, solar elevation, GSD and geographic footprint. Checkpoint input: trusted independently identified corresponding points. Do not infer solar angles or metres per pixel from image brightness.
# 4 Preprocessing metric formulas one to five
For each image, let Iᵢ be valid original intensity, N the valid count and P the full raster pixel count. Compute these statistics before percentile stretching. Matching-copy statistics may also be stored, but label them separately.
## P1 Mean intensity
μ = (1/N) Σᵢ Iᵢ
Inputs: valid original pixel values and count.
Procedure. Sum valid intensities and divide by N. Use float64 accumulation.
Purpose. Describe overall brightness. Do not require source and reference means to be equal.
Display out of 100. Brightness position index = 100(μ − a)/(b − a). Higher means brighter, not better.
## P2 Median intensity
m = middle sorted intensity; average the two middle values for even N
Inputs: valid intensity array.
Procedure. Use NumPy median, preserving the intensity domain.
Purpose. Summarize typical brightness with less influence from extremes.
Display out of 100. Median position index = 100(m − a)/(b − a). It is descriptive, not an accuracy score.
## P3 Intensity standard deviation
σ = √[(1/N) Σᵢ(Iᵢ − μ)²]
Inputs: valid intensities and mean.
Procedure. Use population standard deviation with ddof=0.
Purpose. Describe variation from texture, lighting and noise.
Display out of 100. Variation index = 100 × 2σ/(b − a), for values bounded within [a,b]. More variation is not always better.
## P4 Intensity histogram
hⱼ = Σᵢ 1[Iᵢ belongs to bin j]; bin percentage = 100hⱼ/N
Inputs: valid intensities, bin edges and interval convention.
Procedure. Use 256 bins and save counts and edges. Use a shared intensity domain for comparative plots; last bin includes its upper edge.
Purpose. Inspect distribution, clipping and dynamic range.
Display out of 100. Each bin is displayed as a percentage; all bins sum to 100. A histogram does not have a meaningful single quality score.
## P5 Intensity percentiles
Q_q = quantile(I, q), q ∈ [0,1]
Inputs: valid intensities and requested percentiles.
Procedure. Report Q0.01, Q0.50 and Q0.99 using linear interpolation; store the quantile method.
Purpose. Select robust normalization bounds and describe the intensity distribution.
Display out of 100. Display each percentile intensity as 100(Q_q − a)/(b − a). Distinguish percentile rank from normalized intensity.
# 5 Preprocessing metric formulas six to nine
## P6 Valid pixel fraction
f_valid = 100N/P
Inputs: raster dimensions and valid-pixel mask.
Procedure. Count true mask entries and divide by total pixels. Record mask rules.
Purpose. Measure usable input support.
Display out of 100. Valid-data index = f_valid. A value of 80 means 80% of raster pixels are valid.
## P7 Dark pixel fraction
f_dark = 100 × count(Jᵢ < t_dark)/N
Inputs: normalized valid intensities J and a declared dark diagnostic cutoff.
Procedure. Calculate on the matching-normalized domain. The cutoff is configurable and logged, not a universal shadow threshold.
Purpose. Identify dark regions that may have weak visible evidence; dark texture can still be useful.
Display out of 100. Show dark fraction out of 100. Optionally show bright-support index = 100 − f_dark, clearly descriptive.
## P8 Endpoint or saturation fraction
f_endpoint = 100N_endpoint/N_eval; f_sat = 100N_flagged_sat/N_eval
Inputs: original integer dtype maximum or documented product saturation flags, plus evaluated mask.
Procedure. For endpoint fraction count maximum stored values before enhancement. For actual saturation use product flags; define N_eval to include evaluable saturated pixels and exclude nodata.
Purpose. Flag possible lost brightness detail. Pixel maxima in a PNG are not proof of instrument saturation.
Display out of 100. Show the measured fraction out of 100 and an optional nonclipped index = 100 − fraction. Always identify endpoint versus confirmed saturation.
## P9 Intensity range
I_min = min(I); I_max = max(I); span = I_max − I_min
Inputs: valid original intensities.
Procedure. Store minimum, maximum and span as one metric type.
Purpose. Describe the available intensity span and identify constant images.
Display out of 100. Range utilization index = 100 × span/(b − a). Also show minimum and maximum positions out of 100.
## Intensity bounds for display indices
a and b must represent a documented intensity domain. For ordinary uint8 previews use 0 and 255; for unsigned 16-bit stored intensities use 0 and 65535. Apply declared scale/offset when working in physical units. For signed or floating rasters require a meaningful supplied intensity domain; otherwise keep raw values and show Not available for the intensity index. Record out-of-domain values rather than silently hiding them.
Use consistent bounds to compare two same-domain images. Do not normalize each image’s mean using its own min/max and then imply physical brightness equivalence. Sensors with different responses may not have comparable physical intensities even when their display indices are available.
# 6 Matching preparation and geometric fitting
## Matching normalization
L = Q0.01; U = Q0.99; J = clip((I − L)/(U − L),0,1)
Use each image’s own bounds. Percentiles are configurable processing choices; do not impose a required mean or median.
If U equals L, use valid min/max as a fallback. If that span is also zero, return insufficient evidence. Convert J to uint8 by round(255J) for SIFT. Preserve original arrays. Optional CLAHE is an experimental branch with logged settings, disabled by default; it must not allow nodata to bias local enhancement.
## Feature extraction
Use SIFT detectAndCompute with each valid mask. Each keypoint stores (x,y), scale and orientation; descriptors represent neighbourhood structure. Maintain original dimensions initially. If working copies are resized or cropped, store exact affine coordinate mappings including pixel-centre conventions so match coordinates and the final warp return to original images.
## Descriptor matching
d(a,b) = √[Σₖ(aₖ − bₖ)²]; ambiguity ratio = d₁/d₂
Match floating descriptors with L2 distance. Reject missing descriptors, fewer than two neighbours or a zero second-neighbour distance. Apply a configurable ratio filter and bidirectional one-to-one consistency check.
## Candidate denominator
Candidate-match count means the unique one-to-one pairs that enter geometric verification after preliminary descriptor filtering. Record raw proposals and rejected pairs as diagnostics but do not silently change the denominator used by inlier ratio. Ns and Nr are eligible detected keypoint counts before descriptor filtering.
## Default affine model
q̂ = A p + t
p is a source point, q̂ the predicted reference point, A a 2×2 matrix and t a translation. Estimate robustly, then refine on accepted support. Three noncollinear pairs are the mathematical minimum, not evidence of reliable scene-wide alignment.
## Filtering and status
Robust fitting needs documented algorithm controls. The software shall not claim it is parameter free. A bounded data-dependent refinement cutoff may use T_cut = min(max(kQp(residuals), L_bound), U_bound). This is inspired by ASP reprojection filtering, but its use in 2D image registration is a project adaptation requiring testing. Store effective cutoff and its units. Never keep relaxing controls solely to force success.
Without validated support gates, report Alignment estimated with metrics and a review notice. If the model is singular, nonfinite, unsupported or cannot be estimated, report Inconclusive; unreadable input produces Failed. Independent accuracy remains separate. Warp the original source into the fixed reference grid; bilinear image sampling and nearest-neighbour masks must be recorded.
# 7 Comparison formulas overlap and matching support
## C1 Overlap percentage
O = 100 × Area(Fs ∩ Fr)/Area(Fs)
Inputs: geographic footprints in compatible geometry, or transformed full image bounds.
Procedure. In image mode transform source support into reference coordinates. Include support outside the reference in the denominator. In geospatial mode use suitable lunar area calculations.
Purpose. Measure reference coverage of the source. Identify geographic versus image-space overlap.
Display out of 100. Overlap index = O. This is a coverage percentage, not accuracy.
## C2 Usable overlap fraction
U = 100 × Area(shared valid support)/Area(shared geometric support)
Inputs: geometric overlap and valid masks for both images.
Procedure. Warp the source valid mask and intersect it with the reference mask inside shared geometric bounds. Use consistent area or pixel-area accounting.
Purpose. Measure how much overlap contains usable evidence.
Display out of 100. Usable-support index = U. No overlap gives null, not zero divided by zero.
## C3 Candidate match count
M = count(unique candidate pairs entering verification)
Inputs: filtered one-to-one correspondences and eligible keypoint counts Ns and Nr.
Procedure. Count the exact point pairs passed to the robust estimator.
Purpose. Describe the amount of proposed evidence; more candidates alone is not better.
Display out of 100. Candidate-utilization index = 100M/min(Ns,Nr). This describes feature utilization, not correctness. A zero denominator gives Not available.
## C4 Inlier count
Nin = Σᵢ 1[match i accepted by final geometric verification]
Inputs: final inlier flags, verified pairs and refinement result.
Procedure. Recompute final residuals after refinement and retain the declared verification rule. Store all accepted coordinates.
Purpose. Describe how many correspondences support the fitted alignment.
Display out of 100. Verified-feature utilization index = 100Nin/min(Ns,Nr). Preserve the raw count; this index measures utilization rather than independent accuracy.
## C5 Inlier ratio
Rin = 100Nin/M
Inputs: final inlier count and checked candidate count.
Procedure. Use the same candidate set defined in C3. M=0 returns null with reason.
Purpose. Describe geometric agreement among proposed matches.
Display out of 100. Inlier-agreement index = Rin. High agreement can still be caused by incorrect repetitive patterns.
# 8 Comparison formulas coverage error and conditions
## C6 Inlier spatial coverage
Coverage = 100N_occupied/N_eligible
Inputs: accepted reference-coordinate points, usable-overlap mask and grid definition.
Procedure. Partition the reference into a configurable grid. Declare cell eligibility using overlap support and count cells containing final inliers. Exclude points outside usable overlap.
Purpose. Describe where alignment is constrained; dense clustering in one crater is insufficient.
Display out of 100. Coverage index = Coverage. Store grid shape, cell eligibility rule and counts. If no cells qualify, return null.
## C7 Median geometric residual
eᵢ = ‖qᵢ − T(pᵢ)‖₂; E_med = median(eᵢ)
Inputs: final inlier coordinates and fitted model in original reference pixels.
Procedure. Predict reference locations, subtract observed locations and take Euclidean norms. Report the median of the accepted-match residuals.
Purpose. Measure fitting consistency. It does not independently establish accuracy.
Display out of 100. Residual consistency index = 100/(1 + E_med/e0). e0 is a positive declared error scale in the same units, explained in Section 9.
## C8 Independent checkpoint RMSE
cⱼ = ‖qⱼ − T(pⱼ)‖₂; RMSE = √[(1/K)Σⱼ cⱼ²]
Inputs: K trusted checkpoint pairs excluded from all fitting and final-test model selection.
Procedure. Apply the frozen transformation to original source checkpoint coordinates and compare with trusted reference coordinates.
Purpose. Measure independent alignment error; store count, provenance and uncertainty.
Display out of 100. Checkpoint error index = 100/(1 + RMSE/r0), using a declared positive error scale r0. Without trusted checkpoints, raw value and score are Not independently verified.
## C9 Sun direction difference
ΔS = acos(clip(ŝs · ŝr, −1,1)) × 180/π
Inputs: unit Sun vectors in a common frame at corresponding terrain locations.
Procedure. Normalize vectors and compare only when frames and locations are compatible. Never substitute a simple azimuth subtraction.
Purpose. Describe illumination mismatch, not point-matching accuracy.
Display out of 100. Solar-direction similarity index = 100(1 − ΔS/180). It is an angular similarity display convention.
# 9 Remaining comparison formulas and scoring policy
## C10 Sun elevation difference
ΔE = |Es − Er|
Inputs: source and reference solar elevations in degrees using the same horizon convention.
Procedure. Read verified values or calculate each elevation from its Sun vector and local horizon at corresponding terrain locations.
Purpose. Describe illumination-height mismatch. Equal elevations do not imply equal Sun azimuths.
Display out of 100. Solar-elevation similarity index = 100(1 − ΔE/180), because elevations lie in [−90°,90°]. Label this a geometric display index, not a suitability guarantee.
## C11 Sampling ratio
R = max(GSDs,GSDr)/min(GSDs,GSDr)
Inputs: positive GSDs in the same units, with scene/local meaning and provenance.
Procedure. Use documented comparable sampling. For anisotropic grids show axis-specific ratios as details rather than silently assuming square pixels.
Purpose. Describe sampling mismatch. Resizing a preview does not change the original sensor detail.
Display out of 100. Sampling compatibility index = 100/R. A ratio of 2 gives 50/100; this is not a prediction that registration is 50% accurate.
## Error scale selection
e0 and r0 are normalization anchors, not pass/fail thresholds. At an error equal to the anchor the index is 50; at zero it is 100. Require a named preset, value, unit and rationale. Derive anchors from a stated tolerance/localization uncertainty or a development dataset, then freeze them for comparisons. Do not silently select an anchor from the same run’s own median error.
For an explicitly illustrative UI demonstration a user may select a 1 reference-pixel anchor. It is a display convention, not a validated lunar standard. Production or jury evidence must disclose it. Without a chosen anchor show the raw error and Not configured for its index. Metre indices require valid geospatial scale and an anchor in metres.
## Score interpretation and unavailable data
Clamp valid numeric display indices to [0,100] only after checking domain validity; report out-of-domain inputs. Preserve full precision in storage and show one decimal place in the UI. Histogram and percentile metrics are multi-value outputs; show normalized bins/quantile values rather than inventing a single score. Do not average brightness, feature utilization, geometry and illumination indices into an overall confidence score.
Missing geometry, zero denominator, absent checkpoints or unsupported intensity bounds produce null scores with reasons. The full results table still displays every requested metric. No score is an accuracy percentage, and a high score cannot override an inconclusive transformation.
# 10 Metadata and geometric data requirements
| Data | Expected source and validation |
| --- | --- |
| Dimensions and dtype | Decode image array and compare with label if supplied. Preserve row/column convention and file hash. |
| Intensity units and special values | Label or user metadata: nodata, scale, offset, saturation flags, and declared intensity domain. Store provenance. |
| Sun direction and elevation | Metadata or supporting geometry. Require frame and local horizon conventions; do not derive from brightness. |
| Ground sampling distance | Product/map metadata or verified manual input. Image width alone cannot provide metres per pixel. |
| Footprints and map scale | Validated lunar geospatial support. Otherwise use explicitly labelled image-space support overlap. |
| Trusted checkpoints | Independent CSV or deliberate manual checkpoint annotation kept separate from fitting. Store coordinate frame and uncertainty. |
| Matching geometry | Computed by software: keypoints, descriptors, candidate pairs, inlier flags, model and masks. |

## Sun vector from positions
ŝ = (rSun − rsurface)/‖rSun − rsurface‖
Use positions in a common frame at each acquisition time. Scene-centre values must not be portrayed as local terrain values.
## Solar elevation from local components
E = atan2(sU, √(sE²+sN²)) × 180/π
Components refer to a declared local east, north and up frame. Compare at corresponding terrain positions.
## Supporting raw angles
Az = mod(atan2(sE,sN) × 180/π,360); i = acos(n̂·ŝ); emission = acos(n̂·v̂); phase = acos(ŝ·v̂)
Convert acos results to degrees and clip dot products. n̂ is a unit normal and v̂ points from surface toward camera. Display only where supplied or derived with supported geometry.
## Limits of two image uploads
All nine preprocessing metric types and image-space support measurements can be obtained from readable rasters, subject to declared masks/domain definitions. Solar differences and sampling ratio need metadata. Independent RMSE needs trusted checkpoints. Missing scientific inputs do not block a visual prototype, but they must remain visible as unavailable rather than filled with sample numbers.
# 11 Results page based on the supplied reference

User-provided layout reference. The screenshot contains illustrative imagery and values; the application must generate its own values and visuals from the current uploads.
## Primary layout
Use a dark blue title bar and a light dashboard. Place an evidence sidebar on the left, reference image at the top centre and source image at the top right. Under the two originals place a wide registered comparison with a draggable divider. Align the source to the reference for the divider; a simple divider between unregistered originals is not a registered comparison.
## Evidence sidebar
Prioritize overlap, usable overlap, candidates, inliers, inlier ratio, coverage, median residual and independent RMSE. Show raw values and units plus clearly labelled display indices. Group Sun differences and sampling compatibility beneath them. Supporting raw angles and pixel spacing may appear in an Observation details drawer without expanding the twenty-metric scope.
## Complete metric results
Below the comparison provide Preprocessing, Comparison calculations, Match evidence and Run details tabs. Preprocessing shows nine rows with Source value, Reference value, Difference and Display index for each. Histogram and percentiles expand to charts/multiple values. Comparison calculations shows eleven rows with Raw result, Unit, Display index out of 100, Purpose and availability reason.
## Calculations and visual differences
Clicking a metric opens its formula, substituted actual values, denominator, provenance and index transformation. Toggle original/preprocessed previews, valid masks, accepted/rejected matches and residual arrows. A registered brightness-difference view uses common display normalization and usable-overlap masking; label it appearance difference, since illumination can change intensities even when alignment is correct.
# 12 Stored results API and failure behavior
## Persistence
Every comparison creates a unique run. Store original source/reference, hashes, metadata, masks, intensity arrays or reproducible decoding details, statistics JSON, matching previews, coordinate mappings, candidate/inlier records, transformation, registered source, overlap masks, metric JSON and score configuration. Reopening the page must restore the saved run without recalculation. Configuration changes create a new run linked to the earlier result.
## Metric record
Each metric record contains id, stage, image role or pair, raw_value, raw_unit, frame, formula_id, substituted_inputs, numerator/denominator where applicable, display_index or index array, index_label, index_formula, index_anchor and rationale, availability, unavailable_reason and provenance. Preserve arrays for histograms, percentiles and per-point errors; summarize only for display.
## Match record
Each pair stores source/reference original and working coordinates, descriptor distance/ratio, filtering stage, final inlier flag, residual, rejection reason and keypoint IDs. Store candidate count M explicitly to reproduce the ratio. Checkpoint records are maintained separately and must never be added to fitting correspondences.
| API | Expected behavior |
| --- | --- |
| POST /api/runs | Accept two files, optional metadata/masks/checkpoints and configuration. Return run ID and start background job. |
| GET /api/runs/{id} | Return stage, status, modes, warnings, effective configuration and available assets. |
| GET /api/runs/{id}/metrics | Return all nine per-image and eleven pair metric types with raw values and index details. |
| GET /api/runs/{id}/matches | Return paginated coordinates, inlier flags and residuals. |
| GET /api/runs/{id}/assets/{name} | Serve allowlisted original, processed, registered and report assets. |
| GET /api/runs | Return saved comparison history. |
| POST /api/runs/{id}/cancel | Stop pending work and retain completed stage diagnostics. |

Prevent duplicate processing on refresh, use atomic saves and validate resource limits before allocating decoded arrays or output warps. If fitting fails, keep originals and preprocessing results; show unavailable pair metrics with their reasons. Never use zero to represent missing angles or independent accuracy.
# 13 Worked examples and acceptance checks
| Example | Raw calculation | Display index |
| --- | --- | --- |
| Mean in uint8 domain | Mean = 64; a=0, b=255 | 100×64/255 = 25.1 brightness position |
| Valid fraction | 900 valid / 1000 pixels | 90.0/100 valid-data index |
| Candidate utilization | Ns=400, Nr=500, M=200 | 100×200/400 = 50.0/100 |
| Inlier utilization | Nin=150; min(Ns,Nr)=400 | 37.5/100 verified-feature utilization |
| Inlier ratio | 150 / 200 ×100 | 75.0/100 geometric agreement |
| Spatial coverage | 30 occupied / 40 eligible cells | 75.0/100 coverage |
| Median residual | 0.5 ref pixels; e0=1 ref pixel | 100/(1+0.5/1) = 66.7/100 |
| Sun direction | ΔS=18° | 100(1−18/180) = 90.0/100 |
| Elevation difference | Es=35°, Er=45°; ΔE=10° | 100(1−10/180) = 94.4/100 |
| Sampling ratio | 1.5/0.25 = 6 | 100/6 = 16.7/100 compatibility |

All numbers are arithmetic fixtures, not measurements from the uploaded screenshot. Indices summarize different properties. In particular, 66.7 residual consistency does not mean 66.7% accurate, and 16.7 sampling compatibility does not predict registration failure.
## Required processing tests
Use a known synthetic transform on a textured image with independent withheld points to check coordinates, fitting and checkpoint arithmetic. Test brightness-modified pairs without requiring equal means/medians. Test different resolutions, masked margins, all-invalid and constant images, wrong/nonoverlapping pairs, repeated patterns and missing geometry. Confirm geometric and usable-overlap denominators, grid eligibility and full transformed source support.
## Required display tests
Confirm all twenty types appear; raw units are retained; scores stay within valid domains; histogram percentages sum to 100; percentiles do not become fabricated quality scores; error anchors and provenance are visible; missing fields show reasons. Reopen a saved run and verify identical results. No illustrative screenshot number may appear as a computed value.
# 14 Antigravity build requirements and references
## Implementation stack
Use Next.js, TypeScript and Tailwind for upload/results/history pages; FastAPI for APIs; OpenCV and NumPy for image processing; an appropriate TIFF/GeoTIFF reader when needed; SQLite for local run records and filesystem assets. Process jobs in a background worker, pin tested dependencies and provide setup commands for a local demonstration.
## Build sequence
Phase 1: upload validation, decoding, masks, nine preprocessing metrics and history persistence. Phase 2: normalized copies, SIFT, one-to-one candidate matching, robust affine fitting, original-coordinate warp and image-space comparison metrics. Phase 3: score displays with declared conventions, formula workings, screenshot-inspired dashboard and exports. Phase 4: metadata validation, Sun/GSD outputs and trusted checkpoint evaluation. Keep full scientific mapprojection as a separate extension.
## Acceptance requirement for the coding agent
Implement real calculations from the current uploads. Do not generate fake successful matches, hardcode screenshot values or label normalized indicators as confidence/accuracy. Preserve originals, keep reference fixed, record processing settings and metric provenance, expose missing inputs, and return inconclusive when a credible model cannot be established. Deliver runnable source, pinned dependencies, a README, metadata/checkpoint examples and meaningful arithmetic/geometry tests.
## Evidence supporting the workflow
USGS ISIS documents mean, median, standard deviation, valid counts, saturation categories and minimum/maximum as image statistics. OpenCV documents feature detection, descriptor matching and ratio filtering. ASP documents bounded percentile-based reprojection-error filtering. Those references support the operations; the out-of-100 mappings here are explicitly proposed UI conventions, not scientific standards or validated probabilistic confidence measures.
USGS ISIS image statistics
https://isis.astrogeology.usgs.gov/dev/Application/presentation/Tabbed/stats/stats.html
OpenCV SIFT feature extraction
https://docs.opencv.org/4.12.0/da/df5/tutorial_py_sift_intro.html
OpenCV feature matching
https://docs.opencv.org/4.13.0/dc/dc3/tutorial_py_matcher.html
ASP bundle adjustment and outlier filtering
https://stereopipeline.readthedocs.io/en/stable/tools/bundle_adjust.html
## Delivery definition
The prototype is complete when two uploaded images produce saved preprocessing results, a real estimated alignment or explicit inconclusive outcome, all requested metric rows, available index calculations with disclosed scales, an interactive comparison view and exportable evidence. Scientific accuracy claims require separate independent validation.