# -*- coding: utf-8 -*-
import sys
import os
from os import path
from datetime import datetime
from io import open


CURR_DIR = path.abspath(path.dirname(__file__))
PKG_ROOT = path.join(path.dirname(CURR_DIR), 'src/thumbor_video_engine')


def get_release():
    with open(path.join(PKG_ROOT, '__init__.py'), encoding='utf-8') as f:
        lines = f.read().splitlines()
    for line in lines:
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), '..', 'src')))

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'


project = u'thumbor-video-engine'
copyright = u'%d, The Atlantic' % datetime.now().year
author = u'The Atlantic'

release = get_release()
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
