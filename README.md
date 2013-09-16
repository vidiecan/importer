Importer framework
==================

Generic importer framework with one dataset made specially for EgoMath.

Possible options for wiki dataset are:

        * wiki_to_wikis - e.g., enwiki-20130204-pages-articles.xml -> enwiki-20130204-pages-articles.part*.xml
        * wikis_to_huge_math - e.g., enwiki-20130204-pages-articles.part*.xml -> math-enwiki-20130204-pages-articles.xml.part*.xml.pages
        * wiki_maths_to_wiki_math - e.g., math-enwiki-20130204-pages-articles.xml.part*.xml.pages -> math-all.pages
        * wiki_math_to_pages - e.g., math-all.pages -> output/*/*.html
        * test_queries - perform a set of test queries
