# -*- coding: utf-8 -*-
import os
import sys
import cPickle
import codecs
import converters
import utils

utils.add_to_path(sys, os.path.join(os.path.dirname(__file__), '..'))

from converters import mathml
from indexer.importer import mathdb

logger = utils.logger('datasets.wiki.math')
logger_suspicious = utils.logger("datasets.suspicious")


class page_to_store(object):
    def __init__(self, where, filename):
        self._filename = filename
        self._where = where

    @staticmethod
    def title_to_path( dir_str, title_str ):
        file_name = title_str.replace("*", "{star}"). \
            replace("/", "{in}"). \
            replace("?", "{question}"). \
            replace(":", "{colon}"). \
            replace("\\", "{in}")
        return os.path.join(dir_str, file_name[0], file_name)

    @staticmethod
    def path_to_url( path_str ):
        return path_str.replace(".html", ""). \
            replace(u"{star}", u"*"). \
            replace(u"{in}", u"/"). \
            replace(u"{question}", u"?"). \
            replace(u"{colon}", u":"). \
            replace(u"{in}", u"\\")

    def exists(self):
        return os.path.exists(self.title_to_path(self._where, self._filename))

    def store(self, what_str):
        dir_where = os.path.dirname(self.title_to_path(self._where, self._filename))
        # ensure paths exists
        if not os.path.exists(dir_where):
            os.makedirs(dir_where)
            # write it
        import codecs

        codecs.open(self.title_to_path(self._where, self._filename),
                    encoding='utf-8',
                    mode="wb").write(what_str)


class mathpickles(object):
    THRESHOLD_TO_STORE = 1000

    def __init__(self, filename_mathml_ok, filename_mathml_fail, buffering=None):
        self.encoding = "utf-8"
        self._filename_ok = filename_mathml_ok
        self._filename_fail = filename_mathml_fail

        self._math_ok = {}
        if os.path.exists(self._filename_ok):
            f = self._readf(self._filename_ok, True, buffering=buffering)
            self._math_ok = cPickle.load(f)
            f.close()
        self._math_ok_len = len(self._math_ok)

        self._math_not_ok = {}
        if os.path.exists(self._filename_fail):
            f = self._readf(self._filename_fail, True, buffering=buffering)
            self._math_not_ok = cPickle.load(f)
            f.close()
        self._math_not_ok_len = len(self._math_ok)

    def _readf( self, name_str, raw=False, buffering=None ):
        if raw:
            return open(name_str, "rb", buffering)
        else:
            return codecs.open(name_str, "rb", self.encoding)

    def _writef( self, name_str, raw=False ):
        if raw:
            return open(name_str, "wb+")
        else:
            return codecs.open(name_str, "wb+", self.encoding)

    def get_ok( self, key, default_type=None, **kwargs ):
        return self._math_ok.get(key, default_type)

    def get_not_ok( self, key, default_type=None ):
        return self._math_not_ok.get(key, default_type)

    def add_ok( self, key, value, convert_js, docs=None, url=None ):
        self._math_ok[key] = value

    def add_not_ok( self, key, value, convert_js, docs=None, url=None ):
        self._math_not_ok[key] = value

    def store(self, ignore_threshold_bool=False, after_page=True):
        if ignore_threshold_bool or self._math_ok_len + self.THRESHOLD_TO_STORE < len(self._math_ok):
            self._math_ok_len = len(self._math_ok)
            f = self._writef(self._filename_ok, True)
            cPickle.dump(self._math_ok, f)
            f.close()
        if ignore_threshold_bool or self._math_not_ok_len + self.THRESHOLD_TO_STORE < len(self._math_not_ok):
            self._math_not_ok_len = len(self._math_not_ok)
            f = self._writef(self._filename_fail, True)
            cPickle.dump(self._math_not_ok, f)
            f.close()


def set_dataset( db, latex, dataset ):
    db_inst = db.db
    res = db_inst.query_latex( latex ).result.docs
    if len(res) == 0:
        logger.warning( u"Not found [%s]", latex )
        return
    id_ = res[0]["id"]
    kwargs = {
        "q": "id:" + id_,
    }
    q = db_inst._backend.search(**kwargs)
    if q.result.numFound > 0:
        doc = q.result.docs[0]
        mathdb.use_existing_doc( doc )
        doc["dataset"] = [dataset]
        db_inst.add( doc )


math_parser = None


def convert_wikimath_to_realmath( env_dict,
                                  wiki_math_match,
                                  mathml_pickled,
                                  url,
                                  doc,
                                  total_count,
                                  formula_unique=None,
                                  try_one_more_if_invalid=True ):
    """
     The page we got should be wiki tag free; however, it will contain only
     basic math &lt;math&gt; B \gt &lt;/math&gt; which can contain
     non latex characters &gt; instead of \gt
     - we must fix this

     - get latex math from wiki math
     - try to get mathml from dictionary
        - if not in dict store it after fetching
     - stupid replace of wiki_math with mathml representation

     fix e.g., &gt; or even worse &amp;gt;
  """
    from _parser import math as _math_parser
    global math_parser
    if math_parser is None:
        math_parser = _math_parser()

    latex_math = wiki_math_match.group(1)
    # invalid math - not ended e.g., 26358420
    if env_dict["pager"]["wiki_math_tags"][0] in latex_math:
        logger_suspicious.warning( u"Math includes another math start elem - truncating [%s][%s]", doc, latex_math[:100] )
        latex_math = latex_math[:latex_math.find(env_dict["pager"]["wiki_math_tags"][0])]

    latex_math = math_parser.texify(latex_math)
    latex_math_with_mbox = converters.latex( latex_math, full=False ).str
    latex_math = converters.latex( latex_math ).str

    # what if math is not finished?
    if not formula_unique is None:
        formula_unique.add( latex_math )

    if not len(latex_math) < 2 * 1024:
        logger_suspicious.warning( u"Long latex [%s]", latex_math.replace(u"\n", u"") )

    if "&" in latex_math or "amp;" in latex_math:
        pass

    wiki_math = u"%s%s%s" % ( env_dict["pager"]["wiki_math_tags"][0],
                              latex_math,
                              env_dict["pager"]["wiki_math_tags"][1] )
    # set dataset
    dataset = env_dict["wiki"]["dataset"]
    #set_dataset( mathml_pickled, latex_math, env_dict["wiki"]["dataset"] )

    add_info = {}
    mathml_text = mathml_pickled.get_ok(latex_math_with_mbox,
                                        add_info=add_info,
                                        qf="dataset:wiki-2013") if not latex_math_with_mbox is None else None
    latex_math_db_id = mathml_pickled.db.get_id(latex_math_with_mbox)

    if env_dict["mathml"]["convert"] and 0 < len(latex_math):
        try:
            if not mathml_text:
                should_add = True
                convert_js = None
                if not env_dict["mathml"]["convert_latex"] is None:
                    if mathml_pickled.get_not_ok(latex_math_with_mbox) is None:
                        mathml_text, convert_js = mathml.from_latex(latex_math_with_mbox)
                    else:
                        # we know mathml is not valid
                        mathml_text = wiki_math
                        logger.warning( u"Using wiki math because conversion failed [%s]", latex_math )
                        should_add = False

                if should_add:
                    status_code = 10
                    if convert_js is not None:
                        status_code = int(convert_js["status_code"])
                    if mathml_text and status_code < 2:
                        logger.info( u"Done math: %s [%s]",
                                     utils.ascii(latex_math, errors="replace"),
                                     latex_math_db_id )
                        if not env_dict["mathml"]["convert_latex"] is None:
                            assert not convert_js is None
                            mathml_pickled.add_ok( latex_math_with_mbox, mathml_text, convert_js, [doc], [url], dataset, create_ego=True )
                    else:
                        msg = u"Failed conversion of [%s] [%s] resp. [%s]" % (
                              latex_math, wiki_math_match.group(1), converters.latex(wiki_math_match.group(1)).str)
                        logger_suspicious.warning( msg )
                        logger.warning( msg )
                        if not convert_js is None:
                            mathml_text = wiki_math
                            mathml_pickled.add_not_ok( latex_math_with_mbox, None, convert_js, [doc], [url], dataset, create_ego=True )
                        else:
                            logger.error( u"Returned js is None for [%s]", latex_math )
            else:
                logger.debug( u"Found latex in db [%s].", total_count )
                datasets = add_info["dataset"]
                if not dataset in datasets:
                    mathml_pickled.add_dataset( latex_math_db_id, dataset )

                # add it to the text
                mathml_text = mathml.add_id( mathml_text, latex_math_db_id )


        except Exception, e:
            logger.exception( u"Exception at [%s] [%s]", utils.ascii(doc), mathml_pickled.db.get_id(latex_math_with_mbox) )


    # mostly debugging
    else:
        mathml_text = wiki_math

    try:
        # we have mathml text - but do we have the annotation?
        # - different versions of converters do not output it
        # <m:math display="inline"><m:semantics><m:mi>c</m:mi><m:annotation-xml encoding="MathML-Content"><m:ci>c</m:ci></m:annotation-xml></m:semantics></m:math>
        # vs <annotation id="p1.1.m1.1b" encoding="application/x-tex" xref="p1.1.m1.1.cmml">w</annotation>
        if _math_parser.re_tex_annotation.search(mathml_text) is None:
            # this can mean that we either do not have mathml
            for end_tag in ( "</math>", "</m:math>" ):
                if mathml_text.endswith(end_tag):
                    # we have mathml but no annotation
                    if end_tag == "</math>":
                        annotation = u"<annotation encoding=\"application/x-tex\">%s</annotation>" % latex_math
                    else:
                        annotation = u"<m:annotation encoding=\"application/x-tex\">%s</m:annotation>" % latex_math
                    mathml_text = mathml_text[:-len(end_tag)] + annotation + mathml_text[-len(end_tag):]
                    break



        mathml_text = utils.uni(mathml_text)

        # post processing
        # - converter problem
        #
        for to_remove in ( u"\end{document}", u"nowiki" ):
            if to_remove in mathml_text:
                logger.warn(u"Invalid math [%s]", mathml_text)
                # set to invalid
                mathml_pickled.delete_invalid( latex_math_db_id )
                if try_one_more_if_invalid:
                    return convert_wikimath_to_realmath( env_dict,
                                      wiki_math_match,
                                      mathml_pickled,
                                      url,
                                      doc,
                                      total_count,
                                      formula_unique,
                                      try_one_more_if_invalid=False )
            mathml_text = mathml_text.replace(to_remove, "")

    except UnicodeEncodeError, e:
        logger.warning(u'unicode decode error [%s]', repr(e))

    mathml_text = u'\n</pre>\n<div style="border-width:2px;border-color:red;border-style:solid;">%s</div>\n<pre>\n'\
                  % mathml_text

    return [(wiki_math_match.start(0),
            wiki_math_match.end(0),
            mathml_text)]
