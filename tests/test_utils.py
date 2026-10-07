import unittest

from ingestparser import utils


class TestAuthorNames(unittest.TestCase):
    def setUp(self):
        self.name_parser = utils.AuthorNames()

    def test_parse(self):
        input_authors = [
            "Miller, Elizabeth",
            "Elizabeth Miller",
            "Robert White Smith",
            "M. Power",
            "maria antonia de la paz",
            "bla. bli.",
            "John",
        ]

        expected_authors = [
            {
                "given": "Elizabeth",
                "middle": "",
                "surname": "Miller",
                "suffix": "",
                "prefix": "",
                "nameraw": "Miller, Elizabeth",
            },
            {
                "given": "Elizabeth",
                "middle": "",
                "surname": "Miller",
                "suffix": "",
                "prefix": "",
                "nameraw": "Elizabeth Miller",
            },
            {
                "given": "Robert",
                "middle": "",
                "surname": "White Smith",
                "suffix": "",
                "prefix": "",
                "nameraw": "Robert White Smith",
            },
            {
                "given": "M.",
                "middle": "",
                "surname": "Power",
                "suffix": "",
                "prefix": "",
                "nameraw": "M. Power",
            },
            {
                "given": "maria",
                "middle": "antonia",
                "surname": "de la paz",
                "suffix": "",
                "prefix": "",
                "nameraw": "maria antonia de la paz",
            },
            {
                "given": "bla.",
                "middle": "",
                "surname": "bli.",
                "suffix": "",
                "prefix": "",
                "nameraw": "bla. bli.",
            },
            {
                "given": "John",
                "middle": "",
                "surname": "",
                "suffix": "",
                "prefix": "",
                "nameraw": "John",
            },
        ]

        for idx, i in enumerate(input_authors):
            parsed = self.name_parser.parse(i)

            self.assertEqual(parsed[0], expected_authors[idx])

    def test_parse_collaboration(self):
        input_authors = [
            "The Collaboration: John Stuart",
            "Gaia Collaboration",
            "BICEP/Keck Collaboration: Smith, Jane",
        ]

        # first round, test default collaboration params
        expected_authors = [
            [
                {"nameraw": "The Collaboration", "collab": "Collaboration"},
                {
                    "given": "John",
                    "middle": "",
                    "surname": "Stuart",
                    "suffix": "",
                    "prefix": "",
                    "nameraw": "John Stuart",
                },
            ],
            [{"nameraw": "Gaia Collaboration", "collab": "Gaia Collaboration"}],
            [
                {"nameraw": "BICEP/Keck Collaboration", "collab": "BICEP/Keck Collaboration"},
                {
                    "given": "Jane",
                    "middle": "",
                    "surname": "Smith",
                    "suffix": "",
                    "prefix": "",
                    "nameraw": "Smith, Jane",
                },
            ],
        ]

        for idx, i in enumerate(input_authors):
            parsed = self.name_parser.parse(i)

            self.assertEqual(parsed, expected_authors[idx])

        # turn on fix_arXiv_mixed_collaboration_string param
        input_authors = [
            "Collaboration, Gaia",
            "BICEP/Keck Collaboration: Smith, Jane",
        ]

        # first round, test default collaboration params
        expected_authors = [
            [{"nameraw": "Collaboration, Gaia", "collab": "Gaia Collaboration"}],
            [
                {"nameraw": "BICEP/Keck Collaboration", "collab": "BICEP/Keck Collaboration"},
                {
                    "given": "Jane",
                    "middle": "",
                    "surname": "Smith",
                    "suffix": "",
                    "prefix": "",
                    "nameraw": "Smith, Jane",
                },
            ],
        ]

        for idx, i in enumerate(input_authors):
            parsed = self.name_parser.parse(
                i, collaborations_params={"fix_arXiv_mixed_collaboration_string": True}
            )

            self.assertEqual(parsed, expected_authors[idx])
