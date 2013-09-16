# -*- coding: utf-8 -*-
# pylint: disable=W0621,R0914,C0111,W0702,R0912

"""
  Egomath importer framework

  @author: jm
  @date: 2011
  @version: 1.2
"""

from __future__ import with_statement
import sys
import os
import time

from settings import settings
import utils

utils.initialize_logging(settings["logger_config"])

logger = utils.logger('importer')
import processing


#================
# helpers
#================

def check_system():
    """
        Simple sanity check.
    """
    if not utils.ensure_keys(["name",
                              "logger_config",
                              "mathml"], settings):
        utils.exit(utils.ENVIRONMENT_ENTRY_NOT_FOUND, "")

    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)


def _help(_):
    """ Logs help message """
    logger.warning("""\n%s\nSupported commands:
  --help      prints this message
  --dataset   select dataset (if alone, prints available commands)
    --operation select operation, if empty shows valid operation
    --count     number of documents to process (disables parallelism)
    --parallel  make the operation parallel, make sure that the operation
                implementation supports it! (on for default process operation)
  --verbose   prints even more information
  --debug     debug turned on

You should specify the dataset you would like to process e.g.,
python main.py --dataset=wiki
""", settings["name"]
    )


#noinspection PyBroadException
def parse_command_line( env ):
    """
        Command line.
    """
    import getopt

    opts = None
    try:
        options = ["help",
                   "dataset=",
                   "operation=",
                   "count=",
                   "verbose",
                   "debug",
                   "production",
                   "input=",
                   "parallel"]
        input_options = sys.argv[1:]
        opts, _1 = getopt.getopt(input_options, "", options)
    except getopt.GetoptError, e:
        _help(None)
        utils.exit(utils.ARGS_PARSE_ERROR, str(e))

    what_to_do = None
    dataset = None
    production = False
    input_from_cmd = None
    parallel_process = False
    for option, param in opts:
        # help
        #
        if option == "--help":
            return _help

        if option == "--debug":
            env.debug = True

        if option == "--verbose":
            env.verbose = 1

        if option == "--production":
            production = True

        elif option == "--count":
            env.count = int(param)
            env["parallel"]["enabled"] = False

        # dataset
        #
        elif option == "--parallel":
            parallel_process = True

        # operation
        #
        elif option == "--operation":
            what_to_do = param

        elif option == "--dataset":
            dataset = param
            env["dataset"] = dataset

        elif option == "--input":
            input_from_cmd = param

    if dataset is None:
        return _help

    # we have dataset so load it
    #
    module = None
    fp = None
    try:
        import imp
        fp, pathname, description = imp.find_module(dataset, ["./datasets"])
        module = imp.load_module(dataset, fp, pathname, description)
    finally:
        # Since we may exit via an exception, close fp explicitly.
        if fp:
            fp.close()

    # get operation
    #

    def _get_exported( fncs_list ):
        exported = []
        prefix = env["datasets"]["export_prefix"]
        for m in fncs_list:
            if utils.uni(m).startswith(prefix):
                exported.append(utils.uni(m)[len(prefix):])
        return exported

    def _print_with_options( fncs ):
        fncs_str_arr = _get_exported(fncs)
        log_msg = u"""\n\nPossible options for [%s] dataset are:
\t%s\n\nSelect one of the operations above e.g.,
python main.py --dataset=%s --operation=%s\n"""
        logger.warning(log_msg, dataset, "\n\t".join(fncs_str_arr), dataset, fncs_str_arr[0])

    # print help
    #
    if what_to_do is None:
        return lambda x: _print_with_options(dir(module))

    # import settings
    #
    if hasattr(module, 'update_settings'):
        logger.info(u"Updating settings from module specific fnc.")
        module.update_settings(what_to_do, env)

    # production
    #
    if production:
        env["input"] = env.get_value("input_production", env["input"])
        env["parallel"]["enabled"] = env["parallel"].get_value("enabled_production", env["parallel"]["enabled"])

    if input_from_cmd:
        env["input"] = env["input_base"] + input_from_cmd

    # special case function wrappers
    #
    exported_name = '%s%s' % (env["datasets"]["export_prefix"], what_to_do)

    # call default
    if what_to_do == env["datasets"]["default_method"]:
        try:
            exported_process = getattr(module, exported_name)
            if not hasattr(module, "exported_commit"):
                raise
            #assert getattr( module, exported_name ), "export_process must be present in module"
            what_to_do = lambda x: processing.process(x, exported_process, module.exported_commit)
        except:
            logger.error(u"Invalid operation name [%s]", exported_name)
            return lambda x: _print_with_options(dir(module))

    # call in parallel or call only fnc
    else:
        try:
            exported_fnc = getattr(module, exported_name)
            if parallel_process:
                what_to_do = lambda x: processing.process(x, exported_fnc, None)
            else:
                what_to_do = getattr(module, exported_name)
        except:
            logger.error(u"Invalid operation name [%s]", exported_name)
            return lambda x: _print_with_options(dir(module))

    # what to do but really?
    return what_to_do


#================
# main
#================

if __name__ == "__main__":
    check_system()

    lasted = time.time()
    env = utils.environment()
    env.update(settings)

    try:
        what_to_do = parse_command_line(env)
        what_to_do(env)
    except SystemExit:
        raise
    except Exception, e:
        lasted = time.time() - lasted
        logger.exception("An exception occurred, ouch:\n%s", str(e))
        utils.log_stacktrace_to_file(settings["exception_file"], e)

    finally:
        tt = time.time() - lasted
        logger.warn("Stopping after [%f] secs (%f minutes).", tt, tt / 60.)
