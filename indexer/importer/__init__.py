# -*- coding: utf-8 -*-
# See main file for license.
"""
  Egomath

  @author: jm
  @date: 2013
  @version: 1.0
"""
import hashlib
import sys
import utils

_logger = utils.logger("datasets.wiki.db")
_logger_suspicious = utils.logger("datasets.suspicious")

has_backend = False
# noinspection PyBroadException
try:
    import sunburnt as solr
    has_backend = True
except Exception, e:
    _logger.error("Please, install sunburnt otherwise no indexer (solr) interaction possible!")


# noinspection PyBroadException
class _backend(object):
    """
        Backend impl.
    """
    invalid_query = -1

    def __init__(self, env_dict):
        self.host = env_dict["db"]["url"]
        self.retry = env_dict["db"]["retry_timeout"]
        self.auto_commit = env_dict["db"]["auto_commit"]
        # noinspection PyRedeclaration
        self._backend = self.connect()

    def connect(self):
        # noinspection PyUnusedLocal
        try:
            return solr.SolrInterface(self.host, mode="rw", retry_timeout=self.retry)
        except Exception, e:
            _logger.exception(u"Could not connect to [%s]", self.host)
            return None

    def get_id( self, latex ):
        """ Get unique id. """
        try:
            return hashlib.md5(latex.encode("utf-8")).hexdigest()
        except:
            _logger.exception(u"Could not get id from unicode, possible conflict [%s]", latex)
            return hashlib.md5(utils.ascii(latex)).hexdigest()

    def add( self, document_s, boosts=None ):
        """ Add a document to index. """
        docs = utils.to_array(document_s)
        try:
            for document in docs:
                document.update({
                    "id": self.get_id(document["latex"])
                })
            self._backend.add(docs, boosts)
            if self.auto_commit:
                self.commit()
            return True
        except Exception, e:
            _logger.exception(u"Could not add document to index\n[%s].",
                             utils.uni(e))
            return False

    def query_latex( self, latex, fields=None, qf=None ):
        fields = ["mathml", "status", "id", "dataset"] if fields is None else fields
        res = self.query("latex", u'"%s"' % latex, fields, 1, qf=qf)
        return None if res == _backend.invalid_query else res

    def query_id( self, id_ ):
        res = self.query("id", id_, ["*"], 1)
        return None if res == _backend.invalid_query else res

    def query( self, qfield, qvalue, fields=None, pages_count=10, qf=None ):
        """ Return search result. """
        try:
            kwargs = {}
            if not fields is None:
                kwargs["fl"] = ",".join(fields)
            qvalue = _backend._escape_for_string(qvalue)
            kwargs["q"] = u"%s:%s" % (qfield, qvalue)
            if qf is not None:
                kwargs["qf"] = qf
            kwargs["rows"] = pages_count
            return self._backend.search(**kwargs)
        except Exception, e:
            _logger.exception(u"Could not query backend [%s]." % utils.uni(e))
            _logger_suspicious.exception(u"Could not query backend [%s]." % utils.uni(e))
        return _backend.invalid_query

    @staticmethod
    def _escape_for_string( s ):
        res = u""
        slen = len(s)
        for i, c in enumerate(s):
            if i == 0 or i == slen - 1:
                res += c
                continue
            if c in ( u"\\", u'"', u"(", u")" ):
                res += u'\\' + c
            else:
                res += c
        return res

    def delete( self, docs_array ):
        """ Return search result. """
        try:
            self._backend.delete(docs_array)
            return True
        except Exception, e:
            _logger.warning(u"Could not delete from backend [%s]." % utils.uni(e))
        return False

    def commit( self ):
        # be sure we can write
        _logger.info(u"Trying to commit to index.")
        try:
            _logger.info("Committing to index.")
            self._backend.commit()
            _logger.info("Committed.")
            return True
        except Exception, e:
            _logger.warning(u"Could not commit in backend [%s]." % utils.uni(e))
        return False

    def optimise( self ):
        _logger.info("Optimising index.")
        try:
            self._backend.optimize()
            _logger.info("Optimised.")
            return True
        except Exception, e:
            _logger.warning(u"Could not optimise backend [%s]." % utils.uni(e))
        return False


class mathdb(object):
    """
        Db solr.
    """
    status_ok = 0
    failed_mathml = u"conversionfailed"

    def __init__(self, env_dict):
        self.encoding = "utf-8"
        self.db = _backend(env_dict)
        self.db.connect()
        self.added_count = 0

    def get_ok( self, key, default_type=None, **kwargs ):
        res = self.db.query_latex(key,
                                  fields=kwargs["fields"] if "fields" in kwargs else None,
                                  qf=kwargs["qf"] if "qf" in kwargs else None)
        if not res is None and 0 < len(res.result.docs):
            # add special anchor
            # if not "was_here2" in res.result.docs[0]["dataset"]:
            #     self.added_count += 1
            #     self.db.auto_commit = False
            #     self.add_dataset( res.result.docs[0]["id"], "was_here2" )
            #     if self.added_count > 1000:
            #         self.added_count = 0
            #         self.db.commit()

            if res.result.docs[0]["mathml"][-1].strip() == mathdb.failed_mathml:
                res = None
            else:
                # store dataset
                if "add_info" in kwargs:
                    kwargs["add_info"].update(res.result.docs[0])
                res = res.result.docs[0]["mathml"][0]
        else:
            res = None
        return res or default_type

    def get_not_ok( self, key, default_type=None ):
        res = self.db.query_latex(key)
        if not res is None and 0 < len(res.result.docs):
            if res.result.docs[0]["mathml"][-1].strip() != mathdb.failed_mathml:
                res = None
            else:
                pass
        else:
            res = None
        return res or default_type

    @staticmethod
    def use_existing_doc( doc ):
        del doc["_version_"]
        del doc["latex_text"]

    def delete_invalid( self, id_str ):
        self.db.delete( [id_str] )
        self.db.commit()

    def _create_doc( self, latex, mathml, convert_js, docs=None, url=None, dataset=None, create_ego=False ):
        doc = {
            "mathml": utils.uni(mathml),
            "latex": latex,
            "latex_len": len(latex),
            "documents": docs,
            "url": url,
            "dataset": utils.to_array(dataset),
        }
        for k in ( "result", "status", "status_code", "log" ):
            if k in convert_js:
                doc[k] = convert_js[k]

        if create_ego:
            doc["ego_math"] = ego_convert(latex, mathml[-1])
        return doc

    def add_ok( self, key, value, convert_js, docs=None, urls=None, dataset=None, create_ego=False ):
        self.db.add(self._create_doc(
            key, value, convert_js, docs, urls, dataset, create_ego))

    # noinspection PyUnusedLocal
    def add_not_ok( self, key, _1, convert_js, docs=None, urls=None, dataset=None, create_ego=False  ):
        self.db.add(self._create_doc(
            key, mathdb.failed_mathml, convert_js, docs, urls, dataset, create_ego))

    def add_dataset( self, id_, dataset, **kwargs ):
        res = self.db.query_id(id_)
        assert 1 == len(res.result.docs)
        doc = res.result.docs[0]
        mathdb.use_existing_doc(doc)
        doc["dataset"] = [dataset] + list(doc["dataset"])
        for k, v in kwargs.iteritems():
            if k in doc:
                doc[k] = list(doc[k]) + utils.to_array(v)
        self.db.add(doc)

    # noinspection PyUnusedLocal
    def store(self, ignore_threshold_bool=False, after_page=False):
        # do not commit if we do autocommit
        if self.db.auto_commit and after_page:
            return
        self.db.commit()


# noinspection PyBroadException
def ego_convert( latex_str, mathml_str ):
    """
        Convert both formats.
    """
    from indexer.egomath.interface import egomath_inst

    mathml_repre = u"mathml:problem"
    tex_repre = u"tex:problem"
    mathmldone = False

    # noinspection PyUnusedLocal
    try:
        if not mathml_str is None and \
                len(mathml_str) > 0 and \
                mathml_str != mathdb.failed_mathml:
            mathml_repre = egomath_inst.math_from_mathml(mathml_str)
        mathmldone = True
        if not latex_str is None and \
                len(latex_str) > 0:
            tex_repre = egomath_inst.math_from_tex(latex_str)
            latex_str_cleanup = egomath_inst.math_from_tex_cleanup(latex_str)
            if latex_str_cleanup != latex_str:
                _logger.info(u"Changed\n[%s] to\n[%s]", latex_str, latex_str_cleanup)
            pass
        else:
            sys.exit("Fatal error")
    except Exception, e:
        _logger.exception("%s exception [%s]",
                         "MathML" if mathmldone is False else "TeX",
                         latex_str)
    return u"mathml:\n" + utils.uni(mathml_repre), u"tex:\n" + utils.uni(tex_repre)
