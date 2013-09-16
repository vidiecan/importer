# -*- coding: utf-8 -*-
# See main file for license.
#

settings = {

    # this should not be changed locally
    #
    "mathml": {
        #"convert": "pickle",  # the whole process using already pickled conversions
        "convert": "db",  # the whole process using already pickled conversions
        #"convert": None, # the whole process using already pickled conversions

        "convert_latex": True,  # use convert_service

        #"fail_output"     : u"output/pickles/mathml.fail.html",
        #"ok_output"       : None,#u"output_pickles/mathml.html",
    },

}
