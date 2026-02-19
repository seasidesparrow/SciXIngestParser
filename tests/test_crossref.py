import datetime
import json
import os
import unittest

from adsingestschema import ads_schema_validator

from ingestparser.parsers import crossref


class TestCrossref(unittest.TestCase):
    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata/")
        self.inputdir = os.path.join(stubdata_dir, "input")
        self.outputdir = os.path.join(stubdata_dir, "output")
        self.maxDiff = None

    def test_crossref(self):
        filenames = [
            "crossref_10.1002_1521-3994",
            "crossref_10.3847_2041-8213",
            "crossref_conf_10.1049-cp.2010.1342",
            "crossref_conf_10.1109-MWSYM.2013.6697399",
            "crossref_book_10.1017-CBO9780511709265",
            "crossref_book_10.1007-978-1-4614-3520-4",
            "crossref_10.1103_PhysRevD_64-117303",
            "crossref_cn_10.1051=0004-6361=202243540",
            "crossref_cn_10.1088=1475-7516=2022=10=098",
            "crossref_cn_10.1093=mnras=stac2975",
            "crossref_cn_10.1093=pasj=psac053",
            "crossref_cn_10.3847=1538-4357=ac8c2f",
            "crossref_10.1146_annurev.energy.25.1.441",
            "crossref_10.3137_a0410105",
            "crossref_preprint_10.1002-essoar.10508651.1",
            "crossref_preprint_10.1002-essoar.10511074.2",
            "crossref_preprint_10.31223-X55K7G",
            "crossref_preprint_10.31223-X5FW25",
            "crossref_preprint_10.31223-X5WD2C",
            "crossref_no_contrib_10.4213_im9580e",
            "crossref_no_contrib_10.3367_UFNe.2022.11.039660",
            "crossref_book_chapter_10.1016_B978-0-12-037311-6.50008-9",
            "crossref_gsa_conf",
            "crossref_editors_encyc_astrobio",
        ]
        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile = os.path.join(self.outputdir, f + ".json")

            parser = crossref.CrossrefParser()

            with open(test_infile, "rb") as fp:
                input_data = fp.read()

            with open(test_outfile, "rb") as fp:
                output_text = fp.read()
                output_data = json.loads(output_text)

            parsed = parser.parse(input_data)

            # make sure this is valid schema
            try:
                ads_schema_validator().validate(parsed)
            except Exception:
                self.fail("Schema validation failed")

            # this field won't match the test data, so check and then discard
            time_difference = datetime.datetime.fromisoformat(
                parsed["recordData"]["parsedTime"]
            ) - datetime.datetime.now(datetime.UTC)
            self.assertTrue(abs(time_difference) < datetime.timedelta(seconds=10))
            parsed["recordData"]["parsedTime"] = ""

            self.assertEqual(parsed, output_data)
