import datetime
import json
import os
import unittest

from json_schema import ads_schema_validator

from ingestparser.parsers import ieee


class TestIEEE(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata/")
        self.inputdir = os.path.join(stubdata_dir, "input")
        self.outputdir = os.path.join(stubdata_dir, "output")

    def test_ieee(self):
        filenames = [
            "ieee_example_1",
            "ieee_example_2",
        ]
        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile = os.path.join(self.outputdir, f + ".json")
            parser = ieee.IEEEParser()

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
