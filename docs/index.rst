==================
repostats
==================

This is a library for gleaning information from GitHub through APIv3.
This tool currently requires the use of an `OAuth <https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/>`_ token from GitHub.

* data is initially returned in list and dictionary structures that users can do with as they wish
* there are several functions that take this data create an HTML output page, with a sortable table,  or text output summarizing basic information about the repositories. 
* data that is returned from the GitHub api can be saved and retrived from local json files


Where to Find
=============
The package currently lives on GitHub at `repostats <http://github.com/spacetelescope/repostats>`_.


.. toctree::
   :maxdepth: 1

    Examples and Output <repostats/examples.rst>
    API - available functions <repostats/reference_api.rst>

