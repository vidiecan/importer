# -*- coding: utf-8 -*-
# See main file for license.

import re
import utils
import urllib
import urllib2
from settings import settings

_logger = utils.logger('converters')


class mathml(object):
    """
        MathML object.
    """
    url_form_latex = settings["converters"]["latexml"]["url"]
    encoding = settings["converters"]["encoding"]
    id_str = u' egomath="%s" '
    pattern_id_add = re.compile( u'(<math)\s(.*?xmlns="http://www.w3.org/1998/Math/MathML")' )
    pattern_id_get = re.compile( id_str % u'(.*?)'  )

    def __init__( self, mathml_str ):
        self.str = mathml_str

    @staticmethod
    def from_latex( latex_math_orig ):
        """
            Returns either mathml object or None.
        """
        # try fetching the answer
        js = None
        latex_math = latex_math_orig
        try:
            latex_math = latex(latex_math, full=False).str

            # is empty?
            if len(latex_math.strip()) == 0:
                _logger.warning(u"Warning: empty math - [%s]", repr(latex_math))
                return None, None

            latex_math = u"$ %s $" % latex_math
            # old service req = urllib2.Request(
            # URL, urllib.urlencode({ 'formula' : utils.ascii(latex,DEF_ENCODING) }) )
            # new service
            req = urllib2.Request(mathml.url_form_latex, urllib.urlencode({
                'tex': latex_math.encode( "utf-8" ),
                'profile': 'math',
            }))
            response = urllib2.urlopen(req, timeout=settings["converters"]["latexml"]["timeout"])

            # try parsing the answer
            import json

            js = json.load(response)
            result = js[settings["converters"]["latexml"]["result_field"]]
            message = js[settings["converters"]["latexml"]["status_field"]]
            if result:
                result = result.encode(mathml.encoding)
            if message:
                message = message.encode(mathml.encoding)

        except Exception, e:
            if js is None:
                # fake js
                js = {
                    "result": None,
                    "status": "Problem at early stage.",
                    "status_code": -1,
                    "log": repr(e),
                }
            _logger.error(u"Error: Connection problem - %s with [%s]", repr(e), latex_math)
            return None, js

        everything_ok = False
        for msg in settings["converters"]["latexml"]["status_ok"]:
            if msg in message:
                everything_ok = not message is None and 0 < len(message)
                break
        not_empty_result = result and result != ''
        # everything ok - return answer
        if everything_ok and not_empty_result:
            return mathml(result).str, js

        # something fishy - try to correct it
        ascii_latex = utils.ascii(latex_math, mathml.encoding)
        if everything_ok and not_empty_result and len(ascii_latex) < 6:
            # in case the service returns empty string and it seems to be just a variable
            _logger.warning(u"Warning: returning original - %s", repr(ascii_latex))
            return mathml(ascii_latex).str, js

        # seems not ok but the latest converter returns valid results
        if not everything_ok and not_empty_result:
            _logger.warning(u"Warning: returning conversion but with errors - %s", repr(ascii_latex))
            return mathml(result).str, js

        _logger.error(u"\n!ERROR - converting [%s] -> result [%s] with message [%s]\n%s",
                     ascii_latex, utils.uni(result), utils.uni(message), 40 * "=")
        return None, js

    @staticmethod
    def add_id( mathml_str, id_to_include ):
        mathml_str = mathml.pattern_id_add.sub(
            u"\\1 " + mathml.id_str % id_to_include + u" \\2", mathml_str)
        return mathml_str

    @staticmethod
    def get_id( mathml_str ):
        m = mathml.pattern_id_get.search( mathml_str )
        return m.group() if m else None

    @staticmethod
    def fix_annotation( mathml_str_annotation ):
        """ There are %\n symbols in TeX repre... """
        mathml_str_annotation = mathml_str_annotation.replace( u"%\n", " " )
        return mathml_str_annotation.strip()


class latex(object):
    """
    LaTeX object.
  """
    encoding = settings["converters"]["encoding"]

    tex_normaliser = (
        re.compile( r'( )+' ),

        re.compile( r'({)\s*' ),
        re.compile( r'\s*(})' ),

        re.compile( r'\s*(_)\s*' ),
        re.compile( r'\s*(^)\s*' ),

        re.compile( ur'~*(~)~*' ),
        re.compile( ur'([^\\])~\{\}' ),
        re.compile( ur'([^\\])~' ),
    )
    tex_normaliser_replace = (
        (re.compile( ur'{\(\s*([^()]+?)\s*\)}' ), ur"{\1}" ),
    )

    flags = re.DOTALL | re.UNICODE | re.MULTILINE
    tex_texifiers = (
        ( re.compile( ur'\\Z(\s|$)', flags ), ur"Z " ),
        ( re.compile( ur'\\(or|lor|bigvee|curlyvee)(\s|$)', flags ), ur"\\vee " ),
        ( re.compile( ur'\\(and|land|bigwedge)(\s|$)', flags ), ur"\\wedge " ),
        ( re.compile( ur'\{.matrix\}', flags ), ur"{matrix}" ),
        ( re.compile( ur'\\part(\s|$)', flags ), ur"∂\1" ),
        ( re.compile( ur'\\partial(\s|$)', flags ), ur"∂\1" ),
    )

    def __init__( self, str_, full=True ):
        self.str = latex.texify(str_, full)
        self.str = latex.normalise( self.str )

    @staticmethod
    def texify( latex_str, full=True ):
        #latex_str = utils.ascii(latex_str, latex.encoding)
        if len(latex_str) > 1:
            latex_str = latex_str.strip('$')
        for (k, v) in [
            # spaces
            (r"\ ", r" "),
            (r"\;", r" "),
            (r"\,", r" "),
            (r"\:", r" "),
            (r"\!", r" "),

            #
            (r"\lt;", "\lt "),
            (r"\gt;", "\gt "),
            (r"\lt", " < "),
            (r"\gt", " > "),
            (r"\exist ", r"\exists "),
            (r"\rarr", r"\rightarrow"),
            (r"\arccot ", r"arccot "),
            (r"\arccsc ", r"arccsc "),
            (r"\arcsec ", r"arcsec "),
            (r"\xrightarrow", r"\rightarrow"),

            (r"\ro", r"\rho"),

            (r"\vert", r"|"),
            (r"\Vert", r"|"),
        ]:
            latex_str = latex_str.replace(k, v)

        for p, replace_with in latex.tex_texifiers:
            latex_str = p.sub( replace_with, latex_str )

        latex_str = latex_str.strip()

        for toreplace in (
                r"\Alpha", r"\Beta", r"\Tau", r"\Zeta", r"\Epsilon", r"\Iota"):
            latex_str = latex_str.replace( toreplace, toreplace.lower() )

        if full:
            for toremove in (
                    r"\boldsymbol", r"\bold",
                    r"\emptyset", r"\empty",
                    r"\mathbf", r"\mathbb", r"\textrm", r"\mathcal", r"\mathfrak", r"\mathit",
                    r"\mathsf", r"\mathrm", r"\mathtt", r"\cal", r"\operatorname",
                    r"\begin{cases}", r"\end{cases}", r"\textstyle", r"\displaystyle",
                    r"\,.", r"\left", r"\right"
            ):
                latex_str = latex_str.replace( toremove, u" " )

        if latex_str == "\\R":
            latex_str = "\\Re"
        if latex_str in ["\\Z", "\\C", "\\N", "\\Q"]:
            latex_str = latex_str.lstrip("\\")

        return latex_str.strip()

    @staticmethod
    def remove_basic_text_formatting( tex ):
        """
            Remove mbox etc.
        """
        for pattern in (
            "mbox", "text", "textbf", "textrm",
        ):
            m = re.compile(u"^\s*\\\\%s{(.*?)}\s*$" % pattern).match(tex)
            if m:
                tex = m.group(1)
                break
            # remove empty
            tex = re.compile(u"\\\\%s{\s*}" % pattern).sub( u"", tex)
        return tex

    @staticmethod
    def normalise( tex ):
        """
            Return a normalised tex string e.g., without double whitespace.
        """
        for pattern in latex.tex_normaliser:
            tex = pattern.sub( ur'\1', tex )
        for pattern, sub in latex.tex_normaliser_replace:
            tex = pattern.sub( sub, tex )
        return tex


if __name__ == "__main__":
    #s = u"\mbox{ }_{U_{I_0}}"
    s = ur"^{( 1 / 2\;\:\,\: )}."
    print "Input  ", s, "\nResult:", latex(s).str
    print mathml.from_latex( latex(s).str )
