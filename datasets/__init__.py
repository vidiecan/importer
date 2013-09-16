# -*- coding: utf-8 -*-
"""
  Dataset module.

  Every module inside datasets must export (at least) two functions

    def export_process( (env_dict, pos, file_str) ):
      pass

    def export_commit( env_dict ):
      pass

  where env_dict is a python dict-like structure used to store settings.
  The main settings are inside the settings directory, each module can change these
  if it implements the update_settings method with this signature

  def update_settings( settings_inst ):
    pass

"""

import os
import codecs
import utils
import time
_logger_suspicious = utils.logger("datasets.suspicious")
shared_variable = None


def init_pool( share ):
    """ Helper function to multiprocessing. """
    global shared_variable
    shared_variable = share


#noinspection PyUnresolvedReferences
def analyse_one_page_generic( env, pos, file_str, logger, page_to_dict, add_to_index ):
    """

    """
    global shared_variable
    try:
        all_start = time.time()
        if pos > env.count or shared_variable[0] > 0:
            return

        if os.path.exists( env["parallel"]["wait_file"] ) or \
                os.path.exists( env["parallel"]["wait_file"] + "_" + env.get_value("dataset", "") ):
            logger.warning( u"Waiting because wait file is here..." )
            while os.path.exists( env["parallel"]["wait_file"] ):
                time.sleep( env["parallel"]["wait_sleep"] )

        logger.warning( u"Processing [%s][%s]", pos, file_str )

        # which command to use for conversion
        with codecs.open(file_str, mode="r", encoding="utf-8") as fin:
            html = fin.read()

        if env.verbose:
            logger.warning(u"Adding [%s] [%s]", pos, file_str)
        s = time.time()
        meta_dict = page_to_dict(html, env, pos, file_str)
        _logger_suspicious.debug( u"page_to_dict lasted [%s]", time.time() - s )
        del html

        if not u"id" in meta_dict:
            logger.error(u"Invalid page: could not find element [id]... %s", file_str)
            return

        if env.verbose > 0:
            dict_str = u""
            for k in meta_dict.keys():
                if not k.startswith(u"text"):
                    dict_str += u"%s: %s\n" % (k, meta_dict[k])
            logger.info(dict_str)

        if len(meta_dict.get("math", "")) == 0:
            logger.warning(u"No math inside this page! [%s][%s]", meta_dict["id"], meta_dict["title"])
            return
        num_formulas = len(meta_dict["math"])

        # index only
        if len( env.get_value( "index_only_fields", [] ) ) > 0:
            only_fields = env["index_only_fields"]
            for k in meta_dict.keys():
                if not k in only_fields:
                    meta_dict[k] = None
        # index except only
        if len( env.get_value( "not_index_only_fields", [] ) ) > 0:
            not_fields = env["not_index_only_fields"]
            for k in not_fields:
                meta_dict[k] = None

        # index it
        s = time.time()
        added = add_to_index(env, meta_dict, file_str, logger)
        _logger_suspicious.debug( u"Adding lasted [%s]", time.time() - s )
        del meta_dict

        if added and env["indexer"].get( "continue", False ):
            fname = env["indexer"]["continue"]
            s = time.time()
            with codecs.open( fname, encoding="utf-8", mode="a+" ) as fout:
                fout.write( u"%s\n" % file_str )
            _logger_suspicious.debug( u"Continue writing lasted [%s]", time.time() - s )

        took = time.time() - all_start
        logger.warning( u"Processed [%s][formulas:%s][%s][lasted:%s]",
                        pos, num_formulas, os.path.basename(file_str), took )
        return

    except SystemExit, e:
        logger.exception(u"Thread SystemExit exception in %s:" % file_str)
        utils.log_stacktrace_to_file(env["exception_file"], e)
        raise
    except KeyboardInterrupt:
        logger.critical(u"Got keyboard exception - exiting!")
        shared_variable[0] = 1
    except Exception, e:
        logger.exception(u"Thread exception in %s:" % file_str)
        utils.log_stacktrace_to_file(env["exception_file"], e)
        if env.debug:
            raise
