import datetime
import json
import os
import unittest

import pytest
from adsingestschema import ads_schema_validator

from ingestparser.parsers import wiley


@pytest.mark.filterwarnings("ignore::bs4.MarkupResemblesLocatorWarning")
class TestWiley(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata/")
        self.inputdir = os.path.join(stubdata_dir, "input")
        self.outputdir = os.path.join(stubdata_dir, "output")

    def test_wiley(self):
        filenames = [
            "wiley_jgra_12057",
            "wiley_jgra_57392",
            "wiley_swe_461",
            "wiley_swe_539",
            "wiley_swe_21103",
            "wiley_subsup_1",
            "wiley_subsup_2",
            "wiley_missing_open_attr",
            "wiley_jgra_58674",
        ]
        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile = os.path.join(self.outputdir, f + ".json")
            parser = wiley.WileyParser()

            with open(test_infile, "rb") as fp:
                input_data = fp.read()

            parsed = parser.parse(input_data)

            with open(test_outfile, "rb") as fp:
                output_text = fp.read()
                output_data = json.loads(output_text)

            # make sure this is valid schema
            try:
                ads_schema_validator().validate(parsed)
            except Exception:
                self.fail("Schema validation failed")
                pass

            # this field won't match the test data, so check and then discard
            time_difference = datetime.datetime.fromisoformat(
                parsed["recordData"]["parsedTime"]
            ) - datetime.datetime.now(datetime.UTC)
            self.assertTrue(abs(time_difference) < datetime.timedelta(seconds=10))

            parsed["recordData"]["parsedTime"] = ""
            self.assertEqual(parsed, output_data)
