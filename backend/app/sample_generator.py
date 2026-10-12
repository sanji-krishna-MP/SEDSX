import os
import cv2
import json
import numpy as np
import csv

def generate_lunar_terrain(width: int = 800, height: int = 800, seed: int = 42) -> np.ndarray:
    """Generates a realistic synthetic lunar terrain image with craters, regolith texture and directional lighting."""
    np.random.seed(seed)
    
    # Base regolith micro-roughness (multi-scale noise)
    terrain = np.zeros((height, width), dtype=np.float32)
    for scale in [128, 64, 32, 16, 8, 4]:
        noise = np.random.normal(0, 1, (height // scale + 2, width // scale + 2)).astype(np.float32)
        resized_noise = cv2.resize(noise, (width, height), interpolation=cv2.INTER_CUBIC)
        terrain += resized_noise * (scale / 4.0)

    # Add craters of varying sizes
    num_craters = 45
    for _ in range(num_craters):
        cx = np.random.randint(40, width - 40)
        cy = np.random.randint(40, height - 40)
        radius = np.random.randint(8, 70)
        depth = np.random.uniform(15.0, 60.0)

        # Coordinate grid for crater
        y_grid, x_grid = np.ogrid[:height, :width]
        dist_sq = (x_grid - cx) ** 2 + (y_grid - cy) ** 2
        r_sq = radius ** 2

        # Parabolic crater floor with raised rim
        crater_mask = dist_sq < (radius * 1.5) ** 2
        norm_dist = np.sqrt(dist_sq[crater_mask]) / radius
        
        # Profile: depression inside, rim elevation at norm_dist ~= 1.0, decay outside
        profile = np.zeros_like(norm_dist)
        inside = norm_dist < 1.0
        outside = (norm_dist >= 1.0) & (norm_dist < 1.5)
        profile[inside] = -depth * (1.0 - norm_dist[inside] ** 2) + depth * 0.25 * (norm_dist[inside] ** 4)
        profile[outside] = (depth * 0.3) * (1.0 - (norm_dist[outside] - 1.0) / 0.5) ** 2

        terrain[crater_mask] += profile

    # Simulate directional solar illumination (Sun elevation 35 deg, azimuth 45 deg)
    azimuth_rad = np.radians(45.0)
    elevation_rad = np.radians(35.0)
    sun_dir = np.array([
        np.cos(elevation_rad) * np.cos(azimuth_rad),
        np.cos(elevation_rad) * np.sin(azimuth_rad),
        np.sin(elevation_rad)
    ], dtype=np.float32)

    # Gradient (surface normals)
    gy, gx = np.gradient(terrain)
    # Surface normal vector = [-gx, -gy, 1.0] normalized
    norm = np.sqrt(gx**2 + gy**2 + 1.0)
    nx = -gx / norm
    ny = -gy / norm
    nz = 1.0 / norm

    # Lambertian reflectance: max(0, N · S)
    shading = nx * sun_dir[0] + ny * sun_dir[1] + nz * sun_dir[2]
    shading = np.clip(shading, 0.0, 1.0)

    # Scale to 8-bit digital numbers [20, 240]
    lunar_u8 = np.clip(shading * 200.0 + 25.0, 0, 255).astype(np.uint8)
    return lunar_u8

def create_sample_dataset(output_dir: str):
    """Creates a pair of realistic lunar test images (Source OHRC, Reference LRO NAC), metadata, and checkpoints."""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Generate master high-resolution terrain
    ref_img = generate_lunar_terrain(width=700, height=700, seed=101)
    ref_path = os.path.join(output_dir, "reference_LRO_NAC.png")
    cv2.imwrite(ref_path, ref_img)

    # 2. Apply known ground-truth affine transform to create Source OHRC
    # Rotation 3.5 degrees, Scale 1.02, dx = 35.0, dy = -25.0
    theta = np.radians(3.5)
    s = 1.02
    A_gt = np.array([
        [s * np.cos(theta), -s * np.sin(theta), 35.0],
        [s * np.sin(theta),  s * np.cos(theta), -25.0]
    ], dtype=np.float32)

    # Source dimensions: 650x650
    h_s, w_s = 650, 650
    # Invert affine to map ref coordinates back to source canvas
    A_inv = cv2.invertAffineTransform(A_gt)
    src_img = cv2.warpAffine(ref_img, A_inv, (w_s, h_s), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    # Apply realistic sensor response / slight brightness variation to source
    src_img = np.clip(src_img.astype(np.float32) * 1.08 - 8.0, 0, 255).astype(np.uint8)
    src_path = os.path.join(output_dir, "source_OHRC.png")
    cv2.imwrite(src_path, src_img)

    # 3. Create independent withheld checkpoints (source -> reference)
    checkpoint_points_src = [
        (150.0, 150.0),
        (450.0, 180.0),
        (220.0, 480.0),
        (500.0, 500.0),
        (320.0, 320.0)
    ]
    checkpoints_path = os.path.join(output_dir, "checkpoints.csv")
    with open(checkpoints_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["checkpoint_id", "source_x", "source_y", "reference_x", "reference_y", "provenance", "uncertainty"])
        for i, (sx, sy) in enumerate(checkpoint_points_src, start=1):
            pt_homo = np.array([sx, sy, 1.0], dtype=np.float32)
            ref_pred = A_gt @ pt_homo
            # Add negligible localization jitter (+- 0.2 px) to simulate manual measurement
            rx = float(ref_pred[0] + np.random.uniform(-0.15, 0.15))
            ry = float(ref_pred[1] + np.random.uniform(-0.15, 0.15))
            writer.writerow([f"CP_{i:02d}", sx, sy, round(rx, 2), round(ry, 2), "Withheld manual lunar crater center", "0.2 px"])

    # 4. Source OHRC metadata
    src_metadata = {
        "product_id": "CH2_OHR_NC2_20200815T053012123_D_IMG",
        "acquisition_date": "2020-08-15T05:30:12Z",
        "nodata_value": 0,
        "intensity_scale": 1.0,
        "intensity_offset": 0.0,
        "intensity_units": "DN",
        "intensity_domain": [0.0, 255.0],
        "gsd_m": 0.25,
        "solar_elevation_deg": 38.5,
        "sun_vector": [0.553, 0.553, 0.622],
        "vector_frame": "LUNAR_LOCAL_ENU",
        "provenance": "ISRO ISSDC Chandrayaan-2 PDS4 Archive"
    }
    with open(os.path.join(output_dir, "metadata_source.json"), "w", encoding="utf-8") as f:
        json.dump(src_metadata, f, indent=2)

    # 5. Reference LRO NAC metadata
    ref_metadata = {
        "product_id": "M1143892015LR",
        "acquisition_date": "2013-11-20T14:15:22Z",
        "nodata_value": 0,
        "intensity_scale": 1.0,
        "intensity_offset": 0.0,
        "intensity_units": "DN",
        "intensity_domain": [0.0, 255.0],
        "gsd_m": 0.50,
        "solar_elevation_deg": 35.0,
        "sun_vector": [0.579, 0.579, 0.574],
        "vector_frame": "LUNAR_LOCAL_ENU",
        "provenance": "NASA PDS Lunar Reconnaissance Orbiter LROC Archive"
    }
    with open(os.path.join(output_dir, "metadata_reference.json"), "w", encoding="utf-8") as f:
        json.dump(ref_metadata, f, indent=2)

    print(f"Sample dataset successfully created in: {output_dir}")

if __name__ == "__main__":
    target = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "samples")
    create_sample_dataset(target)
