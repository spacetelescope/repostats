# repostats

This is a library that helps create a sortable HTML table that contains a summary of all the repositories for the specified GitHub organization. It currently requires the user to create a GitHub OAuth token for authentication and to increase the rate limit. 

Here's an example use of the main functionality:

        In [1]: import release

        In [2]: data=release.get_all_releases('spacetelescope',limit=20)
        Examining https://api.github.com/orgs/spacetelescope/repos?per_page=20....
        Checking latest information for: PyFITS
        Checking latest information for: scientific-python-training-2012
        Checking latest information for: synphot_refactor
        Checking latest information for: stsynphot_refactor
        Checking latest information for: understanding-json-schema
        Checking latest information for: asdf
        Checking latest information for: asdf-standard
        Checking latest information for: imexam
        Checking latest information for: spherical_geometry
        Checking latest information for: astronomy-resources
        Checking latest information for: github-issues-import
        Checking latest information for: drizzle
        Checking latest information for: scientific-python-training-2015
        Checking latest information for: gwcs
        Checking latest information for: specview
        Checking latest information for: astroimtools
        Checking latest information for: yaml-schema-standard
        Checking latest information for: UserTraining2015
        Checking latest information for: cubeviz
        Checking latest information for: imgeom

        In [3]: test=release.make_summary_page(data,'spacetelescope.html')
        Saving to spacetelescope.html
        Checking for older html file before writing spacetelescope.html


View the example HTML output page: [spacetelescope](https://htmlpreview.github.io/?https://github.com/sosey/repostats/blob/master/spacetelescope.html)
