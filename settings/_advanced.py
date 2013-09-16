# -*- coding: utf-8 -*-
# See main file for license.
#
import os

settings = {

    #==============================
    # debug
    #==============================
    "exception_file": os.path.join(os.path.dirname(__file__), "../exception.log"),


    # max parallel runners
    # - threads - use False only if you know what you are doing filters will not working correctly
    #
    "parallel": {
        # if there are few tasks, this should be small otherwise not all processes
        # will be started (python will think that they are not needed)
        "chunksize": 100,
        # if you specify this, you have to be sure that there is enough
        # processes so the work is done!
        "maxtasksperchild": None,
        "max": 8,
        "threads": False,

        "wait_file" : os.path.join(os.path.dirname(__file__), "../waitforme"),
        "wait_sleep" : 5,
    },


    # logger config
    "logger_config": os.path.join(os.path.dirname(__file__), "logger.config"),

}
