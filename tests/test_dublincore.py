import datetime
import json
import os
import unittest

from json_schema import ads_schema_validator

from ingestparser.parsers import dubcore


class TestDublinCore(unittest.TestCase):
    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata/")
        self.inputdir = os.path.join(stubdata_dir, "input")
        self.outputdir = os.path.join(stubdata_dir, "output")
        self.maxDiff = None

    def test_dubcore(self):
        filenames = [
            "dubcore_pos_ecrs_002",
            "arxiv_1711_05739",
            "arxiv_0901_2443",
            "arxiv_1711_04702",
            "arxiv_math_0306266",
        ]
        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile = os.path.join(self.outputdir, f + ".json")
            parser = dubcore.DublinCoreParser()

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


class TextDublinCoreMulti(unittest.TestCase):
    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata/")
        self.inputdir = os.path.join(stubdata_dir, "input")
        self.outputdir = os.path.join(stubdata_dir, "output")

    def test_dubcore_multi(self):
        filenames = [
            "arxiv_multi_20230125",
        ]

        parser = dubcore.MultiDublinCoreParser()

        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile_header = os.path.join(self.outputdir, f + "_header.txt")
            test_outfile_noheader = os.path.join(self.outputdir, f + "_noheader.txt")

            with open(test_infile, "r") as fp:
                input_data = fp.read()

            parsed = parser.parse(input_data, header=True)

            with open(test_outfile_header, "r") as fp:
                output_text = fp.read()
                output_data_header = output_text.strip().split("\n\n")

            self.assertEqual(parsed, output_data_header)

            with open(test_outfile_noheader, "r") as fp:
                output_text = fp.read()
                output_data_noheader = output_text.strip().split("\n\n")

            parsed = parser.parse(input_data, header=False)

            self.assertEqual(parsed, output_data_noheader)
