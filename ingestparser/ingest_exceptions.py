# TODO add exception handling


class IngestParserException(Exception):
    pass


class AuthorParserException(IngestParserException):
    pass


class MissingAuthorsException(IngestParserException):
    pass


class MissingDoiException(IngestParserException):
    pass


class MissingTitleException(IngestParserException):
    pass


class NoSchemaException(IngestParserException):
    pass


class NotCrossrefXMLException(IngestParserException):
    pass


class TooManyDocumentsException(IngestParserException):
    pass


class WrongSchemaException(IngestParserException):
    pass


class XmlLoadException(IngestParserException):
    pass


class WrongFormatException(IngestParserException):
    pass
