# -*- coding: utf-8 -*-
# See main file for license.
#
#   Parses wiki dump and returns  page iterator.
#

import os
import sys
import re
import string
import time

import utils

utils.add_to_path(sys, os.path.join(os.path.dirname(__file__), '..'))
from settings import settings as _settings_global
from datasets.wiki._settings import settings as _settings_local
from HTMLParser import HTMLParser
from converters import mathml

logger = utils.logger('datasets.wiki.parser')
logger_suspicious = utils.logger("datasets.suspicious")


#=======================
# unescaper
#=======================

html_parser = HTMLParser()


def unescape_recursive(text_str):
    """
    Use HTMLParser.escape
    """
    math_text_tmp_old = text_str
    math_tex_tmp_new = html_parser.unescape(math_text_tmp_old)
    while math_text_tmp_old != math_tex_tmp_new:
        math_text_tmp_old = math_tex_tmp_new
        math_tex_tmp_new = html_parser.unescape(math_text_tmp_old)
    return math_tex_tmp_new


#=======================
# parser
#=======================

class parser(HTMLParser):
    """
    Wiki parser
    """
    flags = re.DOTALL | re.UNICODE | re.MULTILINE

    MATH_SEP_END = _settings_local["pager"]["math_sep"][1]

    wiki_comment_remove_pattern = re.compile(r'&lt;!--.*?--&gt;()', flags)

    wiki_nowiki_remove_pattern = re.compile(ur'&lt;nowiki&gt;.*?&lt;/nowiki&gt;', flags)

    wiki_tag_remove_patterns = [
        # noinclude
        re.compile(r"&lt;noinclude&gt;.*?&lt;/noinclude&gt;()", flags),
        # <!-- -->
        re.compile(r'&lt;!--.*?--&gt;()', flags),
        # ref
        #re.compile(r'&amp;\s*?lt;\s*?ref.*?lt;/ref\s*?&amp;\s*?gt;()', flags),
        re.compile(u'&lt;\s*?ref[^/]*?&gt;(.+?)&lt;\s*/ref\s*&gt;', flags),
        re.compile(u'&lt;\s*?ref.*?(?:/&gt;|/ref\s*?&gt;)()', flags),
        # font
        re.compile(r"\'{3,5}()", flags),
    ]

    wiki_tag_remove_patterns_full = [
        # {{ }}
        re.compile(r'{{[^{]*?}}()', flags),
        re.compile(r'{\|.*?\|}()', flags),
        # <table .. /table>
        re.compile(r'&lt;table.*?&lt;/table&gt;()', flags),
        # [[ ]]
        re.compile(r'\[\[[^\]]+?\|([^\|]*?)\]\]', flags),
        re.compile(r'\[\[(.*?)\]\]', flags),
        re.compile(r'\]\]()', flags),
        re.compile(r'\[\[()', flags),
    ]

    # internals for read state machine
    NOT_READ = 0
    READ = 1

    def __init__(self):
        HTMLParser.__init__(self)
        self.data = {}
        self.text = u""
        self.fsm = (parser.NOT_READ, u"")
        self.math_parser = math()
        # store id of the main formula - 2013/04 newest gotcha from latexml
        self.math_xref = None

    @utils.time_method
    def feed(self, page_str):
        # assert self.no_wiki_markup( page_str )
        s = time.time()
        res = HTMLParser.feed(self, page_str)
        logger_suspicious.debug(u"  feed lasted [%s]", time.time() - s)
        s = time.time()
        math_field = self.math_parser.parse(self.text, page_str)
        self.data[u"math"] = math_field
        #self.data[u"math"] = u"".join(math_field)
        self.data[u"math_count"] = len(math_field)

        logger_suspicious.debug(u"  math_parser.parse lasted [%s]", time.time() - s)
        return res

    def handle_starttag(self, tag, attrs):
        """
     We are interested in title, meta (id,url,category)

      analyse_pattern = re.compile(
                          r'<title>(?P<title>.+)</title>.*' +
                          r'<meta name="id" content=\"(?P<id>.*?)\" \/\>.*' +
                          r'<meta name="url" content=\"(?P<url>.*?)\" \/\>.*' +
                          r'<meta name="category" content=\"(?P<category>.*?)\" \/\>.*'
                            , re.DOTALL )
    """
        if tag == u'title':
            self.fsm = ( self.READ, u"title" )

        elif tag == u"meta" and attrs:
            interested_attr = None
            interested_value = None
            for (k, v) in attrs:
                if k == u"name":
                    for interested in [u"id",
                                       u"url",
                                       u"category",
                                       u"citations",
                                       u"citations_count",
                                       u"refs",
                                       u"refs_count",
                                       u"lang_avail",
                    ]:
                        if v == interested:
                            interested_attr = interested
                elif k == u"content":
                    interested_value = v
            if interested_attr:
                # special handling
                if interested_attr != u"refs":
                    self.data[interested_attr] = interested_value
                else:
                    ret = self.data.get(interested_attr, [])
                    ret.append(interested_value)
                    self.data[interested_attr] = ret

        elif tag == u"body":
            self.fsm = ( self.READ, u"body" )
        elif tag in [u"m:math", "math"]:
            self.fsm = ( self.NOT_READ, None )
            self.math_xref = None
            for (k, v) in attrs:
                if k.lower() == "xml:id":
                    self.math_xref = v
                    break
        elif tag in [u"m:annotation", u"annotation"] and attrs:
            for (k, v) in attrs:
                if k == u"encoding" and v in [u"TeX", "application/x-tex"]:
                    xref_equal = True
                    if self.math_xref is not None:
                        for (k, v) in attrs:
                            if k.lower() == "xref":
                                v = u".".join(v.split(".")[:-1])
                                if self.math_xref != v:
                                    xref_equal = False
                                break
                    if xref_equal:
                        self.text += u" %s " % _settings_local["pager"]["math_sep"][0]
                        self.fsm = ( self.READ, u"math_text" )
                    break

    def handle_endtag(self, tag):
        if tag in [u"m:annotation", u"annotation"] and self.fsm[0] == self.READ:
            self.text += u" %s " % self.MATH_SEP_END
            self.fsm = ( self.NOT_READ, None )
        elif tag in [u"m:math", "math"]:
            self.fsm = ( self.READ, u"body" )
        elif tag == u"title":
            self.fsm = ( self.NOT_READ, None )

    def handle_charref(self, name):
        if self.fsm[0] == self.READ:
            self.handle_data(u"&#%s;" % name)

    def handle_entityref(self, name):
        if self.fsm[0] == self.READ:
            self.handle_data(u"&%s;" % name)

    def handle_data(self, data):
        if self.fsm[0] == self.READ:
            if self.fsm[1] == u"body":
                self.text += data
            elif self.fsm[1] == u"math_text":

                # there can be untexified text left in index mode
                # new lines etc.
                data = mathml.fix_annotation(data)
                #if data != math().texify(data):
                #    #logger.info("Math/texified math does not match\n[%s]\n[%s]", data, math().texify(data))
                #    pass
                self.text += data
            else:
                self.data[self.fsm[1]] = data

    @staticmethod
    def create_abstract(text, self_data, env_local=None):
        """
      Get a nice abstract
    """
        if env_local is None:
            env_local = _settings_local

        # remove all the wiki tags
        text = parser.remove_wiki_tags_outside_math(text, full=True)

        text_for_abstract = text
        text_for_abstract = text_for_abstract.strip().lstrip(':')
        if len(text_for_abstract) > 0:
            while text_for_abstract[0] in ( u"<", u"{", u"[" ):
                min_found = filter(lambda x: x > 0,
                                   [text_for_abstract.find(c) for c in ( u"}\n", u">\n", u"]\n", )])
                if len(min_found) == 0:
                    break
                min_found = min(min_found)
                text_for_abstract = text_for_abstract[min_found + 1:].strip()
        else:
            logger_suspicious.warning("Empty abstract [%s]", self_data["id"])

        # just output something
        if len(text_for_abstract) < 10:
            text_for_abstract = text

        from_pos = env_local["pager"]["abstract"]["from"]
        to_pos = env_local["pager"]["abstract"]["to"]
        to_pos_final = to_pos
        if to_pos - from_pos > 0 and len(text_for_abstract) > from_pos:
            # we should not be inside math
            satisfied = False
            tmpstart = 0
            while not satisfied:
                math_pos_start = text_for_abstract.find(env_local["pager"]["math_sep"][0], tmpstart + 1, to_pos)
                # ok, we did not find but check in which round
                #
                if math_pos_start == -1:
                    satisfied = True
                    # ok, we have found math, so break it there
                    if tmpstart > 0:
                        assert tmpstart <= to_pos


                else:
                    pos_end = text_for_abstract.find(env_local["pager"]["math_sep"][1], tmpstart + 1)
                    # error if we do not find the end of math
                    if pos_end == -1:
                        logger_suspicious.warning(u"Not finished math! [%s/%s]" % (self_data[u"id"], self_data[u"url"]))
                        satisfied = True
                    else:
                        tmpstart = pos_end + len(env_local["pager"]["math_sep"][1])
                        if tmpstart > to_pos:
                            # so the end is behind what we want to use for math abstract, soo cut it if reasonably long
                            # at least 100
                            if math_pos_start > 50:
                                from_pos = to_pos = math_pos_start
                                from_pos -= 1
                            else:
                                from_pos = to_pos = tmpstart
                                to_pos += 1
                            assert to_pos >= from_pos
                            satisfied = True

            text_range = text_for_abstract[from_pos:to_pos]
            to_pos_final = from_pos
            for char in env_local["pager"]["abstract"]["delimiter"]:
                pos = text_range.rfind(char)
                if pos != -1:
                    to_pos_final = max(from_pos + pos, to_pos_final)
                    # copy everything
            to_pos_final += 1

        return text_for_abstract[:to_pos_final].strip()

    @utils.time_method
    def dict(self):
        """
    Create dictionary of interesting values to indexer.
    """

        # change all math to our eegomath egomathh
        self.text = math.math_pattern.sub(ur"%s \1 %s" % (_settings_local["pager"]["math_sep"][0],
                                                          _settings_local["pager"]["math_sep"][1]),
                                          self.text)
        self.data[u"text"] = self.text
        self.data[u"category"] = filter(lambda x: x.strip() != u"",
                                        self.data.get(u"category", u"").split(_settings_local["pager"]["delimiter"]))
        self.data[u"category"] = [x.strip().split("|")[0] for x in self.data[u"category"]]
        self.data[u"category"] = [x.strip().split("]]")[0] for x in self.data[u"category"]]
        # get abstract
        s = time.time()
        self.data[u"abstract"] = self.create_abstract(self.text, self.data)
        logger_suspicious.debug(u"  create_abstract lasted [%s]", time.time() - s)
        if len(self.data[u"abstract"]) < 100:
            logger_suspicious.critical(u"Abstract too small! [%s]", self.data["id"])

        # find out languages
        self.data[u"lang_avail"] = [x.strip() for x in
                                    self.data.get(u"lang_avail", u"").split(_settings_local["pager"]["delimiter"]) if
                                    x.strip() != u""]

        # refs do not need to be there
        if not u"refs" in self.data:
            self.data[u"refs"] = []
        self.data[u"refs_count"] = len(self.data[u"refs"])

        # not using
        self.data[u"citations"] = None

        return self.data

    @staticmethod
    def positions_in_text(where, *what):
        positions = []
        for (ssep, esep), adjust_offset in what:
            pos = 0
            find_smath = lambda x: where.find(ssep, x)
            pos = find_smath(pos)
            while pos != -1:
                # use in adjust
                esep_len = len(esep)
                if adjust_offset:
                    pos += len(ssep)
                    esep_len = 0
                found_esep = where.find(esep, pos)
                to_add_text = where[pos:esep_len + found_esep].strip("\n")
                # make few checks
                # - not found end?!!!
                # - too big?
                # - ...
                if -1 == found_esep or \
                        len(to_add_text) > 100000 or \
                   False:  # can be egomath inside to_add_text.count(ssep) != 1 or to_add_text.count(esep) != 1:
                    logger_suspicious.warning(u"Math fragment has invalid content [%s] size [%s]",
                                              to_add_text[:300],
                                              len(to_add_text))
                    positions.append((-1, None))
                else:
                    if 0 == len(to_add_text):
                        pass
                    positions.append((pos, to_add_text))
                pos = find_smath(pos + 1)
        return positions

    @staticmethod
    def no_wiki_markup(text):
        """
            Check we do not have any wiki markup.
        """
        new_text = text
        new_text = parser.remove_wiki_tags_outside_math(new_text)
        return new_text == text

    @staticmethod
    def replace_math_in_nowiki(text):
        do = True
        while do:
            do = False
            for match in parser.wiki_nowiki_remove_pattern.finditer(text):
                orig_frag = match.group()
                new_frag = orig_frag.replace(u"&lt;math", u"&lt; math")
                new_frag = new_frag.replace(u"&lt;/math", u"&lt; / math")
                if len(new_frag) != len(orig_frag):
                    text = text[:match.start()] + new_frag + text[match.end():]
                    do = True
                    break
        return text

    @staticmethod
    def remove_wiki_tags_outside_math(text, full=False):
        """
            Do not remove wiki tags inside math
            \sin{{x}} will be incorrectly replaced and wiki uses that a lot
        """
        if len(text.strip()) == 0:
            return text

        # 0. remove xml comments
        text = parser.wiki_comment_remove_pattern.sub(u"", text)

        def positions_in_text_re(where):
            positions = []
            patterns = _settings_local["pager"]["re_maths"]
            for pattern in patterns:
                for match in pattern.finditer(where):
                    positions += [( match.start(), match.end() )]
            positions.sort(key=lambda x: x[0])
            return positions

        # 1. first very simple corrections
        # wiki specific - adding : before math
        #
        text = re.compile(r"([^:]):+(%s)" % _settings_local["pager"]["wiki_math_tags"][0]).sub(r"\1\2", text)

        # positions are sorted
        def inside_math(position, _):
            for (s, e) in math_positions:
                if s < position < e:
                    return True
                if s > position:
                    return False
            return False

        def substitute(math_positions, mathobj):
            """
                Substitute only if not inside math.
            """
            if inside_math(mathobj.start(), math_positions) or inside_math(mathobj.end() - 1, math_positions):
                return mathobj.group(0)
            return mathobj.group(1)

        res_to_remove = parser.wiki_tag_remove_patterns
        if full:
            res_to_remove += parser.wiki_tag_remove_patterns_full

        math_positions = positions_in_text_re(text)
        for pattern in res_to_remove:
            repeat = True
            while repeat:
                old_text = text
                # check positions and do not remove wiki tags inside them
                # HOWEVER - this leads to problems when math is inside {{}} - TODO
                #
                text = pattern.sub(lambda x: substitute(math_positions, x), old_text)
                repeat = text != old_text
                if repeat:
                    math_positions = positions_in_text_re(old_text)

        # get smallest nowiki
        text = parser.replace_math_in_nowiki(text)

        # do some post processing from the html page itself
        #
        # leftoevers
        text = text.strip()
        text = text.replace(u"()", u"")
        to_remove_chars = u":,\""
        if full:
            to_remove_chars = u":,!{.?\""
        text = text.lstrip(to_remove_chars).strip()

        text = text.replace(u"&amp;thinsp;", u" ")
        text = text.replace(u"&thinsp;", u" ")

        return text

    @staticmethod
    def preprocess_page_math(env_dict, page):
        specific_wiki_math = [
            re.compile("\{\{\s*mvar\s*\|([^{]+?)(?:\}\}|\|[^{]*\}\})", re.U | re.DOTALL),
            re.compile("\{\{\s*math\s*\|([^{]+?)(?:\}\}|\|[^{]*\}\})", re.U | re.DOTALL),
        ]

        # specific hacks
        # {{math|Arg}}
        #
        repl = []
        wiki_specific_remove_apos = [
            ( re.compile(u"\s*''(.*?)''\s*"), ur" \1 " ),
            # u'N&lt;sub&gt;\\'\\'A\\'\\'&lt;/sub&gt;'
            ( re.compile(ur"\s*&lt;\s*sub\s*&gt;(.*?)&lt;/\s*sub\s*&gt;\s*"), ur"_{\1}" ),
            ( re.compile(ur"\s*&lt;\s*sup\s*&gt;(.*?)&lt;/\s*sup\s*&gt;\s*"), ur"^{\1}" ),
        ]
        for p in specific_wiki_math:
            for m in p.finditer(page):
                repl.append([m.start(), m.end(), m.group(1)])
        repl = sorted(repl, key=lambda x: x[0])
        for s, e, math_frag in repl[::-1]:
            for wiki_specific_remove_apo, to_replace_with in wiki_specific_remove_apos:
                math_frag = wiki_specific_remove_apo.sub(to_replace_with, math_frag)
            wiki_math_frag = u"%s %s %s" % ( env_dict["pager"]["wiki_math_tags"][0],
                                             math_frag,
                                             env_dict["pager"]["wiki_math_tags"][1] )
            page = page[:s] + wiki_math_frag + page[e:]
        if 0 != len(repl):
            logger_suspicious.info(u"Added %s specific wiki markups", len(repl))


        # \begin{cases}
        # \end{cases}
        #
        morelines_res = []
        morelines_res_innder = []
        for w in ( "cases", "align[^}]*", "eqnarray[^}]*", ".?matrix", "smallmatrix" ):
            morelines_res.append(re.compile(ur"%s([^&]*?)\\begin\{%s\}(.*?)\\end\{%s\}(.*?)%s" % (
                env_dict["pager"]["wiki_math_tags"][0], w, w, env_dict["pager"]["wiki_math_tags"][1]
            ), re.U | re.DOTALL | re.M))
            morelines_res_innder.append(re.compile(ur"(?:\s|=)*\\begin\{%s\}(.*?)\\end\{%s\}(?:\s|=|>|<|\d)*" % (w, w),
                                                   re.U | re.DOTALL | re.M))
        repl = []
        for case_re in morelines_res:
            for m in case_re.finditer(page):
                invalid = False
                fs = [m.group(1).strip(), m.group(2).strip(), m.group(3).strip()]
                for i, f in enumerate(fs):
                    if "begin" in f or "end" in f:
                        # try one more attempt
                        invalid = True
                        for r1 in morelines_res_innder:
                            if r1.match(f):
                                f = r1.match(f).group(1)
                                fs[i] = f
                                invalid = False
                                # we saved it
                                break
                        for r1 in [re.compile(ur"\s*\\begin\{[^{}]+\}\s*"),
                                   re.compile(ur"\s*\\end\{[^{}]+\}\s*")
                        ]:
                            if r1.match(f):
                                f = r1.sub("", f)
                                if len(f) < 4:
                                    invalid = False
                                    fs[i] = u""
                                    break
                        continue
                    if invalid:
                        break
                if invalid:
                    continue
                repl.append([m.start(), m.end(), fs])
            ########################### \begin{cases}

        repl = sorted(repl, key=lambda x: x[0])
        for s, e, frags in repl[::-1]:
            wiki_math_frags = []
            frag1 = frags[0]
            if 0 < len(frag1.strip()):
                wiki_math_frags.append(u"%s %s %s" % ( env_dict["pager"]["wiki_math_tags"][0],
                                                       frag1,
                                                       env_dict["pager"]["wiki_math_tags"][1] ))
            frag2 = frags[1]
            frags_split = [x.strip() for x in frag2.split(ur"\\") if 0 < len(x.strip())]
            frags_split = parser.math_split_comma_like(frags_split)
            for frag in frags_split:
                #if frag.endswith(u"\\"):
                #    frag = frag[:-2].strip()
                #else:
                #    # something fishy
                #    continue
                wiki_math_frags.append(u"%s %s %s" % ( env_dict["pager"]["wiki_math_tags"][0],
                                                       frag,
                                                       env_dict["pager"]["wiki_math_tags"][1] ))
            frag3 = frags[2]
            if 0 < len(frag3.strip()):
                wiki_math_frags.append(u"%s %s %s" % ( env_dict["pager"]["wiki_math_tags"][0],
                                                       frag3,
                                                       env_dict["pager"]["wiki_math_tags"][1] ))

            wiki_math_frag = u"\n".join(wiki_math_frags)
            page = page[:s] + wiki_math_frag + page[e:]
        if 0 != len(repl):
            logger_suspicious.info(u"Processed %s cases markups", len(repl))

        # ;
        #
        latex_pattern = env_dict["pager"]["re_math"]
        repl = []
        for m in latex_pattern.finditer(page):
            latex_math = m.group(1).strip()
            frags = parser.math_split_comma_like([latex_math])
            if len(frags) > 1:
                repl.append([m.start(), m.end(), frags])
        repl = sorted(repl, key=lambda x: x[0])
        for s, e, frags in repl[::-1]:
            wiki_math_frag = u""
            for frag in frags:
                wiki_math_frag += u" %s %s %s " % ( env_dict["pager"]["wiki_math_tags"][0],
                                                    frag,
                                                    env_dict["pager"]["wiki_math_tags"][1] )
            page = page[:s] + wiki_math_frag + page[e:]

        ########################### ;


        return page

    @staticmethod
    def math_split_comma_like(frags):
        left_brackets = "[{("
        right_brackets = "]})"
        seps = ";,"
        seps_empty = ":"
        b = 0
        last_seen = -10
        last_seen_chars = "&"

        ret = []
        for pos, f in enumerate(frags):
            was_split = False
            last_pos = 0
            for pos1, c in enumerate(f):
                if c in left_brackets:
                    b += 1
                elif c in right_brackets:
                    b -= 1
                elif c in last_seen_chars:
                    last_seen = pos1
                elif ( c in seps and f[max(0, pos1 - 1)] != u"\\" ) or \
                   ( c in seps_empty and len(f) > pos1 + 1 and f[pos1 + 1] == u" " ):
                    if b == 0 and pos1 - last_seen > 5:
                        # split
                        was_split = True
                        ret.append(f[last_pos:pos1].strip())
                        last_pos = pos1 + 1

            if not was_split:
                ret.append(f)
            else:  # last fragment
                ret.append(f[last_pos:].strip())

        return ret

#=======================
# math
#=======================
_egomath_inst = None


class math(object):
    """
   Wiki math parser.
  """
    flags = re.DOTALL | re.UNICODE | re.MULTILINE

    math_pattern = re.compile(ur'&lt;\s*math\s*&gt;(.*?)&lt;\s*/math\s*&gt;', re.DOTALL)
    math_final_matcher = re.compile(ur"(?:%s(.*?)%s|%s(.*?)%s)" %
                                    (_settings_local["pager"]["math_sep"][0].replace(u"$", ur"\$"),
                                     _settings_local["pager"]["math_sep"][1].replace(u"$", ur"\$"),
                                     _settings_local["pager"]["wiki_math_tags"][0],
                                     _settings_local["pager"]["wiki_math_tags"][1]),
                                    re.DOTALL)

    tex_annotation = ur'(?:<m:annotation [^>]*tex[^>]*>|<annotation [^>]*tex[^>]*>)(.*?)(?:</m:annotation>|</annotation>)'
    re_tex_annotation = re.compile(tex_annotation, re.DOTALL | re.MULTILINE | re.UNICODE | re.IGNORECASE)
    # mathml_db = None
    reset = False

    def __init__(self):
        global _egomath_inst

        from indexer.egomath.interface import egomath, egomath_inst

        if not egomath_inst is None:
            _egomath_inst = egomath_inst
        else:
            _egomath_inst = egomath()
        if not _egomath_inst.indexer is None:
            _egomath_inst.reset_logging()

    def parse(self, text, page_str):
        global _egomath_inst
        # if math.mathml_db is None:
        #     math.mathml_db = _math.mathdb( _settings_local )

        id_str = page_str[180:260].replace("\n", " ")

        math_field = []
        positions = parser.positions_in_text(page_str,
                                             (_settings_local["pager"]["wiki_mathml_tags"], False),
                                             (_settings_local["pager"]["wiki_mathml_tags_v2"], False),
                                             (_settings_local["pager"]["wiki_math_tags"], True),
        )
        positions.sort(key=lambda x: x[0])

        tex_start = _settings_local["pager"]["tex_start"]
        math_sep = _settings_local["pager"]["math_sep"]

        # find all maths in the parsed page and match them with their
        # counterpart in the original text (get either tex or mathml)
        #
        for i, match in enumerate(math.math_final_matcher.finditer(text)):
            start_pos = max(match.start(0) - _settings_global["indexer"]["snippet_chars"] / 2, 0)
            end_pos = min(match.end(0) + _settings_global["indexer"]["snippet_chars"], len(text) - 1)

            # invalid math
            if len(positions) <= i:
                pass
            if positions[i][0] == -1:
                continue
            math_text = positions[i][1]
            math_representation = u""
            #logger.info( u"Working on [%s] len [%s][%s]", math_text, i, len(math_text) )
            if len(math_text) > 50000:
                logger_suspicious.warning(u"Math too big [%s] in [%s]", len(math_text), id_str)
                pass
            if len(math_text) > 0:
                try:
                    # mathml version
                    #
                    if math_text.startswith(u"<m:math") or math_text.startswith(u"<math"):
                        math_tex_tmp = None
                        _bug_oneword = False
                        m = math.re_tex_annotation.search(math_text)
                        if not m:
                            logger_suspicious.warning("Did not find annotation in tex! [%s]", id_str)
                        else:
                            # do a bit of html->normal cleanup
                            math_tex_tmp = unescape_recursive(m.group(1))
                            # must be after unescape
                            math_tex_tmp = self.texify(math_tex_tmp)
                            _bug_oneword = re.compile(u"^[a-z]+$", re.U).match(math_tex_tmp.lower())
                            math_text = math_text.replace(m.group(1), math_tex_tmp)

                        math_representation = _egomath_inst.math_from_mathml(math_text)

                        # FIX one word
                        if _bug_oneword and math_representation.count("*") > 0:
                            math_representation = u"Tex: %s\nego0 : %s\nego8 : id" % (math_tex_tmp, math_tex_tmp)
                            logger_suspicious.debug(u"Fixing oneword [%s]", math_tex_tmp)

                        # Log problem
                        if math_representation is None:
                            logger_suspicious.warning(u"NULL returned from egomath [\n%s\n] in [%s]",
                                                      math_text.replace("\n", " ").replace("\"", "\\\""),
                                                      id_str)

                        if math_tex_tmp is not None and (math_representation is None or 0 == len(math_representation)):
                            # try latex...
                            math_representation = _egomath_inst.math_from_tex(math_tex_tmp)

                        if math_representation is None or 0 == len(math_representation):
                            logger_suspicious.warning(u"Empty math returned from egomath [\n%s\n] in [%s]",
                                                      math_text.replace("\n", " ").replace("\"", "\\\""),
                                                      id_str)

                            # if not math.mathml_db is None:
                            #     i = mathml.get_id( math_text )
                            #     if not i is None:
                            #         # add it to db
                            #         math.mathml_db.add_ego_math( math_representation, i )

                    # tex version
                    #
                    else:
                        # do a bit of html->normal cleanup
                        math_text = unescape_recursive(math_text)
                        math_text = self.texify(math_text, leave_nl=True)
                        # do the conversion
                        math_representation = _egomath_inst.math_from_tex(math_text)
                        # simulate text repre
                        math_text_tex = math_text.replace("\n", " ").strip()
                        math_representation = "Tex: %s\n" % math_text_tex + math_representation

                except Exception, e:
                    logger.exception(u"Cannot convert [%s] because of [%s]",
                                     math_text, utils.uni(e))
            else:
                logger_suspicious.info(u"Empty math in [%s]", id_str)

            if math_representation is None or len(math_representation) == 0:
                continue
                # convert Tex: line to ""showaeble"" tex
            # convert \d: line to math + end token so we can simulate full match
            #
            already_in = set()
            result_math = u""
            for line in math_representation.split("\n"):
                line = line.strip()
                if len(line) == 0:
                    continue
                    # deduplicity - already there
                if line in already_in:
                    continue
                already_in.add(line)

                # insert proper tags
                if not line.startswith(tex_start):
                    line = u"%s %s" % (line, math_sep[1])
                else:
                    line = u"%s %s %s %s" % (tex_start, math_sep[0],
                                             line[len(tex_start):],
                                             math_sep[1])
                result_math += u"%s\n" % line

            # ensure we get all formulae unparsed
            #
            if len(result_math) > 0:
                #math_field += self.snippet_populate(text, result_math, match, start_pos, end_pos)
                math_field += [self.snippet_populate(text, result_math, match, start_pos, end_pos)]

        return math_field

    def snippet_populate(self, text, result_math, match, start_pos, end_pos, env_dict=None):
        """
      Create one nice math snippet.
    """
        if env_dict is None:
            env_dict = _settings_local

        def _adjust(s, e, direction, (start_tag, end_tag)):
            if direction == 0:
                pos_s, pos_e = text.find(start_tag, s, e), \
                               text.find(end_tag, s, e)
                # we end first, so we need to find start
                if pos_e < pos_s or (-1 == pos_s and -1 != pos_e):
                    return max(0, text.rfind(start_tag, 0, pos_e))
                else:
                    return s
            else:
                pos_s, pos_e = text.rfind(start_tag, s, e), \
                               text.rfind(end_tag, s, e)
                if pos_e < pos_s or (-1 == pos_e and -1 != pos_s):
                    return max(0, text.find(end_tag, pos_s) + len(end_tag))
                else:
                    return e

        def _split_only_on_non_alpha(start_pos, end_pos, direction=-1):
            """
       Split on non alpha
      """
            while start_pos > 0:
                if not text[start_pos] in string.whitespace:
                    start_pos += direction
                    continue
                break
            while end_pos < len(text) - 1:
                if not text[end_pos] in string.whitespace:
                    end_pos += -direction
                    continue
                break
            return start_pos, end_pos

        math_sep = env_dict["pager"]["math_sep"]

        # ensure all words are complete (not eegom ...)
        # - then adjust start/end so it is either a complete math or not (for both math tags)
        # - again do the splitting just to be sure
        #
        start_pos, end_pos = _split_only_on_non_alpha(start_pos, end_pos, 1)

        # _settings_local["pager"]["wiki_mathml_tags"] will be converted to math_sep
        start_pos = _adjust(start_pos, match.start(0), 0, math_sep)
        end_pos = _adjust(match.end(0), end_pos, 1, math_sep)
        # however, convert also _settings_local["pager"]["wiki_math_tags"]
        start_pos = _adjust(start_pos, match.start(0), 0, _settings_local["pager"]["wiki_math_tags"])
        end_pos = _adjust(match.end(0), end_pos, 1, _settings_local["pager"]["wiki_math_tags"])

        # final adjustments
        start_pos, end_pos = _split_only_on_non_alpha(start_pos, end_pos)

        whitespace_remover = re.compile(r'\s+')
        snippet_start = whitespace_remover.sub(' ', text[start_pos:match.start(0)])
        snippet_start = snippet_start.lstrip(" ;,!?:")
        snippet_end = whitespace_remover.sub(' ', text[match.end(0):end_pos])
        math_snippet = u"... %s\n%s%s ...\n\n" % (snippet_start, result_math, snippet_end)
        return math_snippet

    def texify(self, text_str, leave_nl=False):
        """
            Wiki TeX like strings to real TeX.
        """
        # bug with %\n ...
        text_str = u"\n".join([x.strip().rstrip(u"%") for x in text_str.splitlines()])

        changed = True
        while changed:
            for (k, v) in [
                # before the others
                (u"&amp;gt;", u" \gt "),
                (u"&amp;lt;", u" \lt "),
                (u"&amp;minus;", u" - "),
                #
                (u"&amp;", u"&"),

                (u"\;", u" "),
                (u"\!", u" "),
                (u"\,", u" "),

                #
                (u"&lt;", u" \lt "),
                (u"&gt;", u" \gt "),
                (u"<", u" \lt "),
                (u">", u" \gt "),
                (u"&lt", u" \lt "),
                (u"&gt", u" \gt "),

            ]:
                old_str = text_str
                text_str = old_str.replace(k, v)
                changed = (old_str != text_str)

        # special chars?
        text_str = HTMLParser().unescape(text_str)
        for (k, v) in [
            # failsafe
            (u"&", u" "),
        ]:
            text_str = text_str.replace(k, v)

        #replace
        # USE CAREFULLY because of f(x,a) problem
        #
        changed = True
        while changed:
            old_str = text_str

            if not leave_nl:
                text_str = text_str.replace(u"\n", u" ")
                text_str = text_str.replace(u"\r", u" ")

            # some of the interpunction math does really make sense e.g., ...
            text_str = text_str.strip()
            text_str = re.compile(ur'\.\s*\.\s*\.').sub(ur'\ldots ', text_str)
            text_str = re.compile(r'(^[.,]*|[.,\\\\]*$)').sub('', text_str)
            changed = (old_str != text_str)

        return text_str.strip()
