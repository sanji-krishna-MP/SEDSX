import cv2, numpy as np, sqlite3, os

conn = sqlite3.connect("backend/data/runs.db")
c = conn.cursor()
run_id = "run_20261012_162213_6a1510"

c.execute("SELECT source_x, source_y, ref_x, ref_y, residual FROM matches WHERE run_id=? AND is_inlier=1", (run_id,))
inliers = c.fetchall()

run_dir = os.path.join("backend/data/runs", run_id)
ref_img = cv2.imread(os.path.join(run_dir, "reference_original"))
src_img = cv2.imread(os.path.join(run_dir, "source_original"))

h_ref, w_ref = ref_img.shape[:2]
h_src, w_src = src_img.shape[:2]

# Create side-by-side visualization of all 59 inliers
canvas_h = max(h_src, h_ref)
canvas_w = w_src + w_ref
canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

canvas[:h_src, :w_src] = src_img
canvas[:h_ref, w_src:w_src+w_ref] = ref_img

# Draw inliers
for i, row in enumerate(inliers):
    sx, sy, rx, ry, res = row
    pt_s = (int(round(sx)), int(round(sy)))
    pt_r = (int(round(rx + w_src)), int(round(ry)))
    
    # Cyan line connecting inlier pairs
    cv2.line(canvas, pt_s, pt_r, (0, 230, 255), 1, cv2.LINE_AA)
    # Lime circles on endpoints
    cv2.circle(canvas, pt_s, 4, (50, 255, 100), -1)
    cv2.circle(canvas, pt_r, 4, (50, 255, 100), -1)

# Bounding boxes
src_pts = np.array([[row[0], row[1]] for row in inliers])
ref_pts = np.array([[row[2], row[3]] for row in inliers])

s_x0, s_y0 = int(np.min(src_pts[:, 0])), int(np.min(src_pts[:, 1]))
s_x1, s_y1 = int(np.max(src_pts[:, 0])), int(np.max(src_pts[:, 1]))
r_x0, r_y0 = int(np.min(ref_pts[:, 0])), int(np.min(ref_pts[:, 1]))
r_x1, r_y1 = int(np.max(ref_pts[:, 0])), int(np.max(ref_pts[:, 1]))

cv2.rectangle(canvas, (s_x0, s_y0), (s_x1, s_y1), (0, 165, 255), 2)
cv2.rectangle(canvas, (r_x0 + w_src, r_y0), (r_x1 + w_src, r_y1), (0, 165, 255), 2)

# Annotations
font = cv2.FONT_HERSHEY_SIMPLEX
cv2.putText(canvas, f"chandrayan.jpg ({w_src}x{h_src}) - Inlier Span: {s_x1-s_x0}x{s_y1-s_y0} px", (30, 40), font, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
cv2.putText(canvas, f"lro.jpg ({w_ref}x{h_ref}) - Inlier Span: {r_x1-r_x0}x{r_y1-r_y0} px", (w_src + 30, 40), font, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
cv2.putText(canvas, f"59 Inliers (cyan lines) | Median Residual: 0.75 px | BBox Spread: 2.65% (Threshold was 3.00%)", (30, canvas_h - 30), font, 0.9, (0, 255, 255), 2, cv2.LINE_AA)

out_path = "backend/data/inliers_59_distribution.png"
cv2.imwrite(out_path, canvas)

# Also copy to artifacts directory
art_dir = r"C:\Users\sanji krishna mp\.gemini\antigravity-ide\brain\a1f09d57-639f-4e6f-9d16-a1a4cf14e3a0"
import shutil
shutil.copy(out_path, os.path.join(art_dir, "inliers_59_distribution.png"))
print("Saved inlier distribution image to:", out_path)
