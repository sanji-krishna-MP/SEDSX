"""
Efficient, streaming parser and validator for lunar image metadata files (.xml, .lbl, .json).
Supports:
- PDS4 / ISRO Chandrayaan-2 OHRC XML (streaming iterparse)
- PDS3 / NASA LRO NAC LBL labels (streaming key-value parser)
- JSON metadata manifests (our schema and generic lunar manifests)
"""

import io
import re
import json
import logging
from typing import Optional, Dict, Any, Tuple
import xml.etree.ElementTree as ET

logger = logging.getLogger("metadata_parser")


def _strip_ns(tag: str) -> str:
    """Strip XML namespace prefix if present."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_pds4_xml(source_bytes: bytes) -> Dict[str, Any]:
    """Streaming XML parser for PDS4 and OHRC XML label files.
    Avoids loading image binary blobs or creating massive DOM trees.
    """
    stream = io.BytesIO(source_bytes)
    extracted: Dict[str, Any] = {
        "product_id": None,
        "instrument_id": None,
        "acquisition_time": None,
        "image_filename": None,
        "width": None,
        "height": None,
        "pixel_data_type": None,
        "resolution": None,
        "format": "PDS4 / OHRC XML",
        "raw_fields": {},
    }

    current_axis_name = None
    observing_components = []

    try:
        # Stream parse
        for event, elem in ET.iterparse(stream, events=("start", "end")):
            tag_name = _strip_ns(elem.tag)
            text_val = (elem.text or "").strip()

            if event == "start":
                if tag_name == "Axis_Array":
                    current_axis_name = None
            elif event == "end":
                # Extract key fields
                if tag_name == "product_id":
                    extracted["product_id"] = text_val
                    extracted["raw_fields"]["product_id"] = text_val
                elif tag_name == "logical_identifier" and not extracted["product_id"]:
                    lid = text_val
                    parts = lid.split(":")
                    extracted["product_id"] = parts[-1] if parts else lid
                    extracted["raw_fields"]["logical_identifier"] = lid

                elif tag_name in ("instrument_id", "instrument_name"):
                    if not extracted["instrument_id"]:
                        extracted["instrument_id"] = text_val
                    extracted["raw_fields"][tag_name] = text_val

                elif tag_name in ("name", "observing_system_name"):
                    up = text_val.upper()
                    if "OHRC" in up or "LROC" in up or "NAC" in up or "CAMERA" in up:
                        if not extracted["instrument_id"]:
                            extracted["instrument_id"] = text_val

                elif tag_name in ("start_date_time", "acquisition_date_time", "start_time"):
                    if not extracted["acquisition_time"]:
                        extracted["acquisition_time"] = text_val
                    extracted["raw_fields"]["start_date_time"] = text_val

                elif tag_name in ("file_name", "fileName", "image_name"):
                    if not extracted["image_filename"]:
                        extracted["image_filename"] = text_val
                    extracted["raw_fields"]["file_name"] = text_val

                elif tag_name == "axis_name":
                    current_axis_name = text_val.lower()

                elif tag_name == "elements":
                    try:
                        val = int(text_val)
                        if current_axis_name in ("line", "lines", "height", "row"):
                            extracted["height"] = val
                        elif current_axis_name in ("sample", "samples", "line_samples", "width", "column"):
                            extracted["width"] = val
                    except ValueError:
                        pass

                elif tag_name in ("lines", "height"):
                    try:
                        extracted["height"] = int(text_val)
                    except ValueError:
                        pass

                elif tag_name in ("line_samples", "samples", "width"):
                    try:
                        extracted["width"] = int(text_val)
                    except ValueError:
                        pass

                elif tag_name in ("data_type", "element_data_type"):
                    if not extracted["pixel_data_type"]:
                        extracted["pixel_data_type"] = text_val
                    extracted["raw_fields"]["data_type"] = text_val

                elif tag_name in ("pixel_resolution", "resolution", "map_scale", "ground_sample_distance", "gsd"):
                    if not extracted["resolution"]:
                        extracted["resolution"] = text_val
                    extracted["raw_fields"]["resolution"] = text_val

                # Clear element memory to optimize streaming on large files
                elem.clear()

    except Exception as e:
        logger.warning(f"PDS4 XML parsing interrupted or partial: {e}")

    # Fallbacks from raw fields or product_id inspection
    if not extracted["instrument_id"] and extracted["product_id"]:
        pid = extracted["product_id"].upper()
        if "OHR" in pid or "CH2" in pid:
            extracted["instrument_id"] = "OHRC (Chandrayaan-2)"
        elif "LRO" in pid or "NAC" in pid or pid.startswith("M1"):
            extracted["instrument_id"] = "LRO NAC"

    return extracted


def parse_pds3_lbl(source_bytes: bytes) -> Dict[str, Any]:
    """Streaming key-value parser for PDS3 (.lbl) label files.
    Reads line by line and terminates immediately upon reaching END statement.
    """
    extracted: Dict[str, Any] = {
        "product_id": None,
        "instrument_id": None,
        "acquisition_time": None,
        "image_filename": None,
        "width": None,
        "height": None,
        "pixel_data_type": None,
        "resolution": None,
        "format": "PDS3 LBL",
        "raw_fields": {},
    }

    # Decode as ASCII / Latin-1 text
    text = source_bytes.decode("latin-1", errors="replace")
    lines = text.splitlines()

    current_object = None
    sample_bits = None
    sample_type = None

    kv_regex = re.compile(r"^\s*([A-Za-z0-9_\^:]+)\s*=\s*(.*?)\s*$")

    for line in lines:
        stripped = line.strip()
        if stripped == "END" or stripped == "^END":
            break

        match = kv_regex.match(stripped)
        if not match:
            continue

        key, val = match.groups()
        key = key.upper()
        # Clean quotes and inline units like <METERS/PIXEL>
        clean_val = val.strip().strip('"').strip("'")
        if "/*" in clean_val:
            clean_val = clean_val.split("/*")[0].strip()

        if key == "OBJECT":
            current_object = clean_val.upper()
            continue
        elif key in ("END_OBJECT", "END-OBJECT"):
            current_object = None
            continue

        extracted["raw_fields"][key] = clean_val

        if key == "PRODUCT_ID" and not extracted["product_id"]:
            extracted["product_id"] = clean_val
        elif key in ("INSTRUMENT_ID", "INSTRUMENT_NAME") and not extracted["instrument_id"]:
            extracted["instrument_id"] = clean_val
        elif key in ("START_TIME", "IMAGE_TIME", "START_DATE_TIME") and not extracted["acquisition_time"]:
            extracted["acquisition_time"] = clean_val
        elif key in ("^IMAGE", "FILE_NAME", "^FILE") and not extracted["image_filename"]:
            extracted["image_filename"] = clean_val
        elif key in ("LINES", "IMAGE_LINES") and (current_object in ("IMAGE", None) or extracted["height"] is None):
            try:
                extracted["height"] = int(clean_val.split()[0])
            except (ValueError, IndexError):
                pass
        elif key in ("LINE_SAMPLES", "IMAGE_LINE_SAMPLES") and (current_object in ("IMAGE", None) or extracted["width"] is None):
            try:
                extracted["width"] = int(clean_val.split()[0])
            except (ValueError, IndexError):
                pass
        elif key in ("SAMPLE_BITS", "IMAGE_SAMPLE_BITS"):
            sample_bits = clean_val
        elif key in ("SAMPLE_TYPE", "DATA_TYPE"):
            sample_type = clean_val
        elif key in ("SCALED_PIXEL_WIDTH", "MAP_SCALE", "PIXEL_RESOLUTION", "RESOLUTION"):
            extracted["resolution"] = clean_val

    # Construct pixel data type
    if sample_type and sample_bits:
        extracted["pixel_data_type"] = f"{sample_type} ({sample_bits}-bit)"
    elif sample_bits:
        extracted["pixel_data_type"] = f"{sample_bits}-bit integer"
    elif sample_type:
        extracted["pixel_data_type"] = sample_type

    # Fallback instrument inference
    if not extracted["instrument_id"] and extracted["product_id"]:
        pid = extracted["product_id"].upper()
        if "LROC" in pid or "NAC" in pid or pid.startswith("M1"):
            extracted["instrument_id"] = "LROC-NAC"
        elif "OHR" in pid or "CH2" in pid:
            extracted["instrument_id"] = "OHRC"

    return extracted


def parse_json_metadata(source_bytes: bytes) -> Dict[str, Any]:
    """Parser for JSON metadata files."""
    extracted: Dict[str, Any] = {
        "product_id": None,
        "instrument_id": None,
        "acquisition_time": None,
        "image_filename": None,
        "width": None,
        "height": None,
        "pixel_data_type": None,
        "resolution": None,
        "format": "JSON",
        "raw_fields": {},
    }

    data = json.loads(source_bytes.decode("utf-8", errors="replace"))
    extracted["raw_fields"] = data

    # Product ID
    extracted["product_id"] = data.get("product_id") or data.get("productId") or data.get("id")

    # Instrument ID
    inst = data.get("instrument_id") or data.get("instrument") or data.get("instrumentId")
    if not inst:
        prov = str(data.get("provenance") or "").upper()
        pid = str(extracted["product_id"] or "").upper()
        if "CHANDRAYAAN" in prov or "OHRC" in prov or "CH2" in pid or "OHR" in pid:
            inst = "OHRC"
        elif "LRO" in prov or "LROC" in prov or "NAC" in prov or pid.startswith("M1"):
            inst = "LRO NAC"
    extracted["instrument_id"] = inst

    # Acquisition time
    extracted["acquisition_time"] = (
        data.get("acquisition_date")
        or data.get("acquisition_time")
        or data.get("start_time")
        or data.get("date")
    )

    # Image filename
    extracted["image_filename"] = (
        data.get("image_filename")
        or data.get("filename")
        or data.get("file_name")
        or data.get("image_name")
    )

    # Dimensions
    w = data.get("width") or data.get("line_samples") or data.get("samples")
    h = data.get("height") or data.get("lines")
    if w is not None:
        try:
            extracted["width"] = int(w)
        except ValueError:
            pass
    if h is not None:
        try:
            extracted["height"] = int(h)
        except ValueError:
            pass

    # Pixel data type
    pdt = data.get("pixel_data_type") or data.get("pixel_type") or data.get("intensity_units")
    if pdt:
        extracted["pixel_data_type"] = str(pdt)

    # Resolution
    res = data.get("gsd_m") or data.get("resolution") or data.get("pixel_resolution")
    if res is not None:
        extracted["resolution"] = f"{res} m/px" if isinstance(res, (int, float)) else str(res)

    return extracted


def parse_metadata_file(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    """Dispatcher to parse .xml, .lbl, or .json file."""
    fn_lower = filename.lower()
    if fn_lower.endswith(".xml"):
        return parse_pds4_xml(file_bytes)
    elif fn_lower.endswith(".lbl"):
        return parse_pds3_lbl(file_bytes)
    elif fn_lower.endswith(".json"):
        return parse_json_metadata(file_bytes)
    else:
        # Sniff content
        sniff = file_bytes[:500].strip()
        if sniff.startswith(b"<?xml") or sniff.startswith(b"<Product_") or sniff.startswith(b"<"):
            return parse_pds4_xml(file_bytes)
        elif sniff.startswith(b"{"):
            return parse_json_metadata(file_bytes)
        elif b"PDS_VERSION_ID" in sniff or b"RECORD_TYPE" in sniff or b"OBJECT =" in sniff:
            return parse_pds3_lbl(file_bytes)
        raise ValueError(f"Unsupported metadata file format '{filename}'. Please upload .xml, .lbl, or .json")


def validate_metadata_against_image(
    extracted: Dict[str, Any],
    expected_role: str,  # "source" | "reference"
    image_filename: Optional[str] = None,
    image_width: Optional[int] = None,
    image_height: Optional[int] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """Validates metadata against expected role ('source'=OHRC, 'reference'=LRO NAC) and uploaded image.
    Returns:
        (status, status_label, checks_summary)
        Statuses:
        - 'Metadata Matched'
        - 'Metadata Mismatch'
        - 'Invalid Metadata'
        - 'Upload Successful' (partially verified / waiting for image)
    """
    # 1. Basic validity check
    has_ident = bool(extracted.get("product_id") or extracted.get("instrument_id"))
    if not has_ident and not extracted.get("raw_fields"):
        return ("Invalid Metadata", "File contains no readable PDS3/PDS4/JSON metadata fields.", {"valid": False})

    inst = str(extracted.get("instrument_id") or "").upper()
    pid = str(extracted.get("product_id") or "").upper()
    meta_img_fn = str(extracted.get("image_filename") or "").lower()

    mismatches = []
    matches = []

    is_ohrc_inst = any(k in inst or k in pid for k in ["OHRC", "CH2", "CHANDRAYAAN", "TMC"])
    is_lro_inst = any(k in inst or k in pid for k in ["LRO", "LROC", "NAC", "NACL", "NACR"])

    if expected_role == "source":
        # Expect OHRC
        if is_lro_inst and not is_ohrc_inst:
            mismatches.append(f"Instrument '{extracted.get('instrument_id') or pid}' belongs to LRO NAC, not OHRC Source.")
        elif is_ohrc_inst:
            matches.append(f"Instrument matches OHRC ({extracted.get('instrument_id') or 'Chandrayaan-2'}).")
    elif expected_role == "reference":
        # Expect LRO NAC
        if is_ohrc_inst and not is_lro_inst:
            mismatches.append(f"Instrument '{extracted.get('instrument_id') or pid}' belongs to OHRC, not LRO NAC Reference.")
        elif is_lro_inst:
            matches.append(f"Instrument matches LRO NAC ({extracted.get('instrument_id') or 'LROC'}).")

    # 2. Check Image Correspondence if Image is Uploaded
    if image_filename:
        img_fn_clean = image_filename.lower().rsplit(".", 1)[0]
        # Check filename stem match if metadata contains image_filename
        if meta_img_fn:
            meta_fn_clean = meta_img_fn.rsplit(".", 1)[0]
            if (
                meta_fn_clean == img_fn_clean
                or meta_fn_clean in img_fn_clean
                or img_fn_clean in meta_fn_clean
                or (pid.lower() in img_fn_clean and len(pid) > 3)
            ):
                matches.append(f"Image filename matches '{extracted.get('image_filename')}'.")
            else:
                mismatches.append(f"Metadata references '{extracted.get('image_filename')}', but uploaded image is '{image_filename}'.")

    # Dimensions check if image dimensions are provided
    if image_width is not None and image_height is not None:
        mw = extracted.get("width")
        mh = extracted.get("height")
        if mw is not None and mh is not None:
            if mw == image_width and mh == image_height:
                matches.append(f"Raster dimensions match exactly ({mw} × {mh} px).")
            else:
                mismatches.append(f"Declared dimensions ({mw} × {mh}) differ from uploaded raster ({image_width} × {image_height}).")

    checks = {
        "matches": matches,
        "mismatches": mismatches,
        "has_image": bool(image_filename),
    }

    if mismatches:
        return ("Metadata Mismatch", "; ".join(mismatches), checks)
    elif matches and (len(matches) >= 1):
        return ("Metadata Matched", "; ".join(matches), checks)
    else:
        # Partial verification: Valid metadata uploaded, but not yet verified against image
        return ("Upload Successful", "Metadata parsed successfully. Ready for comparison.", checks)


def to_image_metadata_dict(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """Map extracted metadata to ImageMetadata model dict."""
    raw = extracted.get("raw_fields", {}) if isinstance(extracted.get("raw_fields"), dict) else {}
    gsd = None
    res = extracted.get("resolution")
    if res is not None:
        try:
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(res))
            if m:
                gsd = float(m.group(1))
        except Exception:
            pass

    return {
        "product_id": extracted.get("product_id") or raw.get("product_id"),
        "acquisition_date": extracted.get("acquisition_time") or raw.get("acquisition_date"),
        "nodata_value": raw.get("nodata_value", 0),
        "intensity_scale": raw.get("intensity_scale", 1.0),
        "intensity_offset": raw.get("intensity_offset", 0.0),
        "intensity_units": raw.get("intensity_units", extracted.get("pixel_data_type", "DN")),
        "intensity_domain": raw.get("intensity_domain", [0.0, 255.0]),
        "gsd_m": gsd if gsd is not None else raw.get("gsd_m"),
        "solar_elevation_deg": raw.get("solar_elevation_deg"),
        "sun_vector": raw.get("sun_vector"),
        "vector_frame": raw.get("vector_frame", "LUNAR_LOCAL_ENU"),
        "provenance": raw.get("provenance") or f"{extracted.get('instrument_id', 'Lunar')} {extracted.get('format', 'Metadata')}"
    }
