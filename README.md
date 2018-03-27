# repostats

This is a library that helps create a sortable HTML table that contains a summary of all the repositories for the specified GitHub organization. It currently requires the user to create a GitHub OAuth token for authentication and to increase the rate limit. 

Here's an example use of the main functionality, get repository info for the spacetelescope
organization, with 50 results per page and only look at the public repositories:

        In [1]: import repostats

        In [2]: data=repostats.get_repo_info(org='spacetelescope', limit=50, pub_only=True)
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

Now, make a summary page of the results and save to spacetelescope.html:

        In [3]: repostats.make_summary_page(data, outpage='spacetelescope.html')
        Saving to spacetelescope.html
        Checking for older html file before writing spacetelescope.html


If you just want to return some basic stats on a specific repository:

        In [4]: stats = repostats.get_statistics(org='spacetelescope', name='asdf')
        In [5]: repostats.print_text_summary(stats)
        Report for spacetelescope: asdf
        Open issues:  15
        Closed issues this week:   6
        Closed issues this month:  19
        Commits in last week:   0
        Commits in last month:   0

        Open Pull Requests:   3

        Number Title                                                                 Created               Last Updated          
        460    WIP: Documentation overhaul for v2.0                                  2018-02-22T14:56:31Z  2018-03-20T20:05:09Z  
        419    Install git hook to automatically update asdf-standard submodule      2017-12-21T21:48:49Z  2018-02-09T17:51:25Z  
        157    WIP: Fast YAML parser                                                 2015-07-23T17:44:07Z  2015-07-23T19:28:20Z  

There are more statistics saved to the `stats` dictionary, it's up to the user to decide what data they would like to view. The text summary is just a basic report example. 


View the example HTML output page: [spacetelescope](https://htmlpreview.github.io/?https://github.com/sosey/repostats/blob/master/spacetelescope.html)
