#
# Create templates using $title and $text
#

htmltemplate = u"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml" lang="en" dir="ltr">
<head>
<title>$title</title>

<meta name="id" content="$id" />
<meta name="url" content="$url" />
<meta name="category" content="$category" />
<meta name="lang_avail" content="$lang_avail" />

<meta name="citations_count" content="$citations_count" />
$refs

<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta http-equiv="Content-Style-Type" content="text/css" />
<meta name="generator" content="MediaWiki 1.16wmf4" />
</head>

<body class="mediawiki ltr ns-0 ns-subject page-Superconformal_algebra skin-vector">
<pre>
$text
</pre>
</body>
</html>"""


mathjaxhtmltemplate = (u"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html lang="en-US" xml:lang="en-US" xmlns="http://www.w3.org/1999/xhtml">
      <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <meta http-equiv="Content-Language" content="en" />
        <link href="./static/css/layout.css" rel="stylesheet" type="text/css" />
        <link href="./static/css/smoothness/jquery-ui-1.8.13.custom.css" rel="stylesheet" type="text/css" />

        <script type="text/x-mathjax-config">
          MathJax.Hub.Config({
            mml2jax: {
              skipTags: ["m:annotation","m:annotation-xml","annotation","annotation-xml",
               ],
              inlineMath: ['eegomathmathml','mathmlegomathh'],
               preview: ["//mathml...//"],
            },
            tex2jax: {
               inlineMath: [ ['eegomath','egomathh'], ],
               preview: ["//math...//"],
              }
          });
        </script>


        <script type="text/javascript"
          src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
        </script>

      </head>

<body>
""",
u"</body></html>")
