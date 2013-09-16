# -*- coding: utf-8 -*-
# See main file for license.
#
import codecs
import glob
import logging
import os
import re
import shutil
import sys
import time
import urllib
import urllib2

sys.path += [os.path.join(os.path.dirname(__file__), '../..')]
import utils

logger = utils.logger('datasets.wiki')
logger_suspicious = utils.logger("datasets.suspicious")

import dump
import templates
from datasets import analyse_one_page_generic

adapter_glob = None
import sunburnt as sunburnt
from indexer.solr import adapter as adapter_file
from indexer.solr import document
adapter_file.solr = sunburnt


#
#
#
def _add_to_index( env, meta_dict, file_str, logger ):
    """
    Default index function based on settings.
    """
    global adapter_glob
    if adapter_glob is not None:
        adapter = adapter_glob
    else:
        logger.warning( u"Connecting to index..." )
        adapter = adapter_file.adapter(env)
        adapter_glob = adapter
    doc = document(
        env["metadata"]["known_keys"].keys(),
        meta_dict,
        env,
    )
    return adapter.add(doc, boosts=env["metadata"]["boosts"])
    #logger.info(u"Added to index [%s]", file_str)


def _delete_index( env, logger ):
    """
    Default index function based on settings.
    """
    global adapter_glob
    if adapter_glob is not None:
        adapter = adapter_glob
    else:
        logger.warning( u"Connecting to index..." )
        adapter = adapter_file.adapter(env)
        adapter_glob = adapter
    adapter.delete( queries=["*:*"] )
    adapter.commit()
    logger.info(u"Deleted index")


def _commit_to_index( env_dict ):
    """
    Final commit after processing.
  """
    from indexer.solr import adapter as adapter_file

    adapter = adapter_file.adapter(env_dict)
    adapter.commit()
    if env_dict["indexer"]["optimise"]:
        adapter.optimise(maxSegments=1)


#
#
#
def _analyse_one_page( (env, pos, file_str) ):
    return analyse_one_page_generic(env, pos, file_str, logger, dump.pager.page_to_dict, _add_to_index)


#===============================
# wiki file -> wikis for parallel
#===============================

def _wiki_dump_to_many_dumps( env_dict ):
    """
    Grab one huge wiki page and make small ones.
  """
    wiki_file = env_dict["wiki"]["big_xml"]
    if not os.path.exists(wiki_file):
        logger.warning(u"Wiki [%s] does not exists!", wiki_file)
        return

    chunk_size = env_dict["wiki"]["wikis_file_buffer"]
    buffer_size = chunk_size
    file_limit = env_dict["wiki"]["wikis_file_limit"]

    pos = 0
    buf_leftover = ""

    def should_end( b ):
        if b == "":
            raise IOError("end reached")

    wiki_file_out_templ = wiki_file + u".part%s.xml"

    with open(wiki_file, 'rb') as f_wiki:
        buf = f_wiki.read(chunk_size)
        to_find = ">"
        first_page = buf.find(to_find)
        header = buf[:first_page + len(to_find)]
        footer = "\n</mediawiki>"

    page_end = "</page>"
    first_time = True
    try:
        with open(wiki_file, 'rb', buffer_size) as f_wiki:
            while buf != "":
                read = 0
                pos += 1
                wiki_file_out = unicode(wiki_file_out_templ % pos)
                with open(wiki_file_out, 'wb+') as f_out:
                    logger.info("Working on [%s]", wiki_file_out)
                    if not first_time:
                        f_out.write(header)
                    else:
                        first_time = False
                    while read < file_limit:
                        buf = buf_leftover + f_wiki.read(chunk_size)
                        buf_leftover = ""
                        should_end(buf)
                        read += len(buf)
                        f_out.write(buf)
                        # find page
                    buf = f_wiki.read(chunk_size)
                    if buf != "":
                        page_end_pos = buf.find(page_end)
                        assert page_end_pos >= 0, "something fishy happened"
                        page_end_pos += len(page_end)
                        f_out.write(buf[:page_end_pos])
                        buf_leftover = buf[page_end_pos:]
                        f_out.write(footer)
    except IOError:
        pass


#===============================
# wiki math files -> wiki math file
#===============================

# noinspection PyBroadException
def _wiki_maths_to_wiki_math( env_dict ):
    """
        Create one wiki.
    """
    xml_math_input = env_dict["wiki"]["xml_math_output"].replace("%s", "*")
    xml_math_output = env_dict["wiki"]["xml_math_output_big"]
    dest = open(xml_math_output, 'wb')
    for filename in glob.iglob(xml_math_input):
        if os.path.basename(xml_math_output) in filename:
            continue
        logger.info("Working on [%s]", filename)
        shutil.copyfileobj(open(filename, 'rb'), dest)
    dest.close()


#===============================
# wiki file -> math wiki file
#===============================

# noinspection PyBroadException
def _wiki_dump_to_huge_math_pages( params ):
    """
        Grab one huge wiki page and have fun with it while creating one huge math page file.
    """
    try:
        if isinstance(params, (list, tuple)):
            env_dict, pos, file_str = params
            wiki_xml_file_glob = file_str
        else:
            env_dict = params
            wiki_xml_file_glob = env_dict["wiki"]["xml"]

        for file_inst in glob.iglob(wiki_xml_file_glob):
            _wiki_dump_to_huge_math_pages_one(env_dict, file_inst)
    except:
        logger.exception(u"_wiki_dump_to_huge_math_pages failed.")


def _wiki_dump_to_huge_math_pages_one( env_dict, wiki_xml_file ):
    """
    Grab one huge wiki page and have fun with it while creating one huge math page file.
  """
    wiki_xml_math_output = env_dict["wiki"]["xml_math_output"] % os.path.basename(wiki_xml_file)

    logger.warning(u"Started extracting math pages from [%s] to [%s]",
                   wiki_xml_file, wiki_xml_math_output)

    # load wiki dump
    #
    wiki_page_dumper = dump.pager(
        wiki_xml_file,
        env_dict["pager"]["delimiter"],
        env_dict["pager"]["buffer"])

    # for all pages and for all wiki maths
    # - try to find must_exist
    # -- if true output
    #
    must_exist = env_dict["pager"]["identify_by"]
    with codecs.open(wiki_xml_math_output, encoding='utf-8', mode='wb') as huge_math_output:
        math_pages = 0
        for pages_done, page in enumerate(wiki_page_dumper.pages()):
            if page and must_exist in page:
                math_pages += 1
                #logger.info( u"Pages done:[%d] Math:[%d]", pages_done, math_pages )
                huge_math_output.write(page)
            else:
                if not page:
                    logger_suspicious.warning(u"Page is null - [%d]", pages_done)

    logger.info(u"Stopped extracting math pages from [%s] to [%s], total [%s]",
                wiki_xml_file, wiki_xml_math_output, math_pages)


#===============================
# huge math wiki file -> pages
#===============================

def _huge_math_page_to_pages( env_dict ):
    """
    Grab one huge wiki page and have fun with it while creating all pages.
    """
    import _math
    wiki_xml_math_output = env_dict["wiki"]["xml_math_output_big"]
    #wiki_xml_math_output = env_dict["wiki"]["xml_math_output_test"]

    from indexer.egomath.interface import egomath_inst

    egomath_inst.reset_logging()

    wiki_pages_output = env_dict["wiki"]["pages_output"]
    pickle_mathml_ok = env_dict["converters"]["latexml"]["pickle_ok"]
    pickle_mathml_fail = env_dict["converters"]["latexml"]["pickle_fail"]

    logger.info(u"Started separating pages from [%s] to [%s]",
                wiki_xml_math_output, wiki_pages_output)

    # load wiki dump
    #
    wiki_page_dumper = dump.pager(wiki_xml_math_output,
                                  env_dict["pager"]["delimiter"],
                                  env_dict["pager"]["buffer"])

    # try to load pickled mathml (ok/fail)
    #
    converted_mathml = None
    if env_dict["mathml"]["convert"] == "pickle":
        buffering = 100 * 1024 * 1024
        converted_mathml = _math.mathpickles(pickle_mathml_ok, pickle_mathml_fail, buffering=buffering)
    elif env_dict["mathml"]["convert"] == "db":
        converted_mathml = _math.mathdb(env_dict)

    latex_pattern = env_dict["pager"]["re_math"]
    title_pattern = re.compile(env_dict["pager"]["re_title"], re.DOTALL)
    total_formula_count = 0
    formula_unique = set() if env_dict["wiki"]["collect_stats"] else None
    pages_done = 0
    converted_mathml_cnt = 0
    from collections import defaultdict


    pages_formula = defaultdict(int)

    # for all pages and for all wiki maths
    #
    for pages_done, page in enumerate(wiki_page_dumper.pages(templates.htmltemplate)):
        logger.info(u'Done %d pages', pages_done)
        # if title already exists do not write
        try:
            title = title_pattern.search(page).group(1).replace(" ", "_")
            url = u"http://en.wikipedia.org/wiki/%s" % title
            assert not u"$title" in title
            page_store = _math.page_to_store(wiki_pages_output, title + ".html")
            if not env_dict["pager"]["overwrite"] and page_store.exists():
                logger.warning(u"Page exists [%s] [%d]", title, pages_done)
                continue
        except Exception, e:
            logger.error(u"Could not store page because of %s", repr(e))
            continue

        from _parser import parser
        page = parser.preprocess_page_math(env_dict, page)


        # the page we got should be wiki tag free; however, it will contain only
        # basic math &lt;math&gt; B \gt &lt;/math&gt; which can contain
        # non latex characters &gt; instead of \gt
        # - we must fix this
        #
        page_replacements = []
        page_formula_count = 0
        for wiki_math_iter in latex_pattern.finditer(page):
            page_formula_count += 1
            total_formula_count += 1

            page_replacements += \
                    _math.convert_wikimath_to_realmath(
                        env_dict,
                        wiki_math_iter,
                        converted_mathml,
                        url,
                        title,
                        total_formula_count,
                        formula_unique)
        pages_formula[page_formula_count] += 1

        info_msg = u"# of formulae on page [%s] is [%d], total [%d]" % (
            utils.ascii(title), page_formula_count, total_formula_count)
        if page_formula_count == 0:
            logger_suspicious.warning(info_msg + u" -> skipping 0.")
            logger.warning(info_msg)
            continue
        else:
            logger.warning(info_msg)

        # create the page
        #
        tmp = ""
        last = 0
        e = None
        for (s, e, r) in page_replacements:
            tmp += page[last:s] + r
            last = e
        tmp += page[e:]
        page = tmp

        # store the page
        try:
            page_store.store(page)
        except IOError, e:
            logger.error(u"Could not store [%s] page because of %s", title, repr(e))

        # store mathml pickler if it changed
        if not env_dict["mathml"]["convert"] is None:
            converted_mathml_cnt += 1
            if converted_mathml_cnt > 100:
                converted_mathml_cnt = 0
                converted_mathml.store(after_page=True)

    if not env_dict["mathml"]["convert"] is None:
        converted_mathml.store()

    info_msg = u"# of pages [%s], # of formulas [%s], # of unique [%s]" % \
               (pages_done,
                total_formula_count,
                len(formula_unique) if not formula_unique is None else u"<not collected>")
    distribution = u""
    for k in sorted(pages_formula.keys()):
        distribution += u"%s:%s, " % (k, pages_formula[k])
    for msg in ( distribution, info_msg ):
        logger_suspicious.warning(msg)
        logger.warning(msg)


def _huge_math_page_texhtml( env_dict ):
    """
        Grab one huge wiki page and have fun with it while creating all pages.
    """
    wiki_xml_math_output = env_dict["wiki"]["big_xml"]
    #wiki_xml_math_output = env_dict["wiki"]["xml_math_output_big"]
    wiki_xml_math_output = env_dict["wiki"]["xml_math_output_test"]

    # load wiki dump
    #
    wiki_page_dumper = dump.pager(wiki_xml_math_output,
                                  env_dict["pager"]["delimiter"],
                                  env_dict["pager"]["buffer"])

    from HTMLParser import HTMLParser

    ht = HTMLParser()

    titles = []
    title_pattern = re.compile(env_dict["pager"]["re_title"], re.DOTALL)
    uniq = set()

    # def do_texhtml( page ):
    #     total = 0
    #     for r in re.compile(u"&lt;.*?texhtml.*?&gt;(.*?)&lt;/.*?&gt;").finditer(page):
    #         found = True
    #         total += 1
    #         #html = r.group()
    #         #msg = u"%s\n\t%s\n\t%s" % (ht.unescape(html), html, r.group(1))
    #         norm = converters.latex.normalise(r.group(1).strip())
    #         if not norm in uniq:
    #             uniq.add(norm)
    #             msg = ht.unescape(r.group(1)).replace(u"&nbsp;", " "). \
    #                 replace(u"<sub>", u"_"). \
    #                 replace(u"<sup>", u"^"). \
    #                 replace(u"<var >", u" ")
    #             logger.info(msg)
    #     return total

    def do_title( page ):
        try:
            title = title_pattern.search(page).group(1)
            titles.append(title)
        except:
            logger.warning(u"Could not parse title [%s]", page[:500])

    # try to load pickled mathml (ok/fail)
    # &lt;span class=&quot;texhtml&quot;&gt;?&lt;/span&gt;
    total = 0
    total_pages = 0
    pages_done = 0
    for pages_done, page in enumerate(wiki_page_dumper.pages(templates.htmltemplate)):

        if pages_done % 100000 == 0:
            logger.info(u"Total formulas: %s, On pages: %s, Unique: %s, Done [%s]" %
                        ( total, total_pages, len(uniq), pages_done ))
        do_title(page)
        # found = do_texhtml( page )
        # if found > 0:
        #     total_pages += 1

    if len(titles) > 0:
        with codecs.open("all.titles", mode="w+", encoding="utf-8") as fout:
            for title in titles:
                fout.write(title + "\n")
    print "Pages done: %s, Total formulas: %s, On pages: %s, Unique: %s" % \
          ( pages_done, total, total_pages, len(uniq) )



def _get_url( env_dict, query, default=None ):
    url = env_dict["backend_host"] + "select?q=" + urllib.quote_plus(query)
    if default is None:
        url += u"&start=0&mqo=10&fl=id,title&wt=json&indent=true"
    else:
        url += default
    # semantics
    #  math=R_i+semantics+k+%5Cneq+0&q=
    req = urllib2.Request( url )
    f = urllib2.urlopen( req )
    response = f.read( )
    f.close()
    import json
    js = json.loads( response )
    return js, response


def _test_queries_one_run( env_dict, logger, test_queries, additional_params, default_params ):
    d = {}
    d["per_query"] = {
        "header": u"type : num        : q       : \"# found\" : QTime  : use_payload  : use_mqo  : use_facet  : use_hl  : use_only_equal \n",
        "expected": [u"type  : $query_pos : $query : $num_found  : $qtime : $use_payload : $use_mqo : $use_facet : $use_hl : $use_only_equal \n"],
        "values": [],
    }
    d["per_query_simple"] = {
        "header": u"num : \"# found\" \n",
        "expected": [u"$query_pos : $num_found \n"],
        "values": [],
    }
    # type : q : qtime : q_type
    d["per_qtime"] = {
        "header": u"type : num        : q      : qtime : qtype \n",
        "expected": [
                      u"type   : $query_pos : $queryf : $prep_hl : prep_hl \n",
                      u"type   : $query_pos : $queryf : $prep_qm : prep_qm \n",
                      u"type   : $query_pos : $queryf : $prep_f  : prep_f \n",
                      u"type   : $query_pos : $queryf : $proc_hl : proc_hl \n",
                      u"type   : $query_pos : $queryf : $proc_qm : proc_qm \n",
                      u"type   : $query_pos : $queryf : $proc_f  : proc_f \n",
        ],
        "values": [],
    }
    query_pos = 0
    for q in [ x.strip() for x in test_queries.splitlines() if len(x.strip()) > 0 ]:
        for add in additional_params:
            query_pos += 1
            if logger:
                logger.info( "Executing [%s]", query_pos )
            try:
                js, resp = _get_url( env_dict, q, add + default_params )
            except:
                if logger:
                    logger.exception( "Executing [%s]", q + add + default_params )
                continue

            #r_str += u"%s - payloads:%s mqo:%s: %s : %s : %s : %s : %s : %s : %s : %s\n" % \
            prepare, process = js["timing"].split( "process={" )
            timing = { "prepare" : {}, "process" : {} }
            pattern = re.compile( ",([a-z_]+?)=\{time=(\d+.\d+)\}" )
            for m in pattern.finditer(prepare):
                timing["prepare"][m.group(1)] = m.group(2)
            for m in pattern.finditer(process):
                timing["process"][m.group(1)] = m.group(2)
            js["timing"] = timing

            use_payload = js["responseHeader"]["params"].get( "mpayload", "true" )
            use_mqo = js["responseHeader"]["params"]["mqo"]
            use_facet = js["responseHeader"]["params"].get( "facet", "false" )
            use_hl = js["responseHeader"]["params"].get( "hl", "false" )
            use_only_equal = js["responseHeader"]["params"].get( "m_only_equal", "false" )
            num_found = js["response"]["numFound"]
            qtime = js["responseHeader"]["QTime"]
            prep_hl = js["timing"]["prepare"]["highlight"]
            prep_qm = js["timing"]["prepare"]["query_math"]
            prep_f = js["timing"]["prepare"]["facet"]
            proc_hl = js["timing"]["process"]["highlight"]
            proc_qm = js["timing"]["process"]["query_math"]
            proc_f = js["timing"]["process"]["facet"]

            query = q.replace( ":", " " )
            queryf = utils.subst_str(u"$query - $use_payload - $use_mqo - $use_facet - $use_hl - $use_only_equal",
                                     locals())
            for k, v in d.iteritems():
                for e in v["expected"]:
                    line = utils.subst_str( e, locals() )
                    v["values"].append(line)

    return d


def _test_queries( env_dict ):
    env_dict["indexer"]["mode"] = "r"
    default_params = env_dict["test_queries"]["default_params"]
    test_queries = env_dict["test_queries"]["queries"]
    additional_params = env_dict["test_queries"]["params"]

    # warm up
    for i in range(3):
        logger.info( u"Warm up run [%s]", i )
        _test_queries_one_run( env_dict, None, test_queries, additional_params, default_params )

    d = _test_queries_one_run( env_dict, logger, test_queries, additional_params, default_params )
    for k, v in d.iteritems():
        vals = u"".join( v["values"] )
        logger.critical( u"\n%s\n%s%s", k, v["header"], vals )

    test_queries = env_dict["test_queries"]["queries_qa"]
    d = _test_queries_one_run( env_dict, logger, test_queries, additional_params, default_params )
    for k, v in d.iteritems():
        if k == "per_query_simple":
            vals = u"".join( v["values"] )
            logger.critical( u"\n%s\n%s%s", k, v["header"], vals )


def _analyse_full( env_dict ):
    #
    info = raw_input("key info")
    logger.warning( "Info key: %s", info )

    if "logs_file_runs" in env_dict:
        log_file = "unknown file"
        _log = logger
        while _log.parent is not None:
            _log = _log.parent
        for h in _log.handlers:
            if isinstance( h, logging.FileHandler ):
                log_file = h.baseFilename
                break
        with codecs.open( env_dict["logs_file_runs"], encoding="utf-8", mode="a+" ) as fout:
            fout.write( u"<%s>: %s\n" % (log_file, info) )

    # delete everything
    _delete_index( env_dict, logger )
    # solr info
    stats_url = "/select?q=*:*&stats=true&stats.field=category&stats.field=citations_count&stats.field=math_count&rows=0&indent=true"
    utils.info_solr_home( env_dict, logger, stats_url=stats_url )
    # process - index
    import processing
    s = time.time()
    processing.process(env_dict, exported_process, None)
    e = time.time()
    logger.info( u"Processing method took [%s]s ([%s]m)", e - s, (e - s) / 60.0 )
    # commit
    env_dict["indexer"]["optimise"] = True
    _commit_to_index(env_dict)
    logger.info( u"Committed to index" )
    # solr info
    info = {}
    utils.info_solr_home( env_dict, logger, stats_url=stats_url, info_dict=info )
    # time
    info["index_time"] = u"%s:%s:%s\n" % ( u"type", u"index time", (e - s) )
    lgr_str = u"\n"
    for v in info.values():
        lgr_str += v + "\n"
    logger.info( lgr_str )
    # do performance testing
    _test_queries( env_dict )



#===============================
# exported
#===============================

def update_settings( what_to_do, settings_inst ):
    """
    Change settings with this dataset.
    """
    from settings import smart_update
    from _settings import settings

    smart_update(settings_inst, settings)
    # ok, we want to have parallel
    if what_to_do == "wikis_to_huge_math":
        settings_inst["input"] = settings_inst["wiki"]["xml"]
        # there are too few so each process should take only 1
        settings_inst["parallel"]["chunksize"] = 1


exported_process = _analyse_one_page
exported_commit = _commit_to_index

# enwiki-20130204-pages-articles.xml -> enwiki-20130204-pages-articles.part*.xml
exported_wiki_to_wikis = _wiki_dump_to_many_dumps
# enwiki-20130204-pages-articles.part*.xml -> math-enwiki-20130204-pages-articles.xml.part*.xml.pages
exported_wikis_to_huge_math = _wiki_dump_to_huge_math_pages
# math-enwiki-20130204-pages-articles.xml.part*.xml.pages -> math-all.pages
exported_wiki_maths_to_wiki_math = _wiki_maths_to_wiki_math
# math-all.pages -> output/*/*.html
exported_wiki_math_to_pages = _huge_math_page_to_pages

exported_htmltex = _huge_math_page_texhtml

#
exported_test_queries = _test_queries
exported_process_full = _analyse_full
