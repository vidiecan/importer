# See main file for license.
#
#   Parses wiki dump and returns  page iterator.
#

import os
import re
import sys
import utils

utils.add_to_path( sys, os.path.join(os.path.dirname(__file__), '..') )
from _settings import settings

logger_suspicious = utils.logger("datasets.suspicious")


class pager(object):
    """
   Wiki dump page element abstraction.
  """

    logger = utils.logger('datasets.dump.pager')

    BUFFER_SIZE = 50 * 1024 * 1024
    PAGE_START = u'<page>'
    PAGE_END = u'</page>'

    def __init__( self, file_name_string, delimiter, buffer_size_int=None ):
        pager.logger.info(u"Initializing with [%s], buffer size [%s].", file_name_string, str(buffer_size_int))
        self.file_name = file_name_string
        self.buffer_size = buffer_size_int if buffer_size_int else pager.BUFFER_SIZE
        self.done = 0.0
        self.file_size = 0
        self.delimiter = delimiter

    def _read_more(self, fileobj, minus_offset):
        # end of file?
        if fileobj.tell() == self.file_size:
            raise EOFError()
            # it is the 1st time
        if fileobj.tell() > minus_offset:
            fileobj.seek(-minus_offset, os.SEEK_CUR)
        try:
            buf = fileobj.read(self.buffer_size)
        except:
            raise
        self.done += len(buf)
        return buf

    def _find_start(self, start_pos, buf, fileobj):
        pos = buf.find(pager.PAGE_START, start_pos)
        # if not found so set file pointer to the end -strlen(<page>)
        # - read buffer again
        while pos == -1:
            buf = self._read_more(fileobj, len(pager.PAGE_START))
            pos = buf.find(pager.PAGE_START)
        return pos, buf

    def _get_page(self, start_pos, buf, fileobj):
        pos = buf.find(pager.PAGE_END, start_pos)
        if pos != -1:
            return pos, buf, buf[start_pos:pos + len(pager.PAGE_END)]

        # append the first part and the read until </page>
        page = buf[start_pos:]
        while pos == -1:
            # append from beginning
            buf = self._read_more(fileobj, len(pager.PAGE_END))
            pos = buf.find(pager.PAGE_END)
            page += buf[len(pager.PAGE_END):pos + len(pager.PAGE_END)]
        return pos, buf, page

    #noinspection PyUnusedLocal
    def page_to_template( self, page, template ):
        # get basic info
        #
        pattern = re.compile(
            r'<title>(?P<title>.*?)</title>.*<id>(?P<id>.*?)</id>.*<revision.*<text[^>]*>(?P<text>.*?)</text>',
            re.DOTALL)
        keywords = {
            u"title": None,
            u"id": None,
            u"text": None,
        }
        m = pattern.search(page)
        if not m:
            pager.logger.error(u"Invalid page: could not find elements... %s", page)
            return template
        else:
            assert page.count( u"<title>" ) == 1, u"Matched more pages?"
            for k, v in keywords.iteritems():
                keywords[k] = m.group(k)

        if utils.uni(keywords[u"id"]) in settings["exclude"]["ids"]:
            logger_suspicious.warning(u"Skipping this file (id in excludes)... %s [%s]",
                                 keywords[u"title"], keywords[u"id"])
            return None

        for not_acceptable_start in settings["exclude"]["title_starts"]:
            if keywords[u"title"].startswith(not_acceptable_start):
                logger_suspicious.warning(u"Skipping this file (invalid title start)... %s [%s]",
                                     keywords[u"title"], keywords[u"id"])
                return None

        # clean up text
        # - get math positions (do not clean text inside them)
        # - split text and clean up tokens between math
        #
        from _parser import parser as wikiparser
        text = wikiparser.remove_wiki_tags_outside_math(keywords[u"text"])
        keywords[u"text"] = text

        # get additional info
        #
        category = re.compile(r'\[\[Category:(.+)\]\]').findall(page)
        keywords["category"] = self.delimiter.join(map(lambda x: x.replace(self.delimiter, " "), category))
        keywords["url"] = u"http://en.wikipedia.org/wiki/%s" % keywords[u"title"].replace(u" ", u"_")

        #
        #
        lang_avail = []
        lines = page.strip().split("\n")
        lang_pattern = re.compile(r'\[\[([a-z].+?):.*\]\]')
        for i in range(len(lines) - 1, 0, -1):
            m = lang_pattern.match(lines[i])
            if m:
                lang_avail.append(m.group(1))
            else:
                if lines[i].strip() == "":
                    break
                elif not lines[i].strip().startswith(u"<"):
                    break
        keywords["lang_avail"] = self.delimiter.join([x.replace(self.delimiter, " ") for x in lang_avail])

        #
        #
        keywords["citations_count"] = page.count(u"&lt;ref&gt;")

        refs = u""

        # problems:
        # [[File:Albedo-e hg.svg|thumb|Percentage of diffusely reflected sun light in
        #    relation to various surface conditions of the Earth]]
        #
        #
        def change_to_link( text ):
            """ Very simple text to link changer. """
            text = text.split(u"#")[0]
            if len(text) > 0:
                text = text[0].upper() + text[1:].replace(u" ", "_")
                return text
            return u""

        for cita in re.compile(r'\[\[([^:\]|]+?)\]\]').findall(page):
            refs += '<meta name="refs" content="%s" />\n' % change_to_link(cita)
        for cita in re.compile(r'\[\[([^:|]+?)\]\]').findall(page):
            refs += '<meta name="refs" content="%s" />\n' % change_to_link(cita)
        keywords["refs"] = refs

        page = None  # memory

        # substitute it
        #
        m = None  # memory
        try:
            return utils.subst_str_nonrecursive(template, keywords)
        except MemoryError, e:
            self.logger.exception(u"Memory exception - %s", repr(e))
        return u""

    #noinspection PyArgumentEqualDefault
    def pages(self, template=None):
        buf = u""
        pos = 0
        last_done_percents = 0
        self.file_size = os.path.getsize(self.file_name)

        import codecs

        with codecs.open(self.file_name,
                         encoding='utf-8',
                         mode='rb',
                         errors='replace',
                         buffering=self.buffer_size * 10) as wiki:
        # iterate till no page is EOF
            while True:
                # get start and read to end, put it to page var
                try:
                    pos, buf = self._find_start(pos, buf, wiki)
                    pos, buf, page = self._get_page(pos, buf, wiki)
                except EOFError:
                    return

                # do further processing with page using template
                if template:
                    page = self.page_to_template(page, template)

                # e.g., excludes
                if page is None:
                    continue

                # return one page
                yield page

                # display info if we increase with at least 1%
                act_done_percents = 100 * self.done / self.file_size
                if act_done_percents > last_done_percents + 1:
                    last_done_percents = act_done_percents
                    pager.logger.info(u"Done: %s%%", str(act_done_percents))

    @staticmethod
    def page_to_dict( page_str, *args ):
        from _parser import parser as wikiparser
        parse = wikiparser()
        parse.feed(page_str)
        logger_suspicious.debug( u"parse.feed lasted [%s]", parse.timed )
        ret = parse.dict()
        logger_suspicious.debug( u"parse.dict lasted [%s]", parse.timed )
        return ret
