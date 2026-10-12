import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from app.metadata_parser import (
    parse_metadata_file,
    validate_metadata_against_image,
    parse_pds3_lbl,
    parse_pds4_xml,
    parse_json_metadata
)

class TestMetadataParser(unittest.TestCase):
    def test_pds3_lbl(self):
        lbl = b"""PDS_VERSION_ID = PDS3
RECORD_TYPE = FIXED_LENGTH
RECORD_BYTES = 1024
^IMAGE = "M1143892015LR.IMG"
PRODUCT_ID = "M1143892015LR"
INSTRUMENT_ID = "LROC"
INSTRUMENT_NAME = "LUNAR RECONNAISSANCE ORBITER CAMERA"
START_TIME = 2013-11-20T14:15:22.456
OBJECT = IMAGE
  LINES = 52224
  LINE_SAMPLES = 5064
  SAMPLE_BITS = 12
  SAMPLE_TYPE = LSB_INTEGER
  SCALED_PIXEL_WIDTH = 0.5 <METERS/PIXEL>
END_OBJECT = IMAGE
END
"""
        res = parse_metadata_file("M1143892015LR.LBL", lbl)
        self.assertEqual(res["product_id"], "M1143892015LR")
        self.assertEqual(res["instrument_id"], "LROC")
        self.assertEqual(res["acquisition_time"], "2013-11-20T14:15:22.456")
        self.assertEqual(res["image_filename"], "M1143892015LR.IMG")
        self.assertEqual(res["width"], 5064)
        self.assertEqual(res["height"], 52224)
        self.assertIn("12-bit", res["pixel_data_type"])
        self.assertIn("0.5", res["resolution"])

        status, msg, _ = validate_metadata_against_image(
            res, "reference", "M1143892015LR.png", 5064, 52224
        )
        self.assertEqual(status, "Metadata Matched")

        # Test mismatch if passed as source (OHRC)
        status_bad, _, _ = validate_metadata_against_image(res, "source")
        self.assertEqual(status_bad, "Metadata Mismatch")

    def test_pds4_xml(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1">
  <Identification_Area>
    <logical_identifier>urn:isro:isda:ch2_ohr:data_derived:ch2_ohr_ncp_20200815t053012123</logical_identifier>
    <product_id>CH2_OHR_NCP_20200815T053012123</product_id>
  </Identification_Area>
  <Observation_Area>
    <Time_Coordinates>
      <start_date_time>2020-08-15T05:30:12.123Z</start_date_time>
    </Time_Coordinates>
    <Observing_System>
      <Observing_System_Component>
        <name>OHRC</name>
        <type>Instrument</type>
      </Observing_System_Component>
    </Observing_System>
  </Observation_Area>
  <File_Area_Observational>
    <File>
      <file_name>ch2_ohr_ncp_20200815t053012123.tif</file_name>
    </File>
    <Array_2D_Image>
      <Axis_Array>
        <axis_name>Line</axis_name>
        <elements>12000</elements>
      </Axis_Array>
      <Axis_Array>
        <axis_name>Sample</axis_name>
        <elements>4000</elements>
      </Axis_Array>
      <Element_Array>
        <data_type>SignedMSB2</data_type>
      </Element_Array>
    </Array_2D_Image>
  </File_Area_Observational>
</Product_Observational>
"""
        res = parse_metadata_file("ch2_ohr.xml", xml)
        self.assertEqual(res["product_id"], "CH2_OHR_NCP_20200815T053012123")
        self.assertIn("OHRC", res["instrument_id"])
        self.assertEqual(res["acquisition_time"], "2020-08-15T05:30:12.123Z")
        self.assertEqual(res["image_filename"], "ch2_ohr_ncp_20200815t053012123.tif")
        self.assertEqual(res["width"], 4000)
        self.assertEqual(res["height"], 12000)
        self.assertEqual(res["pixel_data_type"], "SignedMSB2")

        status, msg, _ = validate_metadata_against_image(
            res, "source", "ch2_ohr_ncp_20200815t053012123.tif", 4000, 12000
        )
        self.assertEqual(status, "Metadata Matched")

    def test_json(self):
        js = b"""{
            "product_id": "CH2_OHR_NC2_20200815T053012123_D_IMG",
            "acquisition_date": "2020-08-15T05:30:12Z",
            "gsd_m": 0.25,
            "provenance": "ISRO ISSDC Chandrayaan-2 PDS4 Archive"
        }"""
        res = parse_metadata_file("sample.json", js)
        self.assertEqual(res["product_id"], "CH2_OHR_NC2_20200815T053012123_D_IMG")
        self.assertEqual(res["instrument_id"], "OHRC")
        self.assertEqual(res["acquisition_time"], "2020-08-15T05:30:12Z")
        self.assertEqual(res["resolution"], "0.25 m/px")

if __name__ == "__main__":
    unittest.main()
