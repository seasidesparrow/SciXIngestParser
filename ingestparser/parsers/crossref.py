import logging
import re

from adsingestp.ingest_exceptions import (
    NotCrossrefXMLException,
    TooManyDocumentsException,
    WrongSchemaException,
    XmlLoadException,
)
from adsingestp.parsers.base import BaseBeautifulSoupParser

logger = logging.getLogger(__name__)

# compile outside of the class definition -- it only needs to be compiled once
re_issn = re.compile(r"^\d{4}-?\d{3}[0-9X]$")  # XXXX-XXXX


class CrossrefParser(BaseBeautifulSoupParser):
    def __init__(self):
        super(BaseBeautifulSoupParser, self).__init__()
        self.base_metadata = {}
        self.input_metadata = None
        self.record_meta = None
        self.record_type = None

    def _get_date(self, date_raw):
        """
        Extract and standarize date from input BeautifulSoup date object
        :param date_raw: BeautifulSoup date object
        :return: formatted date string (yyyy-mm-dd)
        """
        if date_raw.find("year"):
            pubdate = date_raw.find("year").get_text()
        else:
            raise WrongSchemaException("No publication year found")

        if date_raw.find("month"):
            month = date_raw.find("month").get_text()
        else:
            month = "00"

        if len(month) == 1:
            month = "0" + month
        pubdate = pubdate + "-" + month

        if date_raw.find("day"):
            day = date_raw.find("day").get_text()
        else:
            day = "00"

        if len(day) == 1:
            day = "0" + day
        pubdate = pubdate + "-" + day

        return pubdate

    def _get_isbn(self, isbns):
        """
        Takes a list of the ISBN nodes, returns the ISBN text of the correct node

        :param isbns: list of BS nodes
        :return: list of dicts of ISBNs
        """
        isbns_out = []
        for i in isbns:
            isbn_type = i.get("media_type", "print")

            isbns_out.append({"type": isbn_type, "isbn_str": i.get_text()})

        return isbns_out

    def _get_funding(self, fundgroups):
        funding_arr = []
        for fg in fundgroups:
            funder = {}
            funder_name = fg.find("assertion", {"name": "funder_name"})
            funder_award = fg.find("assertion", {"name": "award_number"})
            if funder_name:
                funder_id = funder_name.find("assertion", {"name": "funder_identifier"})
                if funder_id:
                    funder_id = funder_id.extract()
                funder_name = funder_name.extract()
            else:
                funder_id = None

            if funder_name:
                funder.setdefault("agencyname", funder_name.get_text().strip())
            if funder_id:
                funder.setdefault("agencyid", {"idvalue": funder_id.get_text().strip()})
            if funder_award:
                funder.setdefault("awardnumber", funder_award.extract().get_text().strip())

            if funder:
                funding_arr.append(funder)

        return funding_arr

    def _parse_funding(self):
        fundgroups = self.record_meta.find_all("assertion", {"name": "fundgroup"})
        if fundgroups:
            funding = self._get_funding(fundgroups)
            self.base_metadata["funding"] = funding

    def _parse_pub(self):
        # journal articles only
        if self.input_metadata.find("journal") and self.input_metadata.find("journal").find(
            "journal_metadata"
        ):
            journal_meta = self.input_metadata.find("journal").find("journal_metadata")
            if journal_meta.find("full_title"):
                self.base_metadata["publication"] = journal_meta.find("full_title").get_text()

            else:
                self.base_metadata["publication"] = None
            if journal_meta.find_all("issn"):
                issn_all = journal_meta.find_all("issn")
            else:
                issn_all = []
        else:
            self.base_metadata["publication"] = None
            issn_all = []

        issns = []
        for i in issn_all:
            if i.get_text() and re_issn.match(i.get_text()):
                if i.get("media_type"):
                    issns.append((i["media_type"], i.get_text()))
                else:
                    issns.append(("print", i.get_text()))
        self.base_metadata["issn"] = issns

    def _parse_issue(self):
        if self.record_type == "journal":
            meta = self.input_metadata.find("journal").find("journal_issue")

            if meta.find("journal_volume") and meta.find("journal_volume").find("volume"):
                self.base_metadata["volume"] = (
                    meta.find("journal_volume").find("volume").get_text()
                )

        else:
            # no handling here for conferences yet
            meta = None

        if meta and meta.find("issue"):
            self.base_metadata["issue"] = meta.find("issue").get_text()

    def _parse_conf_event_proceedings(self):
        # conferences only, parses event-level and proceedings-level metadata, not conference paper-level metadata
        event_meta = self.input_metadata.find("conference").find("event_metadata")
        proc_meta = self.input_metadata.find("conference").find("proceedings_metadata")
        if not proc_meta:
            proc_meta = self.input_metadata.find("conference").find("proceedings_series_metadata")

        if event_meta.find("conference_name"):
            self.base_metadata["conf_name"] = event_meta.find("conference_name").get_text()

        if event_meta.find("conference_location"):
            self.base_metadata["conf_location"] = event_meta.find("conference_location").get_text()

        if event_meta.find("conference_date"):
            self.base_metadata["conf_date"] = event_meta.find("conference_date").get_text()

        if proc_meta.find("proceedings_title"):
            self.base_metadata["publication"] = proc_meta.find("proceedings_title").get_text()

        if proc_meta.find("publisher_name"):
            self.base_metadata["publisher"] = proc_meta.find("publisher_name").get_text()

        # this will be overwritten by _parse_pubdate, if a pubdate is available for the conference paper itself, but
        # parsing the overall proceedings pubdate here at least provides a backstop
        if proc_meta.find("publication_date"):
            pubdate = self._get_date(proc_meta.find("publication_date"))
            # type of pubdate is not defined here, but default to print
            self.base_metadata["pubdate_print"] = pubdate

        if proc_meta.find("isbn"):
            self.base_metadata["isbn"] = self._get_isbn(proc_meta.find_all("isbn"))

    def _parse_book_series(self):
        series_meta = self.record_meta.find("series_metadata")
        if series_meta.find("title"):
            self.base_metadata["series_title"] = series_meta.find("title").get_text()
        elif series_meta.find("titles"):
            self.base_metadata["series_title"] = series_meta.find("title").get_text()

        # TODO need to add logic for other ID types
        if series_meta.find("issn"):
            self.base_metadata["series_id"] = series_meta.find("issn").get_text()
            self.base_metadata["series_id_description"] = "issn"
        elif series_meta.find("isbn"):
            isbn_list = series_meta.find_all("isbn")
            self.base_metadata["series_id"] = ", ".join(isbn_list)
            self.base_metadata["series_id_description"] = "issn"

    def _parse_posted_content(self):
        if self.record_meta.find("institution"):
            inst_name = None
            if self.record_meta.find("institution").find("institution_name"):
                inst_name = (
                    self.record_meta.find("institution").find("institution_name").get_text()
                )
            if self.record_meta.find("institution").find("institution_acronym"):
                if inst_name:
                    inst_name = (
                        inst_name
                        + " (%s)"
                        % self.record_meta.find("institution")
                        .find("institution_acronym")
                        .get_text()
                    )
                else:
                    inst_name = (
                        self.record_meta.find("institution").find("institution_acronym").get_text()
                    )
            if inst_name:
                self.base_metadata["publisher"] = inst_name
        if self.record_meta.find("posted_date"):
            pubdate = self._get_date(self.record_meta.find("posted_date"))
            self.base_metadata["pubdate_electronic"] = pubdate

    def _parse_title_abstract(self):
        # Only parse title for non book series metadata
        if self.record_meta.find("titles") and self.record_meta.find("titles").find("title"):
            title = self.record_meta.find("titles", recursive=False).find("title").get_text()
            if not title:
                title = self.record_meta.find("titles").find("title").get_text()
            self.base_metadata["title"] = title

        if self.record_meta.find("titles") and self.record_meta.find("titles").find("subtitle"):
            self.base_metadata["subtitle"] = (
                self.record_meta.find("titles").find("subtitle").get_text()
            )

        if self.record_meta.find("jats:abstract") and self.record_meta.find("jats:abstract").find(
            "jats:p"
        ):
            self.base_metadata["abstract"] = self._clean_output(
                self.record_meta.find("jats:abstract").find("jats:p").get_text()
            )
        elif self.record_meta.find("abstract"):
            if self.record_meta.find("abstract").find("title"):
                self.record_meta.find("abstract").find("title").decompose()
            self.base_metadata["abstract"] = self._clean_output(
                self.record_meta.find("abstract").get_text()
            )

    def _parse_contrib(self):
        if self.record_meta.find("contributors"):
            contribs_section = self.record_meta.find("contributors").extract()
            contribs_raw = contribs_section.find_all("person_name")
        else:
            contribs_raw = []

        authors_out = []
        contribs_out = []
        for c in contribs_raw:
            contrib_tmp = {}
            if c.find("given_name"):
                contrib_tmp["given"] = c.find("given_name").get_text()

            if c.find("surname"):
                contrib_tmp["surname"] = c.find("surname").get_text()

            if c.find("suffix"):
                contrib_tmp["suffix"] = c.find("suffix").get_text()

            if c.find("ORCID"):
                orcid = c.find("ORCID").get_text()
                orcid = orcid.replace("http://orcid.org/", "").replace("https://orcid.org/", "")
                contrib_tmp["orcid"] = orcid

            if c.find("affiliation"):
                affil = [a.get_text() for a in c.find_all("affiliation")]
                if affil:
                    contrib_tmp["aff"] = affil
            elif c.find("affiliations"):
                affil = []
                institutions = c.find("affiliations").find_all("institution")
                if institutions:
                    for inst in institutions:
                        name = inst.find("institution_name")
                        dept = inst.find("institution_department")
                        acro = inst.find("institution_acronym")
                        place = inst.find("institution_place")
                        taglist = []
                        if dept:
                            taglist.append(dept.get_text())
                        if name:
                            taglist.append(name.get_text())
                        if acro:
                            taglist.append(acro.get_text())
                        if place:
                            taglist.append(place.get_text())
                        if taglist:
                            affstring = ", ".join(taglist)
                            affstring = re.sub(r"\s+,", ",", affstring)
                            affil.append(affstring)
                if affil:
                    contrib_tmp["aff"] = affil

            role = c.get("contributor_role", "unknown")

            if role == "author":
                authors_out.append(contrib_tmp)
            else:
                contrib_tmp["role"] = role
                contribs_out.append(contrib_tmp)

        if authors_out:
            self.base_metadata["authors"] = authors_out
        if contribs_out:
            self.base_metadata["contributors"] = contribs_out

    def _parse_pubdate(self):
        pubdates_raw = self.record_meta.find_all("publication_date")
        for p in pubdates_raw:
            if p.get("media_type"):
                datetype = p.get("media_type")
            else:
                logger.warning("Pubdate without a media type, assigning print.")
                datetype = "print"

            pubdate = self._get_date(p)
            if datetype == "print":
                self.base_metadata["pubdate_print"] = pubdate
            elif datetype == "online":
                self.base_metadata["pubdate_electronic"] = pubdate
            else:
                logger.warning("Unknown date type: %s" % datetype)

    def _parse_edhistory_copyright(self):
        if self.record_meta.find("crossmark") and self.record_meta.find("crossmark").find(
            "custom_metadata"
        ):
            custom_meta = (
                self.record_meta.find("crossmark").find("custom_metadata").find_all("assertion")
            )
            received = []
            for c in custom_meta:
                if c["name"] == "date_received":
                    received.append(c.get_text())
                elif c["name"] == "date_accepted":
                    self.base_metadata["edhist_acc"] = c.get_text()
                elif c["name"] == "copyright_information":
                    self.base_metadata["copyright"] = c.get_text()

                self.base_metadata["edhist_rec"] = received

    def _parse_page(self):
        if self.record_meta.find("pages"):
            page_info = self.record_meta.find("pages")

            if page_info.find("first_page"):
                self.base_metadata["page_first"] = page_info.find("first_page").get_text()

            if page_info.find("last_page"):
                self.base_metadata["page_last"] = page_info.find("last_page").get_text()

        elif self.record_meta.find("publisher_item") and self.record_meta.find(
            "publisher_item"
        ).find("item_number"):
            ids = {}
            for idx, i in enumerate(
                self.record_meta.find("publisher_item").find_all("item_number")
            ):
                if i.get("item_number_type"):
                    tag = i.get("item_number_type")
                else:
                    tag = None
                ids[tag if tag else "other" + str(idx)] = i.get_text()
            if ids.get("article-number"):
                self.base_metadata["electronic_id"] = ids["article-number"]
            # TODO if there are any other relevant publisher items, add handling here

    def _parse_ids(self):
        self.base_metadata["ids"] = {}

        # TODO ask Matt about crossref ID
        if self.record_meta.find("doi_data") and self.record_meta.find("doi_data").find("doi"):
            self.base_metadata["ids"]["doi"] = (
                self.record_meta.find("doi_data").find("doi").get_text()
            )

    def _parse_references(self):
        if self.record_meta.find("citation_list"):
            refs_raw = self.record_meta.find("citation_list").find_all("citation")

            ref_list = []
            # output raw XML for reference parser to handle
            for r in refs_raw:
                ref_list.append(str(r.extract()).replace("\n", " "))

            self.base_metadata["references"] = ref_list

    def _parse_esources(self):
        links = []
        if self.record_meta.find("doi_data"):
            if self.record_meta.find("doi_data").find("resource"):
                links.append(("pub_html", self.record_meta.find("resource").get_text()))

        self.base_metadata["esources"] = links

    def _dedup_titles(self):
        pubname = self.base_metadata.get("publication", None)
        title = self.base_metadata.get("title", None)
        seriestitle = self.base_metadata.get("series_title", None)
        proctitle = self.base_metadata.get("proceedings_title", None)
        titles = [title, seriestitle, proctitle]
        if pubname in titles:
            self.base_metadata["publication"] = None

    def parse(self, text):
        """
        Parse Crossref XML into standard JSON format
        :param text: string, contents of XML file
        :return: parsed file contents in JSON format
        """
        try:
            d = self.bsstrtodict(text, parser="lxml-xml")
        except Exception as err:
            raise XmlLoadException(err)

        records_in_file = d.find_all("doi_record")
        if len(records_in_file) > 1:
            raise TooManyDocumentsException(
                "This file has %s records, should have only one!" % len(records_in_file)
            )

        try:
            self.input_metadata = d.find("crossref").extract()
        except AttributeError as err:
            raise NotCrossrefXMLException(err)

        type_found = False
        self.record_type = None
        if self.input_metadata.find("journal"):
            type_found = True
            self.record_type = "journal"
            if self.input_metadata.find("journal_article"):
                self.record_meta = self.input_metadata.find("journal_article").extract()
                self.base_metadata["doctype"] = "article"
            else:
                self.record_meta = None
        if self.input_metadata.find("conference"):
            if type_found:
                raise WrongSchemaException("Too many document types found in CrossRef record")
            else:
                type_found = True
                self.record_type = "conference"
                if self.input_metadata.find("conference_paper"):
                    self.record_meta = self.input_metadata.find("conference_paper").extract()
                    self.base_metadata["doctype"] = "inproceedings"
                else:
                    self.record_meta = None
                    self.base_metadata["doctype"] = "proceedings"
        if self.input_metadata.find("book"):
            if type_found:
                raise WrongSchemaException("Too many document types found in CrossRef record")
            else:
                type_found = True
                self.record_type = "book"
                if self.input_metadata.find("book_metadata"):
                    self.record_meta = self.input_metadata.find("book_metadata").extract()
                elif self.input_metadata.find("book_series_metadata"):
                    self.record_meta = self.input_metadata.find("book_series_metadata").extract()
                else:
                    self.record_meta = None

                # Parse metadata related to the book
                if self.record_meta.find("publisher") and self.record_meta.find("publisher").find(
                    "publisher_name"
                ):
                    self.base_metadata["publisher"] = self.record_meta.find(
                        "publisher_name"
                    ).get_text()

                if self.record_meta.find("isbn"):
                    self.base_metadata["isbn"] = self._get_isbn(self.record_meta.find_all("isbn"))

                if self.record_meta.find("volume"):
                    self.base_metadata["volume"] = self.record_meta.find("volume").get_text()

                if self.record_meta.find("series_metadata"):
                    self._parse_book_series()

                if self.record_meta.find("contributors"):
                    self._parse_contrib()

                if self.record_meta.find("title"):
                    self.base_metadata["publication"] = self.record_meta.find("title").get_text()

                # Parse metadata related to the book chapter
                if (
                    self.input_metadata.find("content_item")
                    and self.input_metadata.find("content_item").get("component_type") == "chapter"
                ):
                    self.record_type = "book_chapter"
                    self.record_meta = self.input_metadata.find("content_item")
                    self.base_metadata["doctype"] = "inbook"
                else:
                    self.base_metadata["doctype"] = "book"
        if self.input_metadata.find("posted_content"):
            if type_found:
                raise WrongSchemaException("Too many document types found in CrossRef record")
            else:
                type_found = True
                self.record_type = "posted_content"
                if self.input_metadata.find("posted_content"):
                    if self.input_metadata.find("posted_content").get("type", None) == "preprint":
                        self.base_metadata["doctype"] = "eprint"
                    self.record_meta = self.input_metadata.find("posted_content").extract()
                else:
                    self.record_meta = None

        if not type_found:
            raise WrongSchemaException(
                "Didn't find allowed document type (article, conference, book, posted_content) in CrossRef record"
            )
        elif not self.record_meta:
            raise WrongSchemaException(
                "Null record_meta for document type %s in CrossRef record" % self.record_type
            )

        if self.record_type == "journal":
            self._parse_pub()

        if self.record_type == "conference":
            self._parse_conf_event_proceedings()

        if self.record_type == "posted_content":
            self._parse_posted_content()

        self._parse_funding()
        self._parse_issue()
        self._parse_title_abstract()
        self._parse_contrib()
        self._parse_pubdate()
        self._parse_edhistory_copyright()
        self._parse_page()
        self._parse_ids()
        self._parse_references()
        self._parse_esources()
        self._dedup_titles()

        self.base_metadata = self._entity_convert(self.base_metadata)

        output = self.format(self.base_metadata, format="OtherXML")

        return output
