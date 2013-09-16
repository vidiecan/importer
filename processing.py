# -*- coding: utf-8 -*-
"""
  Multiprocessing stub.
"""
#
# pylint: disable=W0142,R0912,R0914


from __future__ import with_statement
import codecs
import ctypes
import glob
import multiprocessing
from multiprocessing.pool import ThreadPool
import os

import utils

logger = utils.logger('processing')

from datasets import init_pool


def process( env_dict, ftor_to_call, final_ftor ):
    """
    Index function wrapper around analyse_one_page and commit_to_index.

    It either calls them in parallel or sequentially.
  """

    # global exit signaller
    exit_ = multiprocessing.Array(ctypes.c_int, 1, lock=False)
    exit_[0] = 0

    logger.info(u"Reading input from [%s]", env_dict["input"])

    done_set = set()
    if env_dict["indexer"].get( "continue", False ):
        fname = env_dict["indexer"]["continue"]
        if os.path.exists(fname):
            done_set = set( [ utils.uni(x).strip().lower()
                              for x in codecs.open( fname, encoding="utf-8",
                                                    mode="r", errors="ignore" ).readlines() ] )

    def iparameters():
        """ Get iterable params. """
        i = 0
        for file_ in glob.iglob(env_dict["input"]):
            file_ = os.path.abspath(file_)
            if file_.lower() in done_set:
                continue
            no_go = False
            file_basename = os.path.basename(file_)
            for not_acceptable_start in env_dict["exclude"]["file_starts"]:
                if file_basename.startswith(not_acceptable_start):
                    logger.warning(u"Skipping this file (invalid title start) [%s]", file_basename)
                    no_go = True
            if no_go:
                continue
            i += 1
            yield ( env_dict, i, file_ )

    # create pool of slaves if specified
    #
    if env_dict["parallel"]["enabled"] and not env_dict.debug:

        # parallel version
        # - threaded
        # - processed
        #
        max_parallel = env_dict["parallel"]["max"]
        kwargs = {}
        if env_dict["parallel"]["threads"]:
            logger.info("Using threading pool with [%d] max concurrent threads.", max_parallel)
            Pool = ThreadPool
        else:
            Pool = multiprocessing.Pool
            kwargs = {}
            if "maxtasksperchild" in env_dict["parallel"]:
                kwargs["maxtasksperchild"] = env_dict["parallel"]["maxtasksperchild"]
            logger.info("Using process pool with [%d] max concurrent processes, chunk size [%s], [%s].",
                        max_parallel, env_dict["parallel"]["chunksize"], repr(kwargs))

        slaves = Pool(processes=max_parallel,
                      initializer=init_pool,
                      initargs=(exit_,),
                      **kwargs)

        # loop through all files and
        it = slaves.imap(ftor_to_call, iparameters(), chunksize=env_dict["parallel"]["chunksize"])
        slaves.close()
        for _ in it:
            if exit_[0]:
                break
            utils.print_after.step()
        slaves.join()

    # not parallel version
    else:
        logger.info("Executing non parallel version [%s]", "debug=True" if env_dict.debug else "parallel.enabled=False")
        init_pool(exit_)
        for (env, pos, file_) in iparameters():
            ftor_to_call((env_dict, pos, file_))
            utils.print_after.step()
            if pos >= env.count:
                break

    # final break
    #
    if not final_ftor is None:
        final_ftor(env_dict)
