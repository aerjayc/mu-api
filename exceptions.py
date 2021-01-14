class ParseError(Exception):
    """HTML parsing failure (unexpected data)"""
    pass

class RegexParseError(ParseError):
    """Regular Expression returned no match"""

    def __init__(self, pattern=None, string=None):
        if pattern is not None and string is not None:
            message = (f'Regular Expression {repr(pattern)} yielded no results'
                       f'on string {repr(string)}.')
        else:
            message = 'Regular Expression yielded no results'
        super().__init__(message)
