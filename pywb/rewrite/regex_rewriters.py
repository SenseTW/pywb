import re
import sys
import itertools

from url_rewriter import UrlRewriter

#=================================================================
class RegexRewriter(object):
    @staticmethod
    def comment_out(string):
        return '/*' + string + '*/'

    @staticmethod
    def remove_https(string):
        return string.replace("https", "http")

    @staticmethod
    def add_prefix(prefix):
        return lambda string: prefix + string

    @staticmethod
    def archival_rewrite(rewriter):
        return lambda x: rewriter.rewrite(x)

    @staticmethod
    def replacer(string):
        return lambda x: string

    HTTPX_MATCH_STR = r'https?:\\?/\\?/[A-Za-z0-9:_@.-]+'



    DEFAULT_OP = add_prefix


    def __init__(self, rules):
        #rules = self.create_rules(http_prefix)

        # Build regexstr, concatenating regex list
        regex_str = '|'.join(['(' + rx + ')' for rx, op, count in rules])

        # ensure it's not middle of a word, wrap in non-capture group
        regex_str = '(?<!\w)(?:' + regex_str + ')'

        self.regex = re.compile(regex_str, re.M)
        self.rules = rules

    def filter(self, m):
        return True

    def rewrite(self, string):
        return self.regex.sub(lambda x: self.replace(x), string)

    def close(self):
        return ''

    def replace(self, m):
        i = 0
        for _, op, count in self.rules:
            i += 1

            full_m = i
            while count > 0:
                i += 1
                count -= 1

            if not m.group(i):
                continue

            # Optional filter to skip matches
            if not self.filter(m):
                return m.group(0)

            # Custom func
            if not hasattr(op, '__call__'):
                op = RegexRewriter.DEFAULT_OP(op)

            result = op(m.group(i))

            # if extracting partial match
            if i != full_m:
                result = m.string[m.start(full_m):m.start(i)] + result + m.string[m.end(i):m.end(full_m)]

            return result



#=================================================================
class JSLinkRewriter(RegexRewriter):
    """
    JS Rewriter which rewrites absolute http://, https:// and // urls
    at the beginning of a string
    """
    JS_HTTPX = r'(?<="|\')(?:https?:)?\\{0,2}/\\{0,2}/[A-Za-z0-9:_@.-]+'

    def __init__(self, rewriter, rules = []):
        rules = rules + [(self.JS_HTTPX, rewriter.get_abs_url(), 0)]
        super(JSLinkRewriter, self).__init__(rules)

#=================================================================
class JSLocationAndLinkRewriter(JSLinkRewriter):
    """
    JS Rewriter which also rewrites location and domain to the
    specified prefix (default: 'WB_wombat_')
    """

    def __init__(self, rewriter, rules = [], prefix = 'WB_wombat_'):
        rules = rules + [
             (r'(?<!/)\blocation\b', prefix, 0),
             (r'(?<=document\.)domain', prefix, 0),
        ]
        super(JSLocationAndLinkRewriter, self).__init__(rewriter, rules)

#=================================================================
# Set 'default' JSRewriter
JSRewriter = JSLocationAndLinkRewriter


#=================================================================
class XMLRewriter(RegexRewriter):
    def __init__(self, rewriter, extra = []):
        rules = self._create_rules(rewriter.get_abs_url())

        RegexRewriter.__init__(self, rules)

    # custom filter to reject 'xmlns' attr
    def filter(self, m):
        attr = m.group(1)
        if attr and attr.startswith('xmlns'):
            return False

        return True

    def _create_rules(self, http_prefix):
        return [
             ('([A-Za-z:]+[\s=]+)?["\'\s]*(' + RegexRewriter.HTTPX_MATCH_STR + ')', http_prefix, 2),
        ]

#=================================================================
class CSSRewriter(RegexRewriter):
    CSS_URL_REGEX = "url\\s*\\(\\s*[\\\\\"']*([^)'\"]+)[\\\\\"']*\\s*\\)"
    CSS_IMPORT_NO_URL_REGEX = "@import\\s+(?!url)\\(?\\s*['\"]?(?!url[\\s\\(])([\w.:/\\\\-]+)"

    def __init__(self, rewriter):
        rules = self._create_rules(rewriter)

        RegexRewriter.__init__(self, rules)


    def _create_rules(self, rewriter):
        return [
             (CSSRewriter.CSS_URL_REGEX, RegexRewriter.archival_rewrite(rewriter), 1),
             (CSSRewriter.CSS_IMPORT_NO_URL_REGEX, RegexRewriter.archival_rewrite(rewriter), 1),
        ]

