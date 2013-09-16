# -*- coding: utf-8 -*-
# See main file for license.
"""
  Settings module.
"""
import re

settings = {

    "backend_host": "http://localhost:8080/solr-ego-wiki/",

    #"input"       : u"output/wiki/pages/N/Near-field*",
    #"input"       : u"output/wiki/pages/P/Pythagoras.html",
    #"input": u"output/wiki/pages/E/E*mathematical*.html",
    #"input": u"output/wiki/pages/C/Cubic_function.html",
    "input": u"output/wiki/pages/*/*.html",
    "input_production": u"output/wiki/pages/*/*.html",

    "logs_file_runs": "output/log_runs.txt",


    # indexer instance
    #
    "indexer": {
        "id_str": "id",
        #"autocommit" : True,
        #"continue": "output/wiki/done.set",
        "solr_home": ur"g:\ego\work\backend\project\solr_home_wiki2\egomath_wiki\data\index",
    },

    "exclude": {

        "ids": (
        # "22955503",
        # "12794802",
        # # conversion bug  #130
        # "9516940",
        # "20696",
        # "5485345",
        # "9517063",
        ),

        "title_starts": (
            "File:",
            "Template:",
            "Wikipedia:Articles for deletion",
            "Wikipedia:",
            "Help:",
        ),

        "file_starts": (
            "Wikipedia{colon}",
        ),

    },


    "wiki": {

        #
        "collect_stats": True,
        #
        "dataset": u"wiki-2013",
        # wiki input xml file
        #"big_xml"  : u"g:/ego/dataset/wiki/enwiki-latest-pages-articles1.xml",
        "big_xml": u"h:/enwiki/enwiki-20130204-pages-articles.xml",
        "xml": u"h:/enwiki/enwiki-20130204-pages-articles.xml.part*.xml",


        "wikis_file_limit": 4000 * 1024 * 1024,
        "wikis_file_buffer": 200 * 1024 * 1024,

        # output for redirects
        "redirect_output": u".htaccess",
        # output directory for separate pages
        # - you want to change indexer["input"] probably too
        "pages_output": u"output/wiki/pages",

        # wiki output file full of math pages
        #"xml_math_output"  : u"output_math/math.pages",
        "xml_math_output": u"output/wiki/math/math-%s.pages",
        "xml_math_output_big": u"output/wiki/math/math-all.pages",
        "xml_math_output_test": u"output/wiki/math/math.test.pages",
    },


    "pager": {
        "buffer": 5 * 1024 * 1024,  # 100 MB
        "identify_by": u"&lt;/math",
        #"re_math": re.compile( r"&lt;math(?:&gt;|[^/]*?&gt;)(.*?)&lt;/math\s*&gt;", re.DOTALL | re.IGNORECASE ),
        # v2.1 - <math.h>
        "re_math": re.compile( r"&lt;math(?:&gt;|\s+[^/]*?&gt;)(.*?)&lt;/\s*math\s*&gt;", re.DOTALL | re.IGNORECASE ),
        # there was a problem when subst. abstracts - {{}}
        "re_maths": (
            re.compile( r"&lt;math(?:&gt;|\s+[^/]*?&gt;)(.*?)&lt;/\s*math\s*&gt;", re.DOTALL | re.IGNORECASE ),
            re.compile( r"eegomath(.*?)egomathh", re.DOTALL | re.IGNORECASE ),
        ),


        "re_title": u"<title>(.*?)</title>",
        "overwrite": True,
        "delimiter": u";",
        "math_sep": ( u"eegomath", u"egomathh" ),
        "tex_start": u"Tex:",
        "wiki_mathml_tags": (u"<m:math", u"</m:math>"),
        "wiki_mathml_tags_v2": (u"<math", u"</math>"),
        "wiki_math_tags": (u"&lt;math&gt;", u"&lt;/math&gt;"),

        "abstract": {
            "from": 1200,
            "to": 1300,
            "delimiter": ( ".", "!", "?", "\n", " " ),
        }
    },

    "redirect": {
        "directory": "wikipedia",
    },


    "metadata": {
        # known_keys but also conversion between extracted values and well used names
        #
        "known_keys": {
            u"text": None,
            u"id": None,
            u"title": None,
            u"math": None,
            u"url": None,
            u"category": None,

            u"abstract": None,

            u"citations": None,  # still todo
            u"citations_count": None,  # {cite}
            u"refs_count": None,  # [[
            u"refs": None,  # [[

            u"math_count": None,

            u"lang_avail": None,  # [[en:...
        },

        "boosts": {
            "math": "2.5",
        },

        "primary_key": "id",
    },

    "test_queries": {

        "default_params": u"""&start=0&mqo=10&fl=id,title&wt=json&indent=true""",

        "queries": ur"""
                    {!egonear df="math" apart=5}"egosem 0 k noteq","egomathh"
                    math:([2]a*(b+c))
                    math:([1]e^{i\pi}=-1)
                    {!egonear df="math" apart=5}"egosem 0 k noteq","egomathh"
                    math:([1]\pi=c/d)
                    math:([1]e=\lim_{n\to\infty}(1+1/n)^n)
                    math:([1]\frac{d}{dx}e^x)
                    math:([1]\sum_{n=0}^{\infty}\frac{f^{n}(a)}{n!}(x-a)^n)
                    math:([1]Ax=\lambda x)
                    math:([1]z_{n+1} = z_n^2 + c)
                    math:([1]|x+y| \leq |x|+|y|)
                    math:([1]E=m c^2)
                    math:([1]F=G\frac{m_1 m_2}{egovar^2})
                    math:([1]cos^2(x) + sin^2(x))
                    math:([1]id + id)
                    """,

        "queries_qa": ur"""
                    {!egonear df="math" apart=5}"egosem 0 k noteq","egomathh"
                    math:([1]e^{i\pi}=-1)
                    math:([1]\pi=c/d)
                    math:([1]e=\lim_{n\to\infty}(1+1/n)^n)
                    math:([1]\frac{d}{dx}e^x)
                    math:([1]\sum_{n=0}^{\infty}\frac{f^{n}(a)}{n!}(x-a)^n)
                    math:([1]Ax=\lambda x)
                    math:([1]z_{n+1} = z_n^2 + c)
                    math:([1]|x+y| \leq |x|+|y|)
                    math:([1]E=m c^2)
                    math:([1]F=G\frac{m_1 m_2}{egovar^2})
                    math:([1]cos^2(x) + sin^2(x))
                    math:([1]id + id)
                    math:([1]i \hbar \frac{\partial}{\partial t}\Psi = \hat H \Psi)
                    math:([1]\int_0^1 f)
                    math:([1]\sum_{n=1}^{\infty} (1/n))
                    math:([1]egonum^2+egonum^2=egonum^2)
                    math:([1]V-E + F = 2)
                    math:([1]5^2 = 3^2 + 4^2)
                    math:([1]\frac{n!}{2*\pi * i})
                    math:([1]1-1/3+1/5-1/7)
                    math:([1]dr_t=a(b-r_t) dt+\sigma dW_t)
                    math:([204]dr_t = a(b-r_t) dt + \sigma dW_t)
                    math:([1]cos \phi + i * sin \phi = e^{i*\phi})
                    math:([7]cos \phi + i * sin \phi = e^{i*\phi})
                    math:([1]\sum_{n=0}^{\infty} \frac{a^n}{n!})
                    math:([2]\sum_{n=0}^{\infty} \frac{a^n}{n!})
                    math:([1]a*(b+c))
                    math:([2]a*(b+c))
                    """,

        "params": (
            u"&mpayload=true",
            u"&mpayload=false",
            u"&facet=true&facet.sort=count&facet.mincount=1&facet.field={!key=category}category&facet.range={!key=citations_count}citations_count&facet.range={!key=refs_count}refs_count&facet.range={!key=math_count}math_count&f.citations_count.facet.range.start=0&f.citations_count.facet.range.end=100&f.citations_count.facet.range.gap=10&f.citations_count.facet.range.other=after&f.citations_count.facet.range.include=lower&f.refs_count.facet.range.start=0&f.refs_count.facet.range.end=100&f.refs_count.facet.range.gap=20&f.refs_count.facet.range.other=after&f.refs_count.facet.range.include=lower&f.math_count.facet.range.start=0&f.math_count.facet.range.end=100&f.math_count.facet.range.gap=10&f.math_count.facet.range.other=after&f.math_count.facet.range.include=lower",
            u"&hl=true&hl.fl=math&hl.snippets=1&hl.fragsize=400&hl.requireFieldMatch=true&hl.maxAnalyzedChars=5120000&hl.simple.pre=%3Cstrong%20class%3D%22highlight%22%3E&hl.simple.post=%3C%2Fstrong%3E&hl.useFastVectorHighlighter=false&hl.usePhraseHighlighter=true&hl.highlightMultiTerm=true",
            u"&m_only_equal=true",
            u"&hl=true&hl.fl=math&hl.snippets=1&hl.fragsize=400&hl.requireFieldMatch=true&hl.maxAnalyzedChars=5120000&hl.simple.pre=%3Cstrong%20class%3D%22highlight%22%3E&hl.simple.post=%3C%2Fstrong%3E&hl.useFastVectorHighlighter=false&hl.usePhraseHighlighter=true&hl.highlightMultiTerm=true&m_only_equal=true",
        ),
    },

}
