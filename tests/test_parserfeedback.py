from __future__ import print_function

import json
import os
import unittest

from ingestparser.parsers import adsfeedback


class TestFeedback(unittest.TestCase):
    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata")
        self.inputdir = os.path.join(stubdata_dir, "input/")

    # Test 31
    def test_feedbackform_parser(self):
        filenames = [
            "ads_feedback.json",
            "ads_feedback_escape.json",
        ]
        for file in filenames:
            test_infile = os.path.join(self.inputdir, file)
            with open(test_infile) as fp:
                data = fp.read()
                parser = adsfeedback.ADSFeedbackParser(data)
                test_data = parser.parse()

                data_json = json.loads(data)

                # Read bibcode and affiliation from the input file to check against parsed fields
                output_bibcode = data_json.get("bibcode", "")
                if data_json.get("orcid", "") and data_json.get("affiliation", []):
                    output_affil = []
                    for affil, orcid in zip(
                        data_json.get("affiliation", ""), data_json.get("orcid", "")
                    ):
                        if orcid:
                            output_affil.append(
                                str(affil) + ' <id system="ORCID">' + orcid + "</id>"
                            )
                        else:
                            output_affil = data_json.get("affiliation", [])
                else:
                    output_affil = data_json.get("affiliation", [])

                self.assertEqual(test_data.get("bibcode", ""), output_bibcode)
                self.assertEqual(test_data.get("affiliations", ""), output_affil)
