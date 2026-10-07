import logging

from adsingestp import utils
from adsingestp.ingest_exceptions import (
    MissingDoiException,
    MissingTitleException,
    XmlLoadException,
)
from adsingestp.parsers.base import BaseBeautifulSoupParser

logger = logging.getLogger(__name__)


class DataciteParser(BaseBeautifulSoupParser):
    """Compatible with DataCite schema versions 2, 3 and 4"""

    # DC_SCHEMAS = ["http://datacite.org/schema/kernel-2", "http://datacite.org/schema/kernel-3", "http://datacite.org/schema/kernel-4"]

    author_collaborations_params = {
        "keywords": ["group", "team", "collaboration"],
        "remove_the": False,
    }

    datacite_resourcetype_mapping = {
        "Audiovisual": "misc",
        "Collection": "misc",
        "DataPaper": "misc",
        "Dataset": "dataset",
        "Event": "misc",
        "Image": "misc",
        "InteractiveResource": "misc",
        "Model": "misc",
        "PhysicalObject": "misc",
        "Service": "misc",
        "Software": "software",
        "Sound": "misc",
        "Text": "misc",
        "Workflow": "misc",
        "Other": "misc",
    }

    def __init__(self):
        super(BaseBeautifulSoupParser, self).__init__()
        self.base_metadata = {}
        self.input_metadata = None

    def _parse_contrib(self, author=True):
        contribs_out = []
        name_parser = utils.AuthorNames()
        if author:
            if self.input_metadata.find("creators"):
                contrib_array = self.input_metadata.find("creators").find_all("creator")
            else:
                contrib_array = []
        else:
            if self.input_metadata.find("contributors"):
                contrib_array = self.input_metadata.find("contributors").find_all("contributor")
            else:
                contrib_array = []
        for c in contrib_array:
            contrib_tmp = []
            if c.find("givenName") and c.find("familyName"):
                sub_contrib = {}
                sub_contrib["given"] = c.find("givenName").get_text()
                sub_contrib["surname"] = c.find("familyName").get_text()
                contrib_tmp.append(sub_contrib)
            else:
                if author:
                    if c.find("creatorName"):
                        contrib_name = c.find("creatorName").get_text()
                    else:
                        contrib_name = ""
                else:
                    if c.find("contributorName"):
                        contrib_name = c.find("contributorName").get_text()
                    else:
                        contrib_name = ""

                parsed_name_list = name_parser.parse(
                    contrib_name, collaborations_params=self.author_collaborations_params
                )

                contrib_tmp = parsed_name_list

            if c.find_all("affiliation"):
                aff = []
                for a in c.find_all("affiliation"):
                    aff.append(a.get_text())
                for ct in contrib_tmp:
                    ct["aff"] = aff

            for i in c.find_all("nameIdentifier"):
                if (
                    i.get("nameIdentifierScheme", "") == "ORCID"
                    or i.get("schemeURI", "") == "http://orcid.org"
                ):
                    for ct in contrib_tmp:
                        orcid = i.get_text().replace("https://orcid.org/", "")
                        if orcid:
                            ct["orcid"] = orcid

            if not author:
                for ct in contrib_tmp:
                    ct["role"] = c.get("contributorType", "")

            contribs_out += contrib_tmp

        if author:
            self.base_metadata["authors"] = contribs_out
        else:
            self.base_metadata["contributors"] = contribs_out

    def _parse_title_abstract(self):
        titles = {}
        if self.input_metadata.find("titles"):
            titles_raw = self.input_metadata.find("titles").find_all("title")
        else:
            titles_raw = []
        for t in titles_raw:
            title_attr = t.get("xml:lang", "")
            # titleType is only present for subtitles and alternate titles, not the primary title
            type_attr = t.get("titleType", "")
            if not type_attr:
                titles[title_attr.lower()] = self._clean_output(t.get_text())
            if type_attr == "Subtitle":
                self.base_metadata["subtitle"] = self._detag(
                    self._clean_output(t.get_text()), self.HTML_TAGSET["title"]
                )
        if not titles:
            raise MissingTitleException("No title found")
        # we use the English title as the main one, then add any foreign ones
        # there are several options for "English" in this schema, so check for all of them (lowercase forms).  If no language specified (key is ""), assume English.
        en_key = list({"en", "en-us", ""} & set(titles.keys()))[0]
        self.base_metadata["title"] = self._detag(
            self._clean_output(titles.pop(en_key)), self.HTML_TAGSET["title"]
        )
        title_foreign = []
        lang_foreign = []
        for tkey in titles:
            title_foreign.append(titles[tkey])
            lang_foreign.append(tkey)

        # the data model only takes a single foreign-language title; will need to adjust if more are required
        if title_foreign:
            self.base_metadata["title_native"] = self._detag(
                self._clean_output(title_foreign[0]), self.HTML_TAGSET["title"]
            )
            self.base_metadata["lang_native"] = lang_foreign[0]

        # abstract, references are all in the "descriptions" section
        # as of version 3.1 of datacite schema, "References" is not an
        # allowed description type so Lars is shoving the references
        # in a section labeled as "Other" as a json structure
        abstract = None
        if self.input_metadata.find("descriptions"):
            for s in self.input_metadata.find("descriptions").find_all("description"):
                t = s.get("descriptionType", "")
                if t == "Abstract":
                    abstract = s.get_text()

        if abstract:
            self.base_metadata["abstract"] = self._detag(
                self._clean_output(abstract), self.HTML_TAGSET["abstract"]
            )

    def _parse_publisher(self):
        if self.input_metadata.find("publisher"):
            self.base_metadata["publisher"] = self.input_metadata.find("publisher").get_text()

    def _parse_pubdate(self):
        if self.input_metadata.find("publicationYear"):
            self.base_metadata["pubdate_electronic"] = self.input_metadata.find(
                "publicationYear"
            ).get_text()

        if self.input_metadata.find("dates"):
            dates = []
            for d in self.input_metadata.find("dates").find_all("date"):
                t = d.get("dateType", "")
                dates.append({"type": t, "date": d.get_text()})

            if dates:
                self.base_metadata["pubdate_other"] = dates

    def _parse_keywords(self):
        if self.input_metadata.find("subjects"):
            keywords = []
            for k in self.input_metadata.find("subjects").find_all("subject"):
                # check if keyword is from UAT
                if "unified astronomy thesaurus" in str(
                    k.get("subjectScheme", "")
                ).lower() or "uat" in k.get("schemeURI", ""):
                    # extract the numeric keyID from the URI
                    keyid = [int(x) for x in k.get("valueURI", "").split("/") if x.isdigit()]

                    if keyid:
                        keywords.append(
                            {"string": k.get_text(), "system": "UAT", "id": str(keyid[0])}
                        )
                    else:
                        keywords.append({"string": k.get_text(), "system": "UAT"})

                else:
                    keywords.append({"string": k.get_text(), "system": "datacite"})
            self.base_metadata["keywords"] = keywords

    def _parse_ids(self):
        self.base_metadata["ids"] = {}

        if self.input_metadata.find("identifier"):
            if self.input_metadata.find("identifier").get("identifierType", "") == "DOI":
                self.base_metadata["ids"]["doi"] = self.input_metadata.find(
                    "identifier"
                ).get_text()
            else:
                raise MissingDoiException("//identifier['@identifierType'] not DOI!")

        # bibcodes should appear as <alternateIdentifiers>
        if self.input_metadata.find("alternateIdentifiers"):
            pub_ids = []
            for i in self.input_metadata.find("alternateIdentifiers").find_all(
                "alternateIdentifier"
            ):
                t = i.get("alternateIdentifierType", "")
                pub_ids.append({"attribute": t, "Identifier": i.get_text()})
            self.base_metadata["ids"]["pub-id"] = pub_ids

    def _parse_related_refs(self):
        # related identifiers; bibcodes sometime appear in <relatedIdentifiers>
        if self.input_metadata.find("relatedIdentifiers"):
            related_to = []
            references = []
            for i in self.input_metadata.find("relatedIdentifiers").find_all("relatedIdentifier"):
                rt = i.get("relationType", "")
                c = i.get_text()
                if rt == "Cites":
                    references.append(c)
                elif rt in utils.related_trans_dict.keys():
                    related_to.append({"relationship": utils.related_trans_dict[rt], "id": c})
                else:
                    logger.info("RelatedTo type %s not included in translation dictionary", rt)
                    related_to.append({"relationship": "related", "id": c})

            self.base_metadata["relatedto"] = related_to
            self.base_metadata["references"] = references

    def _parse_permissions(self):
        self.base_metadata["openAccess"] = {}

        if self.input_metadata.find("rightsList"):
            is_oa = False
            for i in self.input_metadata.find("rightsList").find_all("rights"):
                u = i.get("rightsURI", "")
                c = i.get_text()
                if u == "info:eu-repo/semantics/openAccess" or c == "Open Access":
                    is_oa = True
                elif "http" in u:
                    self.base_metadata.setdefault("openAccess", {}).setdefault("licenseURL", u)
                    if "creativecommon" in u:
                        is_oa = True
                    if c:
                        self.base_metadata.setdefault("openAccess", {}).setdefault("license", c)
                        if "Creative Common" in c or "GNU General Public License" in c:
                            is_oa = True

            self.base_metadata.setdefault("openAccess", {}).setdefault("open", is_oa)

    def _parse_doctype(self):
        if self.input_metadata.find("resourceType"):
            resource_type = self.input_metadata.find("resourceType").get("resourceTypeGeneral", "")
            doctype = self.datacite_resourcetype_mapping.get(resource_type, "misc")
            self.base_metadata["doctype"] = doctype

    def parse(self, text):
        """
        Parse Datacite XML into standard JSON format
        :param text: string, contents of XML file
        :return: parsed file contents in JSON format
        """
        try:
            d = self.bsstrtodict(text, parser="lxml-xml")
        except Exception as err:
            raise XmlLoadException(err)

        # as a convenience, remove the OAI wrapper if it's there
        if (
            d.find("record")
            and d.find("record").find("metadata")
            and d.find("record").find("metadata").find("resource")
        ):
            self.input_metadata = d.find("record").find("metadata").find("resource")
        else:
            self.input_metadata = d.find("resource")

        # check for namespace to make sure it's a compatible datacite schema
        # schema = self.input_metadata.get("xmlns", "")
        # if schema not in self.DC_SCHEMAS:
        #    raise WrongSchemaException('Unexpected XML schema "%s"' % schema)

        self._parse_contrib(author=True)
        self._parse_contrib(author=False)
        self._parse_title_abstract()
        self._parse_publisher()
        self._parse_pubdate()
        self._parse_keywords()
        self._parse_ids()
        self._parse_related_refs()
        self._parse_permissions()
        self._parse_doctype()

        self.base_metadata = self._entity_convert(self.base_metadata)

        output = self.format(self.base_metadata, format="OtherXML")

        return output
