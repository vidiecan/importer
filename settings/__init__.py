# -*- coding: utf-8 -*-
"""
  Settings module.
"""
# See main file for license.
#

settings = {

    "debug": False,

    "datasets": {
        "export_prefix": "exported_",
        "default_method": "process",
    },

    "input": u"project specific mode",
    "input_production": u"project specific mode",

    # indexer instance
    #
    "indexer": {
    },

    "parallel": {
        #"enabled"    : False,
        "enabled": True,

        # production
        "enabled_production": True,
    },

    # name
    "name": u"Egomath importer v1.3",
}


def smart_update( what, with_what ):
    for k, v in with_what.iteritems():
        # update dicts instead of replace
        if k in what and isinstance(what[k], dict):
            what[k] = dict(what[k].items() + v.items())
        else:
            what[k] = v

# update settings with project ones
#
from . import _advanced
smart_update(settings, _advanced.settings)

from . import _indexer
smart_update(settings, _indexer.settings)

from . import _pager
smart_update(settings, _pager.settings)

from . import _converters
smart_update(settings, _converters.settings)

from . import _db
smart_update(settings, _db.settings)
