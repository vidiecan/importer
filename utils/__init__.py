# -*- coding: utf-8 -*-
"""
  Utility file

  @author: jm
  @version: 1.3
   - added new functions

"""
# See main file for license.
#
# pylint: disable=W0622,E0102,E1101,W0702,W0141,C0111,R0924,R0912,W0110,R0913,W0621,C0111,C0302,W0402,W0404,W0108,R0902,R0914

from __future__ import with_statement
import os
import sys
import copy
import re
import glob
from string import Template
import traceback
import urllib
import codecs
import logging
import urllib2

import settings

if settings.settings.get("production", False):
    logging.raiseExceptions = 0

from time import strftime
import time
from datetime import timedelta
from datetime import date


#=====================================
# python version
#=====================================

def ensure_python(version=None):
    """ Ensure that we use appropriate python version. """
    SUPPORTED_PYTHON = version if version else ( 2, 6 )
    if sys.version_info >= SUPPORTED_PYTHON:
        return
    print "Error: your python version is not supported: %s" % repr(sys.version_info)
    print "Supported version >=: %s, please visit http://python.org/download/releases/ and install it." % repr(
        SUPPORTED_PYTHON)
    sys.exit()

# ensure we have at least version utils supports
ensure_python()


#=====================================
# logger
#=====================================

def initialize_logging(logger_config_file=None, force=False):
    """
    Ensure proper logging levels, formats and also ensures
    that sys.stdout will be also logged.

    If force is True, the handlers will be added even if there are
    more some 0.
  """
    import logging

    if logger_config_file is None:
        root_logger = logging.getLogger()

        # do not add more handlers if we already have some
        if not force and len(root_logger.handlers) > 0:
            return

        if 'LOGGING_LEVEL' in settings.settings and \
                'LOGGING_FORMAT' in settings.settings:
            root_logger.setLevel(settings.settings['LOGGING_LEVEL'])
            console = logging.StreamHandler()
            console.setLevel(settings.settings['LOGGING_LEVEL'])
            console.setFormatter(logging.Formatter(settings.settings['LOGGING_FORMAT']))
            root_logger.addHandler(console)
        else:
            root_logger.setLevel(logging.DEBUG)
            console = logging.StreamHandler()
            console.setLevel(logging.DEBUG)
            root_logger.addHandler(console)
    else:
        import logging.config

        if not os.path.exists(logger_config_file):
            logging.basicConfig(level=logging.WARNING)
            logging.warning("Could not find logger config - using default configuration...")
        else:
            logging.config.fileConfig(logger_config_file)
        root_logger = logging.getLogger()

    class writer(object):
        """ Fake class for sys.stdout  """
        # pylint: disable=C0111
        def __init__(self, logger_logger):
            self.logger = logger_logger

        def write(self, text):
            if text.strip() == "":
                return
                #sys.__stdout__.write( text )
            self.logger.warning(text.strip('\n'))

        def flush(self):
            pass

    sys.stdout = writer(root_logger)


def logger(logger_string):
    """
    Get default logger and add NullHandler for it. Be careful, to use this in your application
    without additional code required use `core.` prefix for all your loggers.

    .. attribute:: logger_string

      String to your library code.
  """
    return logging.getLogger(logger_string)


_logger = logger('utils')
_logger_dbg = logger('utils.debug')


def logger_add_file_handler(filename_str, logger_logger=None, not_more_than=-1):
    """ Adding logging to file.  """
    import logging.handlers

    if not logger_logger:
        logger_logger = logging.getLogger()
    logger_filehandlers = [x for x in logger_logger.handlers
                           if isinstance(x, logging.handlers.WatchedFileHandler)]
    if not_more_than == -1 or not_more_than >= len(logger_filehandlers):
        file_logger = logging.handlers.WatchedFileHandler(filename_str)
        file_logger.setLevel(settings.settings['LOGGING_LEVEL'])
        file_logger.setFormatter(logging.Formatter(settings.settings['LOGGING_FORMAT_FILE']))
        logger_logger.addHandler(file_logger)
    else:
        _logger.warning("Disabled adding filehandler logger to logger [%s]", filename_str)


def log_exception(logger, msg_string, e_exception):
    """
    Log exceptions in default way.

    .. attribute:: logger
    .. attribute:: msg_string
    .. attribute:: e_exception
  """
    logger.exception("Exception demurs: %s \n%s\n%s", msg_string, repr(e_exception), "=" * 40)
    logger.warning("=" * 40)


def log_import(file_string, start_to_import_bool=True):
    """ Log imports for debugging. """
    file_string, file_ = os.path.split(file_string)
    for _ in range(2):
        file_string, file_tmp = os.path.split(file_string)
        file_ = "%s/%s" % (file_tmp, file_)
    if start_to_import_bool:
        _logger_dbg.log(1, 'import %s', file_)
    else:
        _logger_dbg.log(1, '+----- %s', file_)


def log_to_file(filename_str, lines_list):
    """
    Append lines to a file.
  """
    fout = None
    try:
        fout = codecs.open(filename_str, "a+", encoding="utf-8", errors="replace")
        fout.writelines(lines_list)
    except IOError, e:
        log_exception(_logger, "Could not write to file [%s]" % filename_str, e)

    if fout:
        fout.close()


def log_stacktrace_to_file(filename_str, exception=None):
    """
    Log stacktrace to a file.
  """
    with codecs.open(filename_str, mode="a+", encoding="utf-8", errors="replace") as exception_file:
        exception_file.write(10 * u"=")
        exception_file.write(now())
        exception_file.write(10 * u"=" + "\n")
        try:
            if exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                exception_file.write(u"".join([ascii(x) for x in traceback.format_stack(limit=5)]) + u"\n----\n")
                exception_file.write(u"".join([ascii(x) for x in traceback.format_tb(exc_traceback)]) + u"\n----\n")
                exception_file.write(ascii(exc_type) + u"\n")
                exception_file.write(ascii(exc_value) + u"\n")
            else:
                exception_file.write(u"".join([ascii(x) for x in traceback.format_stack()]) + u"\n----\n")
        except Exception, e:
            # we should be able to use this as the errors from above are sane in ascii
            exception_file.write(u"Error while printing stack..[%s]\n", ascii(repr(e)))
        exception_file.write(25 * u"=" + "\n")


#noinspection PyUnresolvedReferences
def log_not_more(logger_fnc, text, max_output_int, where_to_find_details_str):
    """
    Output to logger function text up to max_output_int lines.
  """
    if text.count("\n") > max_output_int:
        text = [x.strip() for x in text.split("\n", max_output_int)]
        logger_fnc("\n".join(text[:max_output_int]))
        logger_fnc(where_to_find_details_str)
    else:
        logger_fnc(text)


from logging.handlers import RotatingFileHandler
import multiprocessing
import threading


# noinspection PyBroadException
class MultiProcessingLog(logging.Handler):
    """
    Synchronised parallel multi processing log.
  """

    def __init__(self, name, mode, maxsize, rotate, encoding="utf-8", delay=0):
        logging.Handler.__init__(self)

        self._handler = RotatingFileHandler(name, mode, maxsize, rotate, encoding, delay)
        self.queue = multiprocessing.Queue(-1)

        t = threading.Thread(target=self.receive)
        t.daemon = True
        t.start()

    def setFormatter(self, fmt):
        """ Default setFormatter impl. """
        logging.Handler.setFormatter(self, fmt)
        self._handler.setFormatter(fmt)

    def receive(self):
        """ Receives one record to log. """
        while True:
            try:
                record = self.queue.get()
                if self._handler:
                    self._handler.emit(record)
            except (KeyboardInterrupt, SystemExit):
                raise
            except EOFError:
                break
            except:
                traceback.print_exc(file=sys.stderr)

    def send(self, s):
        """ Puts to nowait queue. """
        self.queue.put_nowait(s)

    def _format_record(self, record):
        # ensure that exc_info and args
        # have been stringified.  Removes any chance of
        # unpickleable things inside and possibly reduces
        # message size sent over the pipe
        if record.args:
            record.msg = record.msg % record.args
            record.args = None
        if record.exc_info:
            # noinspection PyUnusedLocal
            dummy = self.format(record)
            record.exc_info = None

        return record

    def emit(self, record):
        try:
            s = self._format_record(record)
            self.send(s)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def close(self):
        self._handler.close()
        self._handler = None
        logging.Handler.close(self)

#=====================================
# return / error codes
#=====================================

SUCCESS = 0
FAIL = 1
EXCEPTION = -1

# good
OK = 0
# bad
BAD = 10
WRONG_SPEC_MODULE = BAD + 1
NO_SPEC_MODULE = BAD + 2
CANT_RUN = BAD + 3
ARGS_PARSE_ERROR = BAD + 4
TASK_FAILED = BAD + 5
INVALID_RUN_NAME = BAD + 6
TASKS_FAILED = BAD + 7
REQUIRED_DIRECTORY_MISSING = BAD + 8
NOT_IMPLEMENTED_YET = BAD + 9

# very bad
VERY_BAD = 100
UNEXPECTED_EXCEPTION = VERY_BAD + 1
SPEC_TYPE_NOT_FOUND = VERY_BAD + 2
ARGS_NOT_ENOUGH = VERY_BAD + 3
TASK_NOT_FOUND = VERY_BAD + 4
TARGET_NOT_FOUND = VERY_BAD + 5
CANT_CHANGE_DIRECTORY = VERY_BAD + 6
CANT_RUN_NO_EXECUTE = VERY_BAD + 7
ENVIRONMENT_ENTRY_NOT_FOUND = VERY_BAD + 8

NOT_SUFFICIENT_PERMISSIONS = VERY_BAD + 10
OPERATION_FAILED = VERY_BAD + 11
SHELF_ERROR = VERY_BAD + 12
REQUIRED_TASK = VERY_BAD + 13
INVALID_IMPORT = VERY_BAD + 14

__error_info = {
    OK: "Automation system finished without any errors.",
    WRONG_SPEC_MODULE: "Wrong specification module - please specify a project.",
    NO_SPEC_MODULE: "No specification module provided.",
    CANT_RUN: "Module is not a standalone script.",
    ARGS_PARSE_ERROR: "Error encountered during command line arguments parsing.",
    TASK_FAILED: "Task failed.",
    INVALID_RUN_NAME: "Can not find specified name of a run.",
    TASKS_FAILED: "One or more tasks failed.",
    REQUIRED_DIRECTORY_MISSING: "Required directory missing.",
    NOT_IMPLEMENTED_YET: "Not implemented yet.",

    UNEXPECTED_EXCEPTION: "Caught unexpected exception.",
    SPEC_TYPE_NOT_FOUND: "Wrong specification type.",
    ARGS_NOT_ENOUGH: "Not enough parameters.",
    TASK_NOT_FOUND: "Task not found.",
    TARGET_NOT_FOUND: "Target not found.",
    CANT_CHANGE_DIRECTORY: "Can not change current directory.",
    CANT_RUN_NO_EXECUTE: "Execute method not provided in the task.",
    ENVIRONMENT_ENTRY_NOT_FOUND: "Environment entry not found.",
    NOT_SUFFICIENT_PERMISSIONS: "Your permissions do not allow performing requested operation.",
    OPERATION_FAILED: "Requested operation failed.",
    SHELF_ERROR: "Shelf database error.",
    REQUIRED_TASK: "Element must be a task.",
    INVALID_IMPORT: "Invalid import module.",
}


# noinspection PyShadowingBuiltins
def exit(errno, additional=None):
    """
    Print error message associated with error code and stop execution.
  """
    MAX_NUM_CHARS = 58
    if errno == OK:
        _logger.critical(MAX_NUM_CHARS * "-")
        _logger.info(__error_info[errno])
    else:
        if not errno in ( ARGS_PARSE_ERROR, ARGS_NOT_ENOUGH, ):
            log_stacktrace_to_file(settings.settings["exception_file"])
        _logger.critical(MAX_NUM_CHARS * "-")
        _logger.critical("Reason for exit: '%s'", __error_info[errno])
        if additional:
            _logger.critical("Additional info: %s", additional)
        _logger.critical(MAX_NUM_CHARS * "-")
        _logger.critical('Automation system finished WITH ERRORS (%d)!', errno)

    sys.exit(errno)


#=====================================
# import
#=====================================

def add_to_path(sys_module, dir_str, position=0):
    """ Check if dir_str exists in sys_module.path and insert it to position. """
    assert dir_str
    dir_str = os.path.abspath(dir_str)
    for path in sys_module.path:
        # found path, do not add
        if dir_str == path:
            return
    sys_module.path.insert(position, dir_str)


#=====================================
# I/O related
#=====================================

def read(filename_str, encoding="utf-8"):
    """
    Read lines from a file. Strips new lines and spaces
  """
    try:
        with codecs.open(filename_str, mode="rb", encoding=encoding, errors="replace") as fin:
            return fin.read()
    except IOError, e:
        log_exception(_logger, "Could not read [%s]" % filename_str, repr(e))
        return None


def readlines(filename_str, encoding="utf-8"):
    """
    Read lines from a file. Strips new lines and spaces
  """
    try:
        with codecs.open(filename_str, mode="rb", encoding=encoding, errors="replace") as fin:
            return [uni(x) for x in map(lambda x: x.strip(u"\n\t \r"), fin.readlines()) if x != u""]
    except IOError, e:
        log_exception(_logger, "Could not read [%s]" % filename_str, repr(e))
        return None


# noinspection PyBroadException
def uni(str_str, encoding="utf-8"):
    """
    Try to get unicode without errors
  """
    if isinstance(str_str, unicode):
        return str_str
    try:
        return unicode(str_str, encoding=encoding, errors='ignore')
    except (UnicodeError, TypeError):
        pass
    try:
        return unicode(str(str_str), encoding=encoding, errors='ignore')
    except UnicodeError:
        pass
    try:
        return str_str.decode(encoding=encoding, errors="ignore")
    except Exception:
        pass
    _logger.critical("Could not convert [something] to unicode")
    return u""


# noinspection PyBroadException
def ascii(str_, encoding_string="utf-8", errors='ignore'):
    """ Return ascii representation of unicode """
    import unicodedata

    try:
        str_ = uni(str_, encoding_string)
        str_ = unicodedata.normalize('NFKD', str_).encode('ascii', errors)
        str_ = str_.replace("?", "")
    except:
        pass
    try:
        return str(str_)
    except:
        pass
    return str_


#=====================================
# dict related
#=====================================

def rustleup(obj, data=None):
    """
    Magic function to build objects from other types
    and call its constructor
  """
    if isinstance(obj, dict):
        if data:
            return obj["class"](data)
        else:
            return obj["class"]()
    elif type(obj).__name__.startswith('classobj') or isinstance(obj, type):
        if data:
            return obj(data)
        else:
            return obj()
    else:
        return obj


def inherit(base, child):
    """
    Intuitive dict inheritance with deepcopy.

    .. attribute:: base (dict)

    Object which will be updated.

    .. attribute:: child (dict)

    New values.
  """
    for o in [base, child]:
        if not isinstance(o, dict) and _str(o) != 'environment':
            _logger.warning("Inheriting from non dictionary (or not task_environment)")
    new = copy.deepcopy(base)
    new.update(child)
    return new


def subst_str(str_, *kwargs):
    """
    Substitute template strings recursively (template can contain another template).
  """
    for env in kwargs:
        old = ""
        while old != str_:
            old = str_
            str_ = Template(str_).safe_substitute(env)
    return str_


def subst_dict(d, *kwargs):
    """
    Substitute template strings in dictionary recursively.
  """
    for k, v in d.iteritems():
        if isinstance(v, (str, unicode)):
            d[k] = subst_str(v, *kwargs)
    return d


def subst_str_nonrecursive(str_, *kwargs):
    """ Substitute parameters in string but only once. """
    return Template(str_).safe_substitute(*kwargs)


def extend_env(current_environment, data):
    """
    Get extended environment with set of additional entries.  Subtasks may need to work in context of their parent.

    .. attribute:: current_environment

      Environment

    .. attribute:: data (dict) 

      Data to extend.
  """
    return inherit(current_environment, data)


def validate_dict(dict_, req_keys, instance="unknown"):
    """
    Check whether dict has all required keys
  """
    ret = True
    for req in ensure_iterable(req_keys):
        if isinstance(req, basestring):
            if not req in dict_:
                _logger.warning("Missing [%s] key in dict in %s", req, _str(instance))
                ret = False
        else:  # assume iterable
            found = False
            for req_one in ensure_iterable(req):
                if req_one in dict_:
                    found = True
                    break
            if not found:
                _logger.warning(u"Missing one of [%s] key in dict in %s", uni(req), _str(instance))
                ret = False
    return ret


# noinspection PyBroadException
def dict_repr(dict_, without_key_prefix=None):
    """ Our string representation of a python dict. """
    pprint_meta = u""
    for k, v in dict_.iteritems():
        if without_key_prefix and k.startswith(without_key_prefix):
            continue
        try:
            if isinstance(v, (tuple, list)):
                v = [uni(x) for x in v]
                pprint_meta += u"\n%s: [%s]" % ( uni(k), u", ".join(v) )
            else:
                pprint_meta += u"\n%s: %s" % ( uni(k), uni(v) )
        except:
            pass
    return pprint_meta


#=====================================
# tuple related
#=====================================

def ensure_iterable(l, warn=True):
    """
    Ensure that this type is iterable e.g. ('123') will be handled correctly.

    .. note::

      List and tuples are two different things in python. One can be changed and the other one
      is intuitive::

        ('')    # is str !!
        ('',)   # is an array of strings
        ('','') # is an array of strings

  """
    if not l:
        return l
    if isinstance(l, tuple) or isinstance(l, list):
        return l
    else:
        if warn:
            _logger.warning("Non iterable changing to iterable (%s) - "
                            "maybe you forgot to add comma in one element tuple?", repr(l))
        return [l]


#=====================================
# decorators
#=====================================

def time_method(func):
    """
    Timer decorator will store execution time of a function into
    the class which it uses. The time will be stored in
    instance.timed
  """

    def _enclose(self, *args, **kw):
        """ Enclose every function with this one. """
        start = time.time()
        res = func(self, *args, **kw)
        self.timed = time.time() - start
        return res

    return _enclose


def time_function(d):
    """
    Timer decorator will store execution time of a function into
    the specified dict to timed entry.
  """

    def wrap(func):
        def _enclose(*args, **kw):
            start = time.time()
            res = func(*args, **kw)
            d['timed'] = time.time() - start
            return res

        return _enclose

    return wrap


#=====================================
# time related
#=====================================

def nice_time(sec):
    """
    Return milliseconds in formatted string: HH:MM:SS.ms.
  """
    ms = sec * 1000
    h = int(ms / 3600000)
    ms -= h * 3600000
    m = int(ms / 60000)
    ms -= m * 60000
    s = int(ms / 1000)
    ms -= s * 1000
    return "%02d:%02d:%02d.%03d" % (h, m, s, ms)


def now():
    """
    Return today's date and time
  """
    return strftime("%Y-%m-%d %H:%M:%S")


def today():
    """
    Return today's date in isoformat
  """
    return date.today().isoformat()


def yesterday():
    """
    Return yesterday's date in isoformat
  """
    return (date.today() - timedelta(1)).isoformat()


def in_time_range(from_time_str, to_time_str, time_now=None):
    """
    Returns (True, seconds to to_time_str) if we are inside a time range
    or (False, None) otherwise.
  """
    from datetime import datetime

    def make_datetime(time_str):
        ts = time.mktime(time.strptime("2011 %s" % time_str, "%Y %H:%M"))
        return datetime.fromtimestamp(ts)

    from_time = make_datetime(from_time_str)
    to_time = make_datetime(to_time_str)
    if time_now is None:
        time_now = datetime.now().strftime("%H:%M")
    time_now = make_datetime(time_now)
    inside = from_time <= time_now <= to_time

    def total_seconds(td):
        # this method not available in python2.6
        return td.seconds + td.days * 24 * 3600

    return inside, total_seconds(to_time - time_now) if inside else None


#=====================================
# RTTI related
#=====================================

# noinspection PyBroadException
def _str(inst, full=False):
    """
    Return name of a class/instance. If full is True, try to return
    fully qualified name.
  """
    if full:
        try:
            return re.match(r"[^']+'([^']+)'.*", str(inst.__class__)).group(1)
        except:
            pass
    if hasattr(inst, '__name__'):
        return inst.__name__
    if hasattr(inst, '__class__') and hasattr(inst.__class__, '__name__'):
        return inst.__class__.__name__

    _logger.warning("Cannot find out the name of [%s]", repr(inst))
    return "Invalid name [%s]" % repr(inst)


def strs(str_array):
    """ Create unicode strings. """
    if not isinstance(str_array, (tuple, list)):
        _logger.warning("Neither array nor tuple supplied to strs!")
        return [u""]
    return u"\n".join(map(lambda x: uni(x), str_array))


#=====================================
# numeric
#=====================================

def get_int(number_str, default_int):
    """ Try to parse str to int if not possible than return default """
    try:
        return int(number_str)
    except ValueError:
        return default_int


#=====================================
# apache
#=====================================

# noinspection PyBroadException
def query2array(environ):
    """ Http query parameters to array. """
    encoded_post = environ['QUERY_STRING']
    if not encoded_post or len(encoded_post) == 0:
        _logger.warning("No query string.")

    params = []
    for param in encoded_post.split("&"):
        try:
            (k, v) = param.split("=")
            params.append((k.strip(), v.strip()))
        except:
            continue
    return params


# noinspection PyBroadException
class apache_auth(object):
    # pylint: disable=C0111

    cookie_name = "autosystem"

    def __init__(self, file_=None):
        self._auth_file = None
        self._auth = {}
        if os.path.exists(file_):
            try:
                # parse apache .htaccess like file
                # currently supported directives are
                # - AuthUserFile
                #
                lines = open(file_, "r").readlines()
                for line in [x for x in lines if not x.strip().startswith("#")]:
                    elements = map(lambda x: x.strip(), line.split())
                    if len(elements) == 2:
                        # we have dictionary style object
                        #
                        if elements[0] == "AuthUserFile":
                            self._auth_file = elements[1]
                            break
            except:
                _logger.warning("Exception while reading [%s].", file_)
        else:
            _logger.warning("Can not find .htaccess file [%s].", file_)
            return

        # sanity checks
        #
        if not self._auth_file:
            _logger.warning("Can not find AuthUserFile directive.")
            return
        if not os.path.exists(self._auth_file):
            _logger.warning("Can not find AuthUserFile file [%s].", self._auth_file)
            return

        try:
            lines = open(self._auth_file, "r").readlines()
            for line in filter(lambda x: x.strip() != "", lines):
                username, password = line.split(":", 1)
                self._auth[username] = password.strip()
        except:
            _logger.warning("Exception while reading [%s].", self._auth_file)

    def auth(self, username_str, password_str):
        """ Authenticate. """
        return username_str in self._auth and self._auth[username_str] == password_str

    def auth_post(self, environ):
        """ Authenticate. """
        #'username=jozo&password=3e450f676552d0bbd72188107db29835&redirect_url'
        params = dict(query2array(environ))
        authenticated = self.auth(params["username"], params["password_hidden"])
        cookie = "%s=" % apache_auth.cookie_name
        if authenticated:
            cookie += "%s:%s" % (params["username"], params["password_hidden"])
        return authenticated, params, cookie

    def auth_cookie(self, environ):
        cookies = environ.get('HTTP_COOKIE', '').split(";")
        for cookie in cookies:
            try:
                k, v = cookie.split("=")
            except:
                continue
            if k.strip() == apache_auth.cookie_name:
                username, password = v.split(":", 1)
                return self.auth(username, password)
        return False

    def check_login(self, environ, headers):
        # Check login credentials
        #
        if len(query2array(environ)) > 0:
            try:
                authenticated, _, cookie = self.auth_post(environ)
                if authenticated:
                    headers.append(('Set-Cookie', cookie))
                    return True
            except:
                # something went wrong - go to normal login page
                _logger.exception("")
        return False


def urlencode(url_str):
    """ Encode special chars for urls. """
    return urllib.unquote(url_str)


def urlstripchars(url_str):
    """ Convert slash to backslash. """
    return url_str.replace("\\", "/")


#=====================================
# unsensify
#=====================================

# noinspection PyUnresolvedReferences
def unsensify(sensitive_dict):
    """ Try to remove sensitive data. """
    new_dict = {}
    for k, v in map(lambda x: (x, sensitive_dict[x]), sensitive_dict.keys()):
        if isinstance(v, basestring) or isinstance(v, int):
            if "password" in k:
                continue
            if k == "bs_upload_scp_address" and v.split(":") > 3:
                continue
            if k == "cvs_command" and v.split(":") > 5:
                continue
            new_dict[k] = v

    return new_dict


def unsensify_cmd(cmd_str, max_len=None):
    """ Try to remove sensitive data. """
    cmds = cmd_str.split()

    def _change(s):
        return s + " ... stopping output - probably contains sensitive information"

    if len(cmd_str) > 3:
        for i, frag in enumerate(cmds):
            # something suspicious?
            #
            if "pass" in frag.lower() or \
                    len(frag.split(":")) > 3:
                return _change(" ".join(cmds[:i]))

    return cmd_str[:max_len]


#=====================================
# extract info
#=====================================

# noinspection PyBroadException
def extract_project_name_from_build(lines, line_number, project_default):
    """
    Extract project name from build log.
  """
    line = lines[line_number]

    try:
        # VS20* style
        #
        project_re = re.compile('Project: (.*), Configuration: ')
        m = project_re.search(line)
        if m:
            return m.group(1)

        # ivy + browsersoft style
        #
        if line.strip() == "print-location:":
            return os.path.basename(lines[line_number + 1].split()[-1])

    except:
        pass

    return project_default


#=====================================
# simple local system
#=====================================

def run(cmd, timeout=None):
    """ Run an external command. """
    if settings.settings.get("debug", False):
        _logger.warning("Running in debug mode => not executing (%s)", cmd)
        return 0, "", ""

    import tempfile
    import subprocess

    tempik = tempfile.NamedTemporaryFile(delete=False)
    p = subprocess.Popen(cmd, shell=True, stdin=None, stdout=tempik, stderr=subprocess.STDOUT)

    watcher = None
    if not timeout is None and timeout > 0:
        watcher = watchdog(timeout, p, cmd)
        watcher.start()

    # wait for the end
    p.communicate()

    if not timeout is None and timeout > 0:
        # release watchdog
        p.returncode = watcher.release(p.returncode)

    # read stdin
    tempik.seek(0)
    ret = [tempik.read().strip(), None]  # stdout, stderr
    tempik.close()
    try:
        with codecs.open(tempik.name, "r", "utf-8", errors='replace') as ftemp:
            ret[0] = ftemp.read().strip()
        if p.returncode != 0:
            _logger.warning("Run problem with [retcode:%s][%s][%s][%s]", p.returncode, cmd, ret[0], ret[1])

    except Exception, e:
        _logger.warning("Run problem with [%s][%s][%s]", cmd, ret[0], ascii(e))
        ret[0] = None
    os.unlink(tempik.name)

    return p.returncode, ret[0], ret[1]


def path_glob_needed(path):
    """
    Return True if the path needs glob.

    See glob python package.
  """
    for special_char in ['*', '?']:
        if special_char in path:
            return True
    return False


def path_expand_glob_if_needed(filepath_arr):
    """
    Return array with string paths containing special chars
    like '*' or '?' converted to unix like path regular expressions.

    See glob python package.
  """
    new_paths = []
    for path in filepath_arr:
        if path_glob_needed(path):
            new_paths.append(glob.iglob(path))
        else:
            new_paths.append(path)
    return new_paths


class watchdog(object):
    """
    Watchdog for asynchronous operations with timeout.
  """

    def __init__(self, timeout, process, cmd=None):
        self._event = threading.Event()
        self._p = process
        self._timeout = timeout
        self._timer = None
        self._cmd = cmd

    def start(self):
        """ Set timer on with timeout if specified """
        if self._timeout == 0:
            return None
        event = self._event
        p = self._p

        def _kill_process_after_a_timeout():
            p.terminate()
            event.set()  # tell the main routine that we had to kill
            # use SIGKILL if hard to kill...
            _logger.warning("Killing process by watchdog [PID:%s][%s]...",
                            p.pid, ascii(self._cmd))
            return

        self._timer = threading.Timer(self._timeout, _kill_process_after_a_timeout)
        self._timer.daemon = True
        self._timer.start()

    def release(self, retcode):
        """ Release timeout. """
        if self._timeout == 0:
            return retcode

        self._timer.cancel()
        fired = self._event.isSet()
        self._event.clear()
        return -1 if fired else retcode


#=====================================
# simple environment
#=====================================

# noinspection PyRedeclaration
class environment(object):
    """
    This class represents the execution environment.
  """
    OUTPUT_DIR = 'output_dir'
    DB_BACKEND = 'db_backend'
    VERBOSE = 1
    VERBOSE_ALL = 2

    # pylint: disable=C0111

    def __init__(self):
        self._config = {}
        self._count = sys.maxint
        self._debug = False
        self._profile = False
        self._reader = None
        self._verbose = 0
        self._action = None
        self._action_param = None
        self._config[self.OUTPUT_DIR] = os.path.abspath(os.getcwd())

    # dictionary like interface
    def __contains__(self, key):
        return key in self._config

    def __setitem__(self, key, val):
        self._config[key] = val

    def __getitem__(self, key):
        """ Getitem automatically replaces string templates with their values. """
        if not key in self:
            exit(ENVIRONMENT_ENTRY_NOT_FOUND, "[%s] not in %s" % (key, _str(self)))
        return self._config[key]

    def keys(self):
        return self._config.keys()

    def update(self, conf):
        """ Update environment with new entries and call substitute. """
        self._config.update(copy.deepcopy(conf))
        self.substitute()
        self._debug = self.get_value("debug", False)

    def substitute(self):
        """
      Substitutes template strings in environment. Supports
      hierarchical dictionary templates.
      ["key1"]["key2"] is accessible as ${key1_key2}
    """

        def create_keys(prefix, parsed_dict):
            assert isinstance(parsed_dict, dict)
            tmp_dict = {}
            for k, v in parsed_dict.iteritems():
                new_prefix = u"%s_%s" % (prefix, k) if prefix else k
                if isinstance(v, basestring):
                    tmp_dict[new_prefix] = v
                elif isinstance(v, dict):
                    tmp_dict.update(create_keys(new_prefix, v))
            return tmp_dict

        subst_templates = create_keys(None, self._config)
        for k, v in self._config.iteritems():
            if isinstance(v, basestring):
                self._config[k] = subst_str(v, subst_templates)
            elif isinstance(v, dict):
                self._config[k] = subst_dict(v, subst_templates)
            elif isinstance(v, (list, tuple)):
                self._config[k] = [subst_str(x, subst_templates)
                                   if isinstance(x, basestring) else x for x in v]

    #========================================
    # getters
    #========================================

    def get_value(self, key, default=None):
        if key in self:
            return self[key]
        if default is None:
            _logger.critical("Error: Can't find requested key in %s: %s", _str(self), key)
            exit(ENVIRONMENT_ENTRY_NOT_FOUND)
        return default

    def get_db_backend(self):
        """ Return the URL (e.g. local file) which should be used for storing information. """
        return self[self.DB_BACKEND]

    def set_db_backend(self, backend_str_or_none):
        self[self.DB_BACKEND] = backend_str_or_none

    def get_output_directory(self):
        return self[self.OUTPUT_DIR]

    def set_output_directory(self, dir_):
        self[self.OUTPUT_DIR] = dir_

    #========================================
    # properties
    #========================================

    @property
    def count(self):
        return self._count

    @count.setter
    def count(self, count):
        self._count = count

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, debug_val):
        self._debug = debug_val

    @property
    def reader(self):
        return self._reader

    @reader.setter
    def reader(self, reader):
        self._reader = reader

    @property
    def verbose(self):
        return self._verbose

    @verbose.setter
    def verbose(self, verbose):
        self._verbose = verbose

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, profile):
        self._profile = profile

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, action):
        self._action = action.lower()

    @property
    def action_param(self):
        return self._action_param

    @action_param.setter
    def action_param(self, action_param):
        self._action_param = action_param.lower()


def ensure_keys(keys_arr, dict_):
    """ Check whether all the required keys are present. """
    found_all = True
    for key in keys_arr:
        if not key in dict_:
            _logger.critical("Key [%s] not in dictionary!", key)
            found_all = False
    return found_all


#=====================================
# string populate
#=====================================

def clean_word(word):
    """ Strip word from several non ascii characters. """
    chars = "!?.=-:,()"
    return word.rstrip(chars).lstrip(chars)


#=====================================
# print after
#=====================================

# noinspection PyRedeclaration
class print_after(object):
    """ Class for printing few information about stepping cycles. """
    pos = 0
    max_val = 500
    _logger = None

    def __init__(self):
        pass

    @staticmethod
    def logger(log):
        """ Set logger which will output the info. """
        print_after._logger = log

    @staticmethod
    def after(max_val):
        """ Set value after which info should be printed. """
        print_after.max_val = max_val

    @staticmethod
    def reset():
        """ Reset counter. """
        print_after.pos = 0

    @staticmethod
    def step(step=1):
        """ Do one step. """
        print_after.pos += step
        if print_after._logger and print_after.pos % print_after.max_val == 0:
            print_after._logger.info("Done [%d].", print_after.pos)


#=====================================
# info
#=====================================

def host_info():
    """ Return simple info about OS/arch we run on. """
    import getpass
    import platform

    user = getpass.getuser()
    os_, mach = platform.system(), platform.machine()
    return """ [%s @ %s/%s] """ \
           % (user, os_, mach)


def populate_date(date):
    """ Try to find date patterns and convert them to default one. """
    v = date.strip()
    patterns = [
        (r"^D:(\d\d\d\d)(\d\d)(.*)$", r"\1-\2"),
        (r"^(\d\d\d\d)(\d\d)(.*)$", r"\1-\2"),
        (r"^(\d+)/\d+/(\d\d+) \d\d(.*)$", r"\2-\1"),
        (r"^.* (\d\d\d\d)(?:\W+.*$|$)", r"\1-??"),
    ]

    for (pat, repl) in patterns:
        v_new = re.sub(pat, repl, v)
        if v != v_new:
            return v_new.replace("-0", "-")  # remove 0 from month
    return "??"  # better to avoid javascript problems and indicate error


def xml_strip_control_chars(input_, leave_new_lines=True):
    """
    Strip control characters from xml including ascii control chars.
  """
    # unicode invalid characters
    illegal_unichrs = [(0x00, 0x08), (0x0B, 0x1F), (0x7F, 0x84), (0x86, 0x9F),
                       (0xD800, 0xDFFF), (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF),
                       (0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF), (0x3FFFE, 0x3FFFF),
                       (0x4FFFE, 0x4FFFF), (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
                       (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF), (0x9FFFE, 0x9FFFF),
                       (0xAFFFE, 0xAFFFF), (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
                       (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF), (0xFFFFE, 0xFFFFF),
                       (0x10FFFE, 0x10FFFF)]

    RE_XML_ILLEGAL = u'[%s]' % u''.join([u"%s-%s" % (unichr(low), unichr(high))
                                         for (low, high) in illegal_unichrs if low < sys.maxunicode])

    input_ = re.sub(RE_XML_ILLEGAL, u"", input_)
    # ascii control characters
    if leave_new_lines:  # leave 0x0a 0x0d
        input_ = re.sub(r"[\x01-\x09\x0E-\x1F\x0B\x0C\x7F]", "", input_)
    else:
        input_ = re.sub(r"[\x01-\x1F\x7F]", "", input_)
    return input_


def xml_strip_control_chars_dict(dict_):
    for k, v in dict_.iteritems():
        if isinstance(v, basestring):
            dict_[k] = xml_strip_control_chars(v)
        elif isinstance(v, (list, tuple)):
            new_v = []
            for list_item in v:
                new_v.append(xml_strip_control_chars(uni(list_item)))
            dict_[k] = new_v


#=====================================
# mime
#=====================================

class mime(object):
    """ Simple mime type abstraction. """
    PDF_MIME = "application/pdf"

    @staticmethod
    def pdf(mime_str):
        """ Is the mimetype pdf. """
        return mime_str == mime.PDF_MIME


def to_array(o):
    """ Convert to array. """
    return [o] if hasattr(o, "items") or not hasattr(o, "__iter__") else o


# noinspection PyBroadException
def info_solr_home(env_dict, logger, stats_url, info_dict=None):
    assert env_dict["indexer"]["solr_home"]
    assert os.path.exists(env_dict["indexer"]["solr_home"])
    path = env_dict["indexer"]["solr_home"]
    KB = 1024
    MB = KB * KB
    GB = KB * MB

    # http://lucene.apache.org/core/4_0_0-ALPHA/core/org/apache/lucene/codecs/lucene40/package-summary.html#Limitations
    _files = {
        "ext": {
            ".*fnm": [0, "Stores information about the fields"],

            ".*fdx": [0, "Field index - contains pointers to field data"],
            ".*fdt": [0, "Field data -the stored fields for documents"],
            ".*frq": [0, "Frequencies - contains the list of docs which contain each term along with frequency"],

            ".*tis": [0, "Term Infos - part of the term dictionary, stores term info"],
            ".*tim": [0, "The term dictionary, stores term info"],
            ".*tip": [0, "The index into the Term Dictionary"],

            ".*tii": [0, "Term Info Index - the index into the Term Infos file"],

            ".*prx": [0, "Positions - stores position information about where a term occurs in the index"],
            ".*nrm.*": [0, "Norms - encodes length and boost factors for docs and fields"],
            ".*dv.*": [0, "Per document values"],
            ".*tvx": [0, "Term Vector Index - stores offset into the document data file"],
            ".*tvd": [0, "Term Vector Documents - contains information about each document that has term vectors"],
            ".*tvf": [0, "Term Vector Fields - the field level info about term vectors"],
            ".*del": [0, "Deleted Documents - info about what files are deleted"],
            ".*cfs": [0, "An optional virtual file consisting of all the other index files."],
            ".*cfe": [0, "An optional virtual file consisting of all the other index files."],
            ".*segments.*": [0, "Segment information"],
            ".*si": [0, "Segment information"],
            ".*pay": [0, "Payloads"],
            ".*pos": [0, "Positions"],
            ".*doc": [0, "Frequencies and Skip Data"],
        }
    }
    path = os.path.join(path, "*")
    logger.info(u"Number of files in [%s] is [%s]" % ( path,
                                                       len(glob.glob(path)) ))

    size_info = {}
    info_str = u"\n"
    for k, v in _files["ext"].iteritems():
        cnt = 0
        pattern = re.compile(k)
        for f in glob.glob(path):
            if pattern.search(f):
                _files["ext"][k][0] += os.path.getsize(f)
                cnt += 1
        size, info = _files["ext"][k]
        info_str += u"[%s GB, %s MB, %s KB] in [%s] files\n  [%s] [%s]\n" % (
            size / GB, size / MB, size / KB, cnt, k, info[:70])
        size_info[k.replace("*", "").replace(".", "")] = size / KB

    total = 0
    total_files = 0
    for f in glob.glob(path):
        total += os.path.getsize(f)
        total_files += 1
    info_str += u"Total [%s GB, %s MB] in [%s] files" % (total / GB, total / MB, total_files)
    logger.warning( info_str )

    # more info
    def _fetch_json( url, in_field=None, remove_fields=None ):
        req = urllib2.Request( url + "&wt=json" )
        f = urllib2.urlopen( req )
        response = f.read()
        f.close()
        import json
        js = json.loads( response )
        if in_field is not None:
            for f in in_field:
                js = js[f]
            if remove_fields is not None:
                for r in remove_fields:
                    if r in js:
                        del js[r]
        return js

    import pprint
    pp = pprint.PrettyPrinter( indent=4 )

    js_luke = _fetch_json( env_dict["backend_host"] + "/admin/luke?",
                      ("index",), ( "fields", "info" ) )
    logger.warning( u"Index info all\n%s", pp.pformat(js_luke) )
    js_stats = _fetch_json( env_dict["backend_host"] + stats_url,
                      ("stats", "stats_fields"), None )
    logger.warning( u"Index info stats\n%s", pp.pformat(js_stats) )

    # prepare for R - type name size
    #
    if info_dict is None:
        return
    cleanup_size = ( "nrm", "prx", "segments", "cfe", "tis", "del", "frq", "tii", "dv", "tvf", "cfs" )
    for k in cleanup_size:
        if k in size_info:
            if size_info[k] != 0:
                logger.critical( u"Index file cleaned up but not null %s", k )
            del size_info[k]
    size_info_str = u""
    for k, v in size_info.iteritems():
        size_info_str += u"%s:%s:%s\n" % ( u"type", k, v )
    size_info_str += u"%s:%s:%s\n" % ( u"type", u"total", total / KB )
    info_dict["size"] = size_info_str
    # index
    index_info_str = u""
    index_info_str += u"%s:%s:%s\n" % ( u"type", u'"#docs"', js_luke["numDocs"] )
    try:
        index_info_str += u"%s:%s:%s\n" % ( u"type", u'"#for."', js_stats["math_count"]["sum"] )
        index_info_str += u"%s:%s:%s\n" % ( u"type", u'"#for. mean"', js_stats["math_count"]["mean"] )
        index_info_str += u"%s:%s:%s\n" % ( u"type", u'"#for. max"', js_stats["math_count"]["max"] )
    except:
        pass
    info_dict["index"] = index_info_str
