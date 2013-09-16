# -*- coding: utf-8 -*-
# See main file for license.

import utils
import re

_logger = utils.logger("common.indexer")
from xml.sax.saxutils import escape


class document(object):
    """
    Class representing one document from index.
  """

    def __init__( self, keys, values, env_dict ):
        self._keys = keys
        self._values = values
        self._env = env_dict

    def dict( self, check_keys=True ):
        document_dict = {}

        missing_fields_arr = []
        for k in self._keys:
            # this means we do not have a key filled - very bad
            if not k in self._values:
                if check_keys:
                    _logger.warning(u"Key [%s] not in meta dictionary for [%s]",
                                   k, self._values.get(self._env["metadata"]["primary_key"], u"unknown id"))
                    return {}
                else:
                    continue

            value = self._values[k]
            if not value is None:
                document_dict[k] = value
            else:
                # do not log out missing text fields - we do it in elsewhere
                if not k.startswith(u"text"):
                    missing_fields_arr += [k]

        # remove empty fields
        #
        empty_fields_arr = []
        for k, v in document_dict.iteritems():
            #noinspection PySimplifyBooleanCheck
            if v is None:  # or len(utils.uni(v)) == 0:
                empty_fields_arr += [k]
            # delete empty fields - save index space/problems with empty in result list
        for k in empty_fields_arr:
            del document_dict[k]

        # escape chars in text fields if present
        #
        for key in self._keys:
            if key.startswith(u"text") and key in document_dict:
                # 1st put space between math there
                # so we can remove the shi.t in the indexer
                document_dict[key] = \
                    re.compile(u"><", re.UNICODE).sub(u"> <", document_dict[key])
                #
                document_dict[key] = escape(document_dict[key])
            if key.startswith(u"math") and not key == "math_count":
                arr = document_dict[key]
                if isinstance(arr, (tuple, list)):
                    for pos, v in enumerate(arr):
                        arr[pos] = re.compile(u"</m:math", re.UNICODE).sub(u" </m:math", v)
                        arr[pos] = re.compile(u"</math", re.UNICODE).sub(u" </math", v)
                else:
                    document_dict[key] = re.compile(u"</m:math", re.UNICODE).sub(u" </m:math", document_dict[key])
                    document_dict[key] = re.compile(u"</math", re.UNICODE).sub(u" </math", document_dict[key])

        # make it xml friendly
        #
        utils.xml_strip_control_chars_dict(document_dict)

        # empty/missing fields
        #
        id_ = self._values.get(self._env["metadata"]["primary_key"], "id not available")
        empty_fields = u""
        for k in empty_fields_arr:
            empty_fields += u" [%s][%s]" % (k, id_)
        missing_fields = u""
        for k in missing_fields_arr:
            if k == "citations":
                pass
            else:
                missing_fields += u" [%s][%s]" % (k, id_)
            # debug warnings
        #
        if len(missing_fields) > 0:
            utils.logger("suspect").warning(
                u"Document has missing field(s): %s", missing_fields)
        if len(empty_fields) > 0:
            utils.logger("suspect").warning(
                u"Document has empty field(s): %s", empty_fields)

        return document_dict
