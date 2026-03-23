import datetime
import json
import os
import unittest

import pytest
from json_schema import ads_schema_validator

from ingestparser.parsers import jats


@pytest.mark.filterwarnings("ignore::bs4.MarkupResemblesLocatorWarning")
class TestJATS(unittest.TestCase):
    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), "stubdata/")
        self.inputdir = os.path.join(stubdata_dir, "input")
        self.outputdir = os.path.join(stubdata_dir, "output")
        self.maxDiff = None

    def test_jats(self):
        filenames = [
            "jats_aip_amjph_90_286",
            "jats_aip_key_headings",
            "jats_aip_key_headings2",
            "jats_aip_native_strip",
            "jats_aip_aipc_2470_040010",
            "jats_spie_jmnmm_1.JMM.21.4.041407",
            "jats_spie_opten_1.OE.62.4.048103",
            "jats_spie_opten_1.OE.62.4.066101",
            "jats_versita_index_tags_1",
            "jats_versita_index_tags_2",
            "jats_versita_index_tags_3",
            "jats_edp_jnwpu_40_96",
            "jats_edp_aa_661_70",
            "jats_nature_41467_2023_Article_40261",
            "jats_nature_natsd_12_7375",
            "jats_nature_natas_tmp",
            "jats_nature_roman_num_1",
            "jats_nature_article_pubdatetype_1",
            "jats_sci_376_521",
            "jats_sci_fix_collab_duplication",
            "jats_springer_AcMSn_s10409-023-23061-x",
            "jats_springer_AcMSn_s10409-023-23086-x",
            "jats_springerEarly_ExA_s10686-023-09907-7",
            "jats_springer_EPJC_s10052-023-11699-1",
            "jats_springer_Natur_s41598-023-38673-x",
            "jats_springer_EPJC_s10052-023-11733-2",
            "jats_springer_ZaMP_s00033-023-02064-z",
            "jats_springer_JHEP_JHEP07_2023_200",
            "jats_springer_AcMSn_s10409-023-23108-x",
            "jats_springer_NatCo_s41467-023-40272-3",
            "jats_springer_cldy_84_1543",
            "jats_springer_jhep_2022_05_05",
            "jats_springer_SoPh_s11207-023-02231-5_mathtex",
            "jats_springer_roman_num_1",
            "jats_springer_Article_collab",
            "jats_springer_article_pubdatetype_2",
            "jats_springer_affil_punctuation_1",
            "jats_springer_badmarkup_1",
            "jats_springer_running_title_in_subtitle",
            "jats_aas_apj_967_1_35",
            "jats_aas_empty_smallcaps_tag_apj_976_1_119",
            "jats_iop_apj_923_1_47",
            "jats_iop_ansnn_12_2_025001",
            "jats_iop_jinst_17_05_P05009",
            "jats_iop_no_contribs",
            "jats_iop_no_orcid_tag",
            "jats_iop_preprint_in_record",
            "jats_iop_blank_affil_removed",
            "jats_iop_blank_affil_removed2",
            "jats_iop_list_embedded_email",
            "jats_iop_malformed_orcid",
            "jats_mnras_493_1_141",
            "jats_mnras_inst_1",
            "jats_pnas_1715554115",
            "jats_pnas_119_2201344119",
            "jats_a+a_multiparagraph_abstract",
            "jats_a+a_subtitle",
            "jats_a+a_nested_collab",
            "jats_iucr_d-60-02355",
            "jats_iucr_d-75-00616",
            "jats_aps_phrvd_106_023001",
            "jats_aps_phrvd_100_052015",
            "jats_aps_phrvx_12_021031",
            "jats_aps_native_authors_1",
            "jats_aps_fix_collab_failure",
            "jats_mdpi_climate-11-00147",
            "jats_mdpi_galaxies-11-00090",
            "jats_mdpi_symmetry-15-00939",
            "jats_mdpi_universe-08-00651",
            "jats_aaas_no_issue_pagecount",
            "jats_ees_affil_punctuation_2",
            "jats_liebert_no_journal_title",
            "jats_liebert_atypon",
            "jats_indersci_url_ident",
            "jats_gsl_unkeyed_xref",
            "jats_gsl_egsp_isbn_type",
            "jats_cjes_2014_0180",
            "jats_csp_weird_affil_problem",
            "jats_ieee_omit_western_name_alternatives",
            "jats_sage_epubppub_date",
        ]

        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile = os.path.join(self.outputdir, f + ".json")
            parser = jats.JATSParser()

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

            parsed["recordData"]["parsedTime"] = ""
            self.assertEqual(parsed, output_data)

    def test_nlm_lxml(self):
        # test parsing with BeautifulSoup parser='lxml'
        filenames = [
            "nlm_iop_apj_859_2_101",
            "nlm_iop_aj_162_1",
            "nlm_iop_aj_158_4_139",
            "nlm_tf_gapfd_116_38",
            "nlm_tf_roman_num_1",
            # "nlm_spie_12.2663387",
            # "nlm_spie_12.2665113",
            # "nlm_spie_12.2663472",
            # "nlm_spie_12.2665157",
            # "nlm_spie_12.2663687",
            # "nlm_spie_12.2665696",
            # "nlm_spie_12.2663029",
            # "nlm_spie_12.2664418",
            # "nlm_spie_12.2690579",
            # "nlm_spie_12.2663066",
            # "nlm_spie_12.2664959",
            # "nlm_spie_12.2663263",
            # "nlm_spie_12.2665099",
        ]
        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile = os.path.join(self.outputdir, f + ".json")
            parser = jats.JATSParser()

            with open(test_infile, "rb") as fp:
                input_data = fp.read()

            parsed = parser.parse(input_data, bsparser="lxml")

            with open(test_outfile, "rb") as fp:
                output_text = fp.read()
                output_data = json.loads(output_text)

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

    def test_jats_cite_context(self):
        filenames = [
            "jats_aj_158_4_139_fulltext",
        ]

        for f in filenames:
            test_infile = os.path.join(self.inputdir, f + ".xml")
            test_outfile = os.path.join(self.outputdir, f + ".json")
            test_outfile_tags = os.path.join(self.outputdir, f + "_tags.json")
            parser = jats.JATSParser()

            with open(test_infile, "rb") as fp:
                input_data = fp.read()

            # Test output as strings
            with open(test_outfile, "rb") as fp:
                output_text = fp.read()
                output_data = json.loads(output_text)
            cite_context = parser.citation_context(input_data)

            self.assertEqual(len(cite_context["unresolved"]), 2)
            self.assertEqual(len(cite_context["resolved"]), 0)
            self.assertEqual(cite_context, output_data)

            cite_context_resolved = parser.citation_context(input_data, resolve_refs=True)

            self.assertEqual(len(cite_context_resolved["unresolved"]), 0)
            self.assertEqual(len(cite_context_resolved["resolved"]), 2)
            self.assertEqual(
                cite_context["unresolved"]["ajab3643bib21"],
                cite_context_resolved["resolved"]["2011Icar..213..564F"],
            )
            self.assertEqual(
                cite_context["unresolved"]["ajab3643bib22"],
                cite_context_resolved["resolved"]["2017Icar..286...94F"],
            )

            # Test output as BeautifulSoup tags
            with open(test_outfile_tags, "rb") as fp:
                output_text = fp.read()
                output_data_tags = json.loads(output_text)
            cite_context = parser.citation_context(input_data, text_output=False)
            self.assertEqual(cite_context, output_data_tags)
