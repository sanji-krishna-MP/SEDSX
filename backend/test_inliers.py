import sqlite3, json, numpy as np, cv2, os

conn = sqlite3.connect("backend/data/runs.db")
c = conn.cursor()
run_id = "run_20261012_162213_6a1510"

c.execute("SELECT source_x, source_y, ref_x, ref_y, is_inlier, residual FROM matches WHERE run_id=? AND is_inlier=1", (run_id,))
inliers = c.fetchall()
print(f"Total inliers: {len(inliers)}")

src_pts = np.array([[row[0], row[1]] for row in inliers])
ref_pts = np.array([[row[2], row[3]] for row in inliers])

# Source span
src_x_min, src_x_max = np.min(src_pts[:, 0]), np.max(src_pts[:, 0])
src_y_min, src_y_max = np.min(src_pts[:, 1]), np.max(src_pts[:, 1])
src_span_x = src_x_max - src_x_min
src_span_y = src_y_max - src_y_min

# Ref span
ref_x_min, ref_x_max = np.min(ref_pts[:, 0]), np.max(ref_pts[:, 0])
ref_y_min, ref_y_max = np.min(ref_pts[:, 1]), np.max(ref_pts[:, 1])
ref_span_x = ref_x_max - ref_x_min
ref_span_y = ref_y_max - ref_y_min

print(f"Source Inliers X: [{src_x_min:.1f}, {src_x_max:.1f}] (span={src_span_x:.1f} px / 1535 = {src_span_x/1535*100:.1f}%)")
print(f"Source Inliers Y: [{src_y_min:.1f}, {src_y_max:.1f}] (span={src_span_y:.1f} px / 1025 = {src_span_y/1025*100:.1f}%)")
print(f"Ref Inliers X: [{ref_x_min:.1f}, {ref_x_max:.1f}] (span={ref_span_x:.1f} px / 1536 = {ref_span_x/1536*100:.1f}%)")
print(f"Ref Inliers Y: [{ref_y_min:.1f}, {ref_y_max:.1f}] (span={ref_span_y:.1f} px / 1024 = {ref_span_y/1024*100:.1f}%)")

# Spread ratio calculated as (span_x * span_y) / (W * H)
spread_ratio = (ref_span_x * ref_span_y) / (1536 * 1024)
print(f"Current bounding box spread ratio: {spread_ratio:.4f} ({spread_ratio*100:.2f}%)")

# Check convex hull area or standard deviation / dispersion
from scipy.spatial import ConvexHull
try:
    hull = ConvexHull(ref_pts)
    hull_area = hull.volume # In 2D, volume is area
    print(f"Convex hull area: {hull_area:.1f} px^2 ({hull_area / (1536*1024) * 100:.2f}% of image)")
except Exception as e:
    print("Hull error:", e)

# Check image files in run dir
run_dir = os.path.join("backend/data/runs", run_id)
ref_img = cv2.imread(os.path.join(run_dir, "reference_original"))
src_img = cv2.imread(os.path.join(run_dir, "source_original"))
print(f"Ref original shape on disk: {ref_img.shape if ref_img is not None else None}")
print(f"Src original shape on disk: {src_img.shape if src_img is not None else None}")

# Check if there is any resizing done anywhere in image_processing.py
# Let's verify if original matches match the original pixel sizes
print(f"First 5 inliers (src -> ref):")
for i in range(min(5, len(inliers))):
    print(f"  {i}: Src=({inliers[i][0]:.1f}, {inliers[i][1]:.1f}) -> Ref=({inliers[i][2]:.1f}, {inliers[i][3]:.1f}), res={inliers[i][5]:.2f}")
