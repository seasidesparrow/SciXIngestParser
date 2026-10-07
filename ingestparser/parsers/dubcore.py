import logging

from adsingestp import utils
from adsingestp.ingest_exceptions import (
    MissingAuthorsException,
    MissingTitleException,
    NoSchemaException,
    WrongSchemaException,
    XmlLoadException,
)
from adsingestp.parsers.base import BaseBeautifulSoupParser, IngestBase

logger = logging.getLogger(__name__)


class MultiDublinCoreParser(IngestBase):
    start_re = r"<record(?!-)[^>]*>"
    end_re = r"</record(?!-)[^>]*>"

    def parse(self, text, header=False):
        """
        Separate multi-record DublinCore XML document into individual XML documents

        :param text: string, input XML text from a multi-record XML document
        :param header: boolean (default: False), set to True to preserve overall
            document header/footer for each separate record's document
        :return: list, each item is the XML of a separate DublinCore document
        """
        output_chunks = []
        for chunk in self.get_chunks(text, self.start_re, self.end_re, head_foot=header):
            output_chunks.append(chunk.strip())

        return output_chunks


class DublinCoreParser(BaseBeautifulSoupParser):
    # Generic Dublin Core parser

    DUBCORE_SCHEMA = ["http://www.openarchives.org/OAI/2.0/oai_dc/"]

    author_collaborations_params = {
        "keywords": ["group", "team", "collaboration"],
        "remove_the": False,
    }

    def __init__(self):
        super(BaseBeautifulSoupParser, self).__init__()
        self.base_metadata = {}
        self.input_header = None
        self.input_metadata = None

    def _parse_ids(self):
        self.base_metadata["ids"] = {}
        self.base_metadata["ids"]["pub-id"] = []

        if self.input_header.find("identifier"):
            for dc_id in self.input_header.find_all("identifier"):
                self.base_metadata["ids"]["pub-id"].append(
                    {"attribute": "urn", "Identifier": dc_id.get_text()}
                )

        doi = None
        if self.input_metadata.find("dc:identifier"):
            for dc_id in self.input_metadata.find_all("dc:identifier"):
                id_text = dc_id.get_text().strip()

                self.base_metadata["ids"]["pub-id"].append(
                    {"attribute": "publisher-id", "Identifier": id_text}
                )

                if "doi.org/" in id_text:
                    # normalize to just the DOI
                    doi = id_text.split("doi.org/")[-1]
        if doi:
            self.base_metadata["ids"]["doi"] = doi

    def _parse_title(self):
        title_array = self.input_metadata.find_all("dc:title")
        if title_array:
            title_array_text = [i.get_text() for i in title_array]
            if len(title_array) == 1:
                self.base_metadata["title"] = self._clean_output(title_array_text[0])
            else:
                self.base_metadata["title"] = self._clean_output(": ".join(title_array_text))
        else:
            raise MissingTitleException("No title found")

    def _parse_author(self):
        authors_out = []
        name_parser = utils.AuthorNames()

        author_array = self.input_metadata.find_all("dc:creator")

        for a in author_array:
            # Get ORCID from id attribute if present
            orcid = a.get("id")
            if orcid and "orcid.org" in orcid:
                # normalize to just the ORCID
                orcid = orcid.split("orcid.org/")[-1]

            author_text = a.get_text()
            parsed_name_list = name_parser.parse(
                author_text,
                collaborations_params=self.author_collaborations_params,
            )

            for author_tmp in parsed_name_list:
                # Get author ORCID if present
                if orcid:
                    author_tmp["orcid"] = orcid
                authors_out.append(author_tmp)

        if not authors_out:
            raise MissingAuthorsException("No contributors found for")

        self.base_metadata["authors"] = authors_out

    def _parse_pubdate(self):
        if self.input_metadata.find("dc:date"):
            self.base_metadata["pubdate_electronic"] = self.input_metadata.find(
                "dc:date"
            ).get_text()

    def _parse_pub(self):
        if self.input_metadata.find("dc:source"):
            self.base_metadata["publication"] = self.input_metadata.find("dc:source").get_text()

        if self.input_metadata.find("dc:publisher"):
            self.base_metadata["publisher"] = self.input_metadata.find("dc:publisher").get_text()

    def _parse_abstract(self):
        desc_array = self.input_metadata.find_all("dc:description")
        # in general, only 'dc:description'[0] is the abstract, the rest are comments
        if desc_array:
            self.base_metadata["abstract"] = self._clean_output(desc_array.pop(0).get_text())

        if desc_array:
            comments_out = []
            for d in desc_array:
                # TODO: FIX
                comments_out.append({"text": self._clean_output(d.get_text())})

            self.base_metadata["comments"] = comments_out

    def _parse_keywords(self):
        keywords_array = self.input_metadata.find_all("dc:subject")

        if keywords_array:
            keywords_out = []
            for k in keywords_array:
                keywords_out.append({"string": k.get_text()})
            self.base_metadata["keywords"] = keywords_out

    def parse(self, text):
        """
        Parse DublinCore XML into standard JSON format
        :param text: string, contents of XML file
        :return: parsed file contents in JSON format
        """
        try:
            d = self.bsstrtodict(text, parser="lxml-xml")
        except Exception as err:
            raise XmlLoadException(err)

        if d.find("record"):
            self.input_header = d.find("record").find("header")

        dc_elem = None
        if d.find("record") and d.find("record").find("metadata"):
            # self.input_metadata = d.find("record").find("metadata").find("oai_dc:dc")
            metadata = d.find("record").find("metadata")
            dc_elem = metadata.find("oai_dc:dc") or metadata.find("oai-dc:dc")

        if dc_elem is None:
            raise NoSchemaException("Unknown record schema.")

        self.input_metadata = dc_elem

        schema_spec = dc_elem.get("xmlns:oai_dc") or dc_elem.get("xmlns:oai-dc") or ""

        if not schema_spec:
            raise NoSchemaException("Unknown record schema.")
        elif schema_spec not in self.DUBCORE_SCHEMA:
            raise WrongSchemaException("Wrong schema.")

        self._parse_ids()
        self._parse_title()
        self._parse_author()
        self._parse_pubdate()
        self._parse_abstract()
        self._parse_keywords()
        self._parse_pub()

        self.base_metadata = self._entity_convert(self.base_metadata)

        output = self.format(self.base_metadata, format="OtherXML")

        return output
