# See main file for license.
# -*- coding: utf-8 -*-
from settings import settings
import utils

logger = utils.logger("common.indexer")
from jpype import *


#not needed - lock = multiprocessing.Lock()
#noinspection PyBroadException
jvm = None


# noinspection PyBroadException
class egomath(object):
    def __init__( self ):
        # - not multiprocessing returning? setUsePythonThreadForDeamon(True)
        self.open()
        self.indexer = None
        res = self.init()
        if not res:
            logger.warning("Egomath java provider not initialised correctly.")
        else:
            logger.warning( "Egomath version:\n%s", self.version() )

    def open(self):
        global jvm
        if jvm is None:
            jvm = "something"
            startJVM(
                getDefaultJVMPath(),
                #"-ea", # - enable asserts
                "-XX:-UseParallelGC",
                "-Xmx200m",
                "-Djava.class.path=%s" % settings["indexer"]["egomath_jvm"])

    def init( self ):
        for cls in ["org.egomath.formats.xml.XmlUtil",
                    "org.egomath.Indexer"]:
            try:
                JClass(cls)
            except:
                logger.exception("Initialize jvm/jpype correctly please!")
                return False

        self.egomath_package = JPackage('org').egomath
        self.indexer = self.egomath_package.Indexer()
        return True

    #noinspection PyComparisonWithNone
    def math_from_mathml( self, mathml, explicit_include_tex=False ):
        if not self.indexer:
            raise EnvironmentError("jvm error - egomath.indexer is None")
        if explicit_include_tex:
            return self.indexer.mathml_to_string_include_tex(mathml)
        else:
            return self.indexer.mathml_to_string(mathml)

    #noinspection PyComparisonWithNone
    def mathml_to_tex( self, mathml ):
        if not self.indexer:
            raise EnvironmentError("jvm error - egomath.indexer is None")
        return self.indexer.mathml_to_tex(mathml)

    #noinspection PyComparisonWithNone
    def math_from_tex( self, tex ):
        if not self.indexer:
            raise EnvironmentError("jvm error - egomath.indexer is None")
        return self.indexer.tex_to_string(tex)

    #noinspection PyComparisonWithNone
    def math_from_tex_cleanup( self, tex ):
        if not self.indexer:
            raise EnvironmentError("jvm error - egomath.indexer is None")
        return self.indexer.tex_to_string_cleanup(tex)

    #noinspection PyComparisonWithNone
    def features_from_mathml( self, mathml_str, depth=-1 ):
        if not self.indexer:
            raise EnvironmentError("jvm error - egomath.indexer is None")
        return self.indexer.features_from_mathml(mathml_str, depth)

    #noinspection PyComparisonWithNone
    def features_from_tex( self, tex_str, depth=-1 ):
        if not self.indexer:
            raise EnvironmentError("jvm error - egomath.indexer is None")
        try:
            return self.indexer.features_from_tex(tex_str, depth)
        except:
            logger.exception( u"Got params [%s] [%s]", tex_str, depth )
            raise

    def reset_logging( self ):
        return self.egomath_package.Indexer.reset_logging()

    def version(self):
        return self.egomath_package.Indexer.version()

    def close(self):
        global jvm
        try:
            if not jvm is None:
                jvm = None
                shutdownJVM()
        except:
            pass

    def __del__(self):
        self.close()


egomath_inst = egomath()
