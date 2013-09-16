# -*- coding: utf-8 -*-
# See main file for license.
#

settings = {

    "backend_host": "project specific",

    # indexer instance
    #
    "indexer": {
        "mode": "w",
        "autocommit": False,
        "keepalive": True,
        "optimise": False,

        "id_str": "id",

        #"egomath_jvm": "./libs/egomath/dist_temp/egomathsearch.jar;./libs/xercesImpl.jar;./libs/mathml.jar",
        # for windows
        "egomath_jvm": "./libs/egomath/dist/egomathsearch.jar;./libs/xercesImpl.jar;./libs/mathml.jar",
        # for linux
        #"egomath_jvm" : "./libs/egomath/dist/egomathsearch.jar:./libs/xercesImpl.jar:./libs/mathml.jar",
        "snippet_chars": 100,
        "retry_timeout": -1,
        "share_adapter": True,

        # no write operations will be performed
        "unwriteable": ( "03:00", "03:01" ),
    },

}
