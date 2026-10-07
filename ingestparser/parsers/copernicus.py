import logging

from adsingestp import utils
from adsingestp.ingest_exceptions import (
    MissingAuthorsException,
    MissingTitleException,
    NoSchemaException,
    WrongSchemaException,
    XmlLoadException,
)
from adsingestp.parsers.base import BaseBeautifulSoupParser

logger = logging.getLogger(__name__)


class CopernicusParser(BaseBeautifulSoupParser):
    copernicus_schema = ["http://www.w3.org/1999/xlink", "http://www.w3.org/1998/Math/MathML"]

    author_collaborations_params = {
        "keywords": ["group", "team", "collaboration"],
        "remove_the": False,
    }

    def __init__(self):
        super(BaseBeautifulSoupParser, self).__init__()
        self.base_metadata = {}
        self.input_header = None
        self.input_metadata = None

    def _parse_journal(self):
        if self.input_metadata.find("journal"):
            journal_metadata = self.input_metadata.find("journal")

            if journal_metadata.find("journal_title"):
                self.base_metadata["publication"] = journal_metadata.find(
                    "journal_title"
                ).get_text()

            if journal_metadata.find("volume_number"):
                self.base_metadata["volume"] = journal_metadata.find("volume_number").get_text()

    def _parse_pagination(self):
        if self.input_metadata.find("start_page"):
            self.base_metadata["page_first"] = self.input_metadata.find("start_page").get_text()

        if self.input_metadata.find("end_page"):
            self.base_metadata["page_last"] = self.input_metadata.find("end_page").get_text()

        if self.input_metadata.find("article_number"):
            self.base_metadata["electronic_id"] = self.input_metadata.find(
                "article_number"
            ).get_text()

    def _parse_ids(self):
        self.base_metadata["ids"] = {}

        issns = []
        if self.input_metadata.find("issn"):
            issns.append(("print", self.input_metadata.find("issn").get_text()))

        if self.input_metadata.find("eissn"):
            issns.append(("electronic", self.input_metadata.find("eissn").get_text()))

        self.base_metadata["issn"] = issns

        if self.input_metadata.find("doi"):
            self.base_metadata["ids"]["doi"] = self.input_metadata.find("doi").get_text()

    def _parse_title(self):
        title_array = self.input_metadata.find("article_title").get_text()
        if title_array:
            title_temp = self.bsstrtodict(title_array, "html.parser")
            title = title_temp.get_text().title()

            self.base_metadata["title"] = title

        else:
            raise MissingTitleException("No title found")

    def _parse_author(self):
        author_list = []
        name_parser = utils.AuthorNames()

        affil_map = {}

        # Create a dictionary to map affiliation names to affiliation numbers
        if self.input_metadata.find("affiliations"):
            affil_list = self.input_metadata.find("affiliations").find_all("affiliation")
            for aff in affil_list:
                affil_map[aff.get("numeration", "")] = self._clean_output(aff.get_text())

        author_array = self.input_metadata.find_all("author")
        for a in author_array:
            author_temp = {}
            name = a.find("name").get_text()
            parsed_name = name_parser.parse(
                name, collaborations_params=self.author_collaborations_params
            )
            author_temp = parsed_name[0]

            if a.find("email"):
                author_temp["email"] = a.find("email").get_text()
            if a.find("contrib-id"):
                orcid = a.find("contrib-id").get_text()
                orcid = orcid.replace("http://orcid.org/", "")
                author_temp["orcid"] = orcid

            if a["affiliations"]:
                aff_temp = []
                for author_affil in str(a["affiliations"]).split(","):
                    aff_temp.append(affil_map[author_affil])
                author_temp["aff"] = aff_temp

            author_list.append(author_temp)

        if not author_list:
            raise MissingAuthorsException("No contributors found for")

        self.base_metadata["authors"] = author_list

    def _parse_pubdate(self):
        if self.input_metadata.find("publication_date"):
            self.base_metadata["pubdate_electronic"] = self.input_metadata.find(
                "publication_date"
            ).get_text()
            self.base_metadata["pubdate_print"] = self.input_metadata.find(
                "publication_date"
            ).get_text()

    def _parse_abstract(self):
        abstract = None
        if self.input_metadata.find("abstract"):
            for s in self.input_metadata.find("abstract"):
                abstract_html = s.get_text()

                # Use BS to remove html markup
                abstract_temp = self.bsstrtodict(abstract_html, "html.parser")
                abstract = abstract_temp.get_text()

        if abstract:
            self.base_metadata["abstract"] = self._clean_output(abstract)

    def _parse_references(self):
        if self.input_metadata.find("references") and self.input_metadata.find("references").find(
            "reference"
        ):
            references = []
            for ref in self.input_metadata.find("references").find_all("reference"):
                # output raw XML for reference service to parse later
                ref_xml = str(ref.extract()).replace("\n", " ")
                references.append(ref_xml)

            self.base_metadata["references"] = references

    def _parse_esources(self):
        links = []
        if self.input_metadata.find("fulltext_pdf"):
            links.append(("pub_pdf", self.input_metadata.find("fulltext_pdf").get_text()))
        if self.input_metadata.find("abstract_html"):
            links.append(("pub_html", self.input_metadata.find("abstract_html").get_text()))

        self.base_metadata["esources"] = links

    def parse(self, text):
        """
        Parser for Copernicus Publishing

        Parse Copernicus XML into standard JSON format
        :param text: string, contents of XML file
        :return: parsed file contents in JSON format
        """
        try:
            d = self.bsstrtodict(text, parser="lxml-xml")
        except Exception as err:
            raise XmlLoadException(err)

        try:
            self.input_metadata = d.find("article")
        except Exception as err:
            raise NoSchemaException(err)

        schema = self.input_metadata.get("xmlns:xlink", "")
        if schema not in self.copernicus_schema:
            raise WrongSchemaException('Unexpected XML schema "%s"' % schema)

        self._parse_journal()
        self._parse_ids()
        self._parse_title()
        self._parse_author()
        self._parse_pubdate()
        self._parse_pagination()
        self._parse_abstract()
        self._parse_references()
        self._parse_esources()

        self.base_metadata = self._entity_convert(self.base_metadata)

        output = self.format(self.base_metadata, format="Copernicus")

        return output
