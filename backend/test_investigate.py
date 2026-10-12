import sqlite3, json, os

conn = sqlite3.connect("backend/data/runs.db")
c = conn.cursor()
c.execute("SELECT id, source_filename, reference_filename, inlier_count, candidate_count, warnings, config, affine_params, overlap_bbox, median_residual, source_dims, ref_dims FROM runs ORDER BY created_at DESC LIMIT 5")
rows = c.fetchall()
for r in rows:
    print("ID:", r[0])
    print("Files:", r[1], r[2])
    print("Inliers/Candidates:", r[3], r[4])
    print("Warnings:", r[5])
    print("Affine params:", r[7])
    print("Residual:", r[9])
    print("Dims:", r[10], r[11])
    print("---")
