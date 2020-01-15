# -*- coding: utf-8 -*-
import sys
import os
from datetime import datetime


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'


project = u'thumbor-video-engine'
copyright = u'%d, The Atlantic' % datetime.now().year
author = u'The Atlantic'

release = __import__('thumbor_video_engine').__version__
version = '.'.join(release.split('.')[:2])

extensions = []

source_suffix = '.rst'
master_doc = 'index'
language = None

exclude_patterns = [u'_build', 'Thumbs.db', '.DS_Store']
add_function_parentheses = True
add_module_names = False
pygments_style = 'trac'
todo_include_todos = False

html_theme = 'default'
html_last_updated_fmt = '%b %d, %Y'
html_show_sphinx = False

if not on_rtd:  # only import and set the theme if we're building docs locally
    extensions.insert(0, 'readthedocs_ext.readthedocs')

    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
