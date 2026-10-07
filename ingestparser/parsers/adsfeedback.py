import json
import logging

from adsingestp import utils
from adsingestp.parsers.base import BaseBeautifulSoupParser

logger = logging.getLogger(__name__)


class ADSFeedbackParser(BaseBeautifulSoupParser):
    def __init__(self, json_string=None):
        super(BaseBeautifulSoupParser, self).__init__()
        if json_string:
            self.data = json.loads(json_string)

    def parse(self, json_string=None, **kwargs):
        if json_string:
            self.data = json.loads(json_string)
        output_metadata = dict()

        simple_fields = [
            "bibcode",
            "abstract",
            "publication",
            "title",
            "authors",
            "comments",
            "keywords",
            "references",
            "publicationDate",
        ]

        for field in simple_fields:
            if self.data.get(field, ""):
                output_metadata[field] = self.data[field]

        # Collection/database:
        if self.data.get("collection", ""):
            collections = self.data["collection"]
            database = list()
            for col in collections:
                if col == "astronomy":
                    database.append("AST")
                elif col == "physics":
                    database.append("PHY")
            if database:
                output_metadata["database"] = database

        # Affiliation and ORCID fields
        affil_list = self.data.get("affiliation", "")
        orcid_list = self.data.get("orcid", "")

        n_affil = len(affil_list)
        n_orcid = len(orcid_list)
        n_auth = len(output_metadata["authors"])

        if n_affil == n_auth:
            if n_orcid == n_affil:
                new_affils = list()
                for affil, orcid in zip(affil_list, orcid_list):
                    if orcid:
                        affil = affil + ' <id system="ORCID">' + orcid + "</id>"
                    new_affils.append(affil)
                affil_list = new_affils

            output_metadata["affiliations"] = affil_list
        else:
            logger.info("Number of affiliations does not match number of authors")

        # Properties / URLs
        # url_types = ['pdf','other','doi','html','arxiv']
        properties = {}
        url_data = self.data.get("urls", "")
        for url in url_data:
            (utype, link) = url.split()
            utype = utype.strip("(").strip(")").upper()
            properties[utype] = link
        if properties:
            output_metadata["properties"] = properties

        # Fix names
        old_names = output_metadata["authors"]
        authparse = utils.AuthorNames()
        new_names = [authparse.parse(name) for name in old_names]
        output_metadata["authors"] = new_names

        return output_metadata
