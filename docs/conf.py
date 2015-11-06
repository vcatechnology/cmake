#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Python GitHub (pygh) documentation build configuration file

import sys
import os
import shlex
import sphinx_rtd_theme

# -- General configuration ------------------------------------------------

# Add the location to find the modules
sys.path.insert(0, os.path.abspath('../..'))

# Minimal Sphinx version
needs_sphinx = '1.0'

# Sphinx extension module names
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
]

# Paths that contain templates
templates_path = ['_templates']

# The suffix(es) of source filenames
source_suffix = ['.rst']

# The encoding of source files.
source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Python GitHub (pygh)'
copyright = '2015, VCA Technology'
author = 'VCA Technology'

# The version info for the project
with open('../VERSION', 'r') as f:
    release = f.read()
version = '.'.join(release.split('.')[:2])

# The language for content autogenerated by Sphinx
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['docs/_*']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Output file base name for HTML help builder.
htmlhelp_basename = 'pyghdoc'

# -- Options for LaTeX output ---------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  (master_doc, 'PythonGitHubpygh.tex', 'Python GitHub (pygh) Documentation',
   'VCA Technology', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'pythongithubpygh', 'Python GitHub (pygh) Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  (master_doc, 'PythonGitHubpygh', 'Python GitHub (pygh) Documentation',
   author, 'PythonGitHubpygh', 'One line description of project.',
   'Miscellaneous'),
]


# -- Options for Epub output ----------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# A list of files that should not be packed into the epub file.
epub_exclude_files = ['search.html']
