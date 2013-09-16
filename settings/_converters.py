# -*- coding: utf-8 -*-
# See main file for license.
#

settings = {

    # this should not be changed locally
    #
    "converters": {

        "encoding": u"utf-8",

        "latexml": {
            #"convert_service" : u"http://tex2xml.kwarc.info/test/ajax/convert.php",
            "url": u"http://latexml.mathweb.org/convert",
            "result_field": u"result",
            "status_field": u"status",
            "status_ok": ( u"No obvious problems", ),

            "timeout": 180,
            "pickle_ok": u"output/pickles/mathml.pickle",
            "pickle_fail": u"output/pickles/mathml.fail.pickle",

            #"fail_output"     : u"output/pickles/mathml.fail.html",
            #"ok_output"       : None,#u"output_pickles/mathml.html",
        }


    },

}
