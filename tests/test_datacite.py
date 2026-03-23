import datetime
import json
import os
import unittest

from json_schema import ads_schema_validator

from ingestparser.parsers import datacite


class TestDatacite(unittest.TestCase):
    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata/")
        self.inputdir = os.path.join(stubdata_dir, "input")
        self.outputdir = os.path.join(stubdata_dir, "output")
        self.maxDiff = None

    def test_datacite(self):
        filenames = [
            "datacite_schema4.1_example-full",
            "datacite_schema3.1_example-full",
            "datacite_schema4.1_example-software",
            "datacite_schema4_example-habanero-pdsdataset",
            "datacite_null_valueuri",
            "datacite-metadata-sample-v2.0",
            "datacite-ornldaac-kernel2.2-0010",
            "zenodo_test",
            "zenodo_test2",
            "zenodo_test3",
            "zenodo_test4",
        ]
        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile = os.path.join(self.outputdir, f + ".json")
            parser = datacite.DataciteParser()

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
