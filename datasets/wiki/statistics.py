# -*- coding: utf-8 -*-
#!/usr/bin/python
#
#   Parses wiki dump and returns  page iterator.
#
import re
import dump
import utils


class elements( object ):
    logger = utils.logger( 'wiki.statistics.elements' )

    def __init__(self, re_expression):
        elements.logger.info( u"Initializing with re_expression=%s", re_expression )
        self._re = re.compile( re_expression, re.DOTALL )

    def __call__(self, pages):
        size = 0
        for page in pages:
            els = self._re.findall( page )
            print utils.ascii( u"\n".join( els ) )
            size += len( els )
        print u"Total size: %d" % size


if __name__ == "__main__":
    import logging

    logging.basicConfig( level=logging.DEBUG )
    MB = 1024 * 1024
    wikier = dump.pager( r"../output_math/math.pages", 50 * MB )
    elements( u"<title>(.*?)</title>" )( wikier.pages( ) )

print "Finished importing %s" % __file__
