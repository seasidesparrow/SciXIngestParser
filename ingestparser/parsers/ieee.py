import logging
import re

from ingestparser import utils
from ingestparser.ingest_exceptions import XmlLoadException
from ingestparser.parsers.base import BaseBeautifulSoupParser

logger = logging.getLogger(__name__)

orcid_format = re.compile(r"(\d{4}-){3}\d{3}(\d|X)")


class IEEEParser(BaseBeautifulSoupParser):
    def __init__(self):
        super(BaseBeautifulSoupParser, self).__init__()
        self.base_metadata = {}
        self.publication = None
        self.publicationinfo = None
        self.volumeinfo = None
        self.article = None

    def _parse_ids(self):
        self.base_metadata["ids"] = {}

        self.base_metadata["issn"] = []
        for i in self.publicationinfo.find_all("issn"):
            self.base_metadata["issn"].append((i["mediatype"], i.get_text()))

        if self.article.find("doi"):
            self.base_metadata["ids"]["doi"] = self.article.find("doi").get_text()

        self.base_metadata["ids"]["pub-id"] = []
        if self.publicationinfo.find("publicationdoi"):
            self.base_metadata["ids"]["pub-id"].append(
                {
                    "attribute": "doi",
                    "Identifier": self.publicationinfo.find("publicationdoi").get_text(),
                }
            )

    def _parse_pub(self):
        if self.publication.find("title"):
            t = self.publication.find("title")
            self.base_metadata["publication"] = self._clean_output(
                self._detag(t, self.HTML_TAGSET["title"]).strip()
            )

        if self.volumeinfo:
            self.base_metadata["volume"] = self.volumeinfo.find("volumenum").get_text()
            self.base_metadata["issue"] = self.volumeinfo.find("issue").find("issuenum").get_text()

    def _parse_page(self):
        n = self.article.find("artpagenums", None)
        if n:
            self.base_metadata["page_first"] = self.base_metadata["page_first"] = self._detag(
                n.get("startpage", None), []
            )
            self.base_metadata["page_last"] = self.base_metadata["page_last"] = self._detag(
                n.get("endpage", None), []
            )

    def _parse_pubdate(self):
        # Look for publication dates in article section
        for date in self.article.find_all("date"):
            date_type = date.get("datetype", "")

            # Get year, month, day values
            if date.find("year"):
                year = date.find("year").get_text()
            else:
                year = "0000"

            if date.find("month"):
                month_raw = date.find("month").get_text()
                if month_raw.isdigit():
                    month = month_raw
                else:
                    month_name = month_raw[0:3].lower()
                    month = utils.MONTH_TO_NUMBER[month_name]
            else:
                month_raw == "00"

            if date.find("day"):
                day = date.find("day").get_text()
            else:
                day = "00"

            # Format date string
            pubdate = year + "-" + month + "-" + day

            # Assign to appropriate metadata field based on date type
            if date_type == "OriginalPub":
                self.base_metadata["pubdate_print"] = pubdate
            elif date_type == "ePub":
                self.base_metadata["pubdate_electronic"] = pubdate

    def _parse_title_abstract(self):
        # Parse title from article section
        if self.article.find("title"):
            self.base_metadata["title"] = self._clean_output(
                self._detag(self.article.find("title"), self.HTML_TAGSET["title"]).strip()
            )

        # Parse abstract from articleinfo section
        if self.article.find("articleinfo"):
            for abstract in self.article.find("articleinfo").find_all("abstract"):
                if abstract.get("abstracttype") == "Regular":
                    self.base_metadata["abstract"] = self._clean_output(
                        self._detag(abstract, self.HTML_TAGSET["abstract"]).strip()
                    )

    def _parse_permissions(self):
        # Check for open-access and permissions information
        if self.article.find("articleinfo"):
            articleinfo = self.article.find("articleinfo")

            # Get copyright holder and year
            if articleinfo.find("articlecopyright"):
                copyright = articleinfo.find("articlecopyright")
                copyright_holder = self._clean_output(copyright.get_text())
                copyright_year = copyright.get("year", "")
                copyright_statement = self._detag(
                    articleinfo.find("article_copyright_statement").get_text(),
                    self.HTML_TAGSET["license"],
                )

                # Format copyright string
                copyright_text = (
                    copyright_year + " " + copyright_holder + ". " + copyright_statement
                )
                self.base_metadata["copyright"] = copyright_text

            # Check if open access is given as "T" (true)
            if articleinfo.find("articleopenaccess"):
                if articleinfo.find("articleopenaccess").get_text() == "T":
                    self.base_metadata.setdefault("openAccess", {}).setdefault("open", True)

    def _parse_authors(self):
        # Parse authors from articleinfo section
        if self.article.find("articleinfo"):
            articleinfo = self.article.find("articleinfo")
            author_list = []

            # Get all authors from authorgroup
            if articleinfo.find("authorgroup"):
                for author in articleinfo.find("authorgroup").find_all("author"):
                    author_tmp = {}

                    # Get author name components
                    if author.find("firstname"):
                        author_tmp["given"] = self._clean_output(
                            author.find("firstname").get_text()
                        )
                    if author.find("surname"):
                        author_tmp["surname"] = self._clean_output(
                            author.find("surname").get_text()
                        )

                    # Get author affiliation
                    if author.find("affiliation"):
                        author_tmp["aff"] = [
                            self._clean_output(author.find("affiliation").get_text())
                        ]
                        author_tmp["xaff"] = []

                    # Get author email
                    if author.find("email"):
                        author_tmp["email"] = self._clean_output(author.find("email").get_text())

                    # Get author ORCID if present
                    if author.find("orcid"):
                        author_tmp["orcid"] = author.find("orcid").get_text()

                    # Check if author is corresponding author
                    if author.get("role") == "corresponding":
                        author_tmp["corresp"] = True

                    author_list.append(author_tmp)

            if author_list:
                self.base_metadata["authors"] = author_list

    def _parse_keywords(self):
        # Parse IEEE keywords from keywordset elements
        keywords = []

        # Handle both IEEE and IEEEFree keyword types
        for keywordset in self.article.find_all("keywordset"):
            keyword_type = keywordset.get("keywordtype", "")

            for keyword in keywordset.find_all("keywordterm"):
                if keyword.string:
                    keywords.append(
                        {
                            "system": keyword_type,
                            "string": self._clean_output(keyword.string.strip()),
                        }
                    )
        if keywords:
            self.base_metadata["keywords"] = keywords

    def _parse_references(self):
        # TODO: check if IEEE gives us references at all
        references = []
        if self.article.find("references"):
            for ref in self.article.find_all("reference"):
                # output raw XML for reference service to parse later
                ref_xml = str(ref.extract()).replace("\n", " ").replace("\xa0", " ")
                references.append(ref_xml)

            self.base_metadata["references"] = references

    def _parse_funding(self):
        funding = []

        # Look for funding info in article metadata

        articleinfo = self.article.find("articleinfo")
        # import pdb; pdb.set_trace()
        if articleinfo.find("fundrefgrp"):
            funding_sections = articleinfo.find("fundrefgrp").find_all("fundref", [])

            for funding_section in funding_sections:
                funder = {}

                # Get funder name
                funder_name = funding_section.find("funder_name")
                if funder_name:
                    funder.setdefault("agencyname", self._clean_output(funder_name.get_text()))

                # Get award/grant numbers
                award_nums = funding_section.find_all("grant_number")
                if award_nums:
                    # Join multiple award numbers with comma if present
                    awards = [self._clean_output(award.get_text()) for award in award_nums]
                    funder.setdefault("awardnumber", ", ".join(awards))

                if funder:
                    funding.append(funder)

        if funding:
            self.base_metadata["funding"] = funding

    def parse(self, text):
        """
        Parse IEEE XML into standard JSON format
        :param text: string, contents of XML file
        :return: parsed file contents in JSON format
        """
        try:
            d = self.bsstrtodict(text, parser="lxml-xml")
        except Exception as err:
            raise XmlLoadException(err)

        if d.find("publication", None):
            self.publication = d.find("publication")

            if self.publication.find("publicationinfo", None):
                self.publicationinfo = self.publication.find("publicationinfo")

            if self.publication.find("volume", None):
                self.volumeinfo = self.publication.find("volume").find("volumeinfo", None)
                self.article = self.publication.find("volume").find("article", None)

        self._parse_ids()
        self._parse_pub()
        self._parse_page()
        self._parse_pubdate()
        self._parse_title_abstract()
        self._parse_permissions()
        self._parse_authors()
        self._parse_keywords()
        self._parse_references()
        self._parse_funding()

        output = self.format(self.base_metadata, format="IEEE")

        return output
