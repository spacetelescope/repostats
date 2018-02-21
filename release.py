"""
Library functions that help summarize
the package repository information for a
specific github organization

"""
from __future__ import print_function, division, absolute_import

import os
import json
import mistune
import urllib3
import urllib3.contrib.pyopenssl
import certifi
from time import gmtime, strftime


def make_summary_page(data=[], outpage="repository_summary.html"):
    """Make a summary HTML page from a list of repositories in the organization.

    Parameters
    ----------
    data: list[dict{}]
        a list of dictionaries
    outpage: string
        the name of the output html page

    """
    urllib3.contrib.pyopenssl.inject_into_urllib3()
    http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())

    if not isinstance(data, list):
        raise TypeError("Expected data to be a list of dictionaries")

    # print them to a web page we can display for ourselves,
    print("Checking for older html file before writing {0:s}".format(outpage))
    if os.access(outpage, os.F_OK):
        os.remove(outpage)
    html = open(outpage, 'w')

    # this section includes the javascript code and google calls for the
    # interactive features (table sorting)

    header = '''
    <html>
      <head>
       <title>Github Organization Package Summary Information </title>

       <meta name="viewport" charset="utf-8" content="width=device-width, initial-scale=1.0">
       <style type="text/css">
            table
            {
                width: 1200px;
                border-collapse: collapse;
            }

            thead
            {
                width: 1200px;
                overflow: auto;
                color: #fff;
                background: #000;
            }
            tbody
            {
                overflow: auto;
            }
            th,td
            {
                padding: .5em 1em;
                text-align: left;
                vertical-align: top;
                border-left: 1px solid #fff;
            }
            .cssHeaderRow {
                background-color: #2A94D6;
                top: 10px;
                overflow: auto;
            }
            .cssHeaderCell {
                color: #FFFFFF;
                background-color: #2A94D6;
                font-size: 14px;
                padding: 6px !important;
                border: solid 1px #FFFFFF;
            }
            .cssTableRow {
                background-color: #F0F1F2;
            }
            .cssOddTableRow {
                background-color: #F0F1F2;
            }
            .cssSelectedTableRow {
                font-size: 20px;
                font-weight: bold;
            }
            .cssHoverTableRow {
                background: #ccd;
            }
            .cssTableCell {
                font-size: 14px;
                padding: 10px !important;
                border: solid 1px #FFFFFF;
            }
            .cssRowNumberCell {
                text-align: center;
            }
        </style>
        <script type="text/javascript" src="https://www.google.com/jsapi"></script>
        <script type="text/javascript">
          google.load("visualization", "1", {packages:["table"]});
          google.setOnLoadCallback(drawTable);
          function drawTable() {
            var data = new google.visualization.DataTable();
            data.addColumn("string", "Package Name");
            data.addColumn("string", "Version");
            data.addColumn("string", "Repository Link");
            data.addColumn("string", "Release Information");
            data.addColumn("string", "Last Released / Changed");
            data.addColumn("string", "Author");
            data.addColumn("string", "Travis-CI");
            data.addColumn("string", "RTD-latest");
            data.addColumn("number", "Open Issues");
            data.addColumn("number", "Forks");
            data.addColumn("number", "Stars");
            data.addColumn("string", "License")


            data.addRows([
    '''
    html.write(header)

    for repo in data:
        # below is the google table code
        software = repo['repo_name']
        version = repo['version']
        if repo['release_notes'] != 'Missing':
            descrip = render_html(repo['release_notes'])
        else:
            changes_url = "{0:s}/blob/master/CHANGES.rst".format(repo['base_url'])
            response = http.request('GET', changes_url)
            if response.status == 200:
                descrip = ("\'<a href=\"{0:s}\">Link to package CHANGES</a>\'".format(changes_url))
            else:
                descrip = ("No CHANGES.rst file, see repository")
        website = repo['website']
        date = repo['published']
        author = repo['author']
        author_page = repo['author_page']
        if author_page == "N/A":
            author_page = repo['base_url']
        issues = repo['open_issues']
        forks = repo['forks']
        stars = repo['stars']
        license = repo['license']
        travis = ("https://img.shields.io/travis/{0:s}/{1:s}.svg".format(repo['organization'],
                                                                         software))
        rtd = ("https://readthedocs.org/projects/{0:s}/badge/?version=latest".format(software))

        html.write("[\"{}\",\"{}\",\'<a href=\"{}\">{}</a>\',{}{}{},\"{}\",\'<a href=\"{}\">{}</a>\',\'<img src=\"{}\">\',\'<img src=\"{}\">\',{},{},{},\"{}\"],\n".format(
                    software, version, website, "Code Repository", chr(96), descrip, chr(96), date, author_page, author,
                    travis, rtd, issues, forks, stars, license))

    page = '''  ]);
    var cssClassNames = {
                    'headerRow': 'cssHeaderRow',
                    'tableRow': 'cssTableRow',
                    'oddTableRow': 'cssOddTableRow',
                    'selectedTableRow': 'cssSelectedTableRow',
                    'hoverTableRow': 'cssHoverTableRow',
                    'headerCell': 'cssHeaderCell',
                    'tableCell': 'cssTableCell',
                    'rowNumberCell': 'cssRowNumberCell'
                };
    var table = new google.visualization.Table(document.getElementById("table_div"));
    table.draw(data, {showRowNumber: true, allowHtml: true, cssClassNames: cssClassNames,});
    }
    </script>
    </head>
    <body>
    <br><p align="center" size=10pt>Click on the column fields to sort </p>
    <br>
    <p align="left" size=10pt>
    <ul>
    <li>Missing Version means no release or tag was found for the repository.<br>
    <li>If there hasn't been any github release or tag  then the information is taken from the last commit to that repository
    </ul>
    </p><br>
    Last Updated: '''

    page += ("{0:s} GMT<br><br> <div id='table_div'></div></body></html>".format(strftime("%a, %d %b %Y %H:%M:%S", gmtime())))
    html.write(page)
    html.close()


def render_html(md=""):
    """Turn markdown string into beautiful soup structure.

    Parameters
    ----------
    md: string
        markdown as a string

    Returns
    -------
    The translated markdown
    """
    if not md:
        return ValueError("Supply a string with markdown")
    m = mistune.markdown(md)
    return m


def get_api_data(url=""):
    """Return the JSON load from the request.

    Parameters
    ----------
    url: string
        The url for querry

    Returns
    -------
    Returns a json payload response
    """
    user_agent = {'user-agent': 'repo-summary-tool'}
    urllib3.contrib.pyopenssl.inject_into_urllib3()
    http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',
                               ca_certs=certifi.where(),
                               headers=user_agent)
    response = http.request('GET', url)
    return json.loads(response.data.decode('iso-8859-1'))


def get_release_specs(data=None):
    """parse out the release information from the json object.

    Parameters
    ----------
    data: dict
        The dictionary of repository information as created by
        the get_all_releases function

    Notes
    -----
    This assumes data is a dictionary and makes standard dict entries
    independent of the type of api request
    """
    if not isinstance(data, dict):
        raise TypeError("Wrong input data type, expected dict")

    specs = {}
    try:
        specs['release_notes'] = data['body']
    except KeyError:
        # No release notes were formalized so link to the
        # CHANGES.rst file that should exist.
        specs['release_notes'] = 'Missing'

    try:
        specs['release_name'] = data['name']
    except KeyError:
        specs['release_name'] = 'N/A'

    try:
        specs['version'] = data['tag_name']
    except KeyError:
        specs['version'] = "Missing"
    try:
        specs['published'] = data['published_at']
    except KeyError:
        specs['published'] = "No Data"
    try:
        specs['website'] = data['html_url']
    except KeyError:
        specs['website'] = 'Missing'
    try:
        specs['author'] = data['author']['login']
    except KeyError:
        specs['author'] = "N/A"
    try:
        specs['author_page'] = data['author']['html_url']
    except KeyError:
        specs['author_page'] = 'N/A'
    return specs


def read_response_file(response=""):
    """Read a JSON response file.

    Parameters
    ----------
    response: string
        name of the json file to read

    Returns
    -------
    The interpreted json file
    """
    if not response:
        raise ValueError("Please specify json file to read")
    with open(response, 'r') as f:
        data = json.load(f)
    return data


def get_all_releases(org="", limit=10, repos=[]):
    """Get the release information for all repositories in an organization.

    Parameters
    ----------
    org: string
        the name of the github organization
    limit: int
        the github response rate limit
    repos: list
        the list of repository dictionaries

    Returns
    -------
    a list of dictionaries with information on each repository
    The github API only returns the first 30 repos by default.
    At most it can return 100 repos at a time. Multiple calls
    need to be made for more.
    """

    if not org:
        raise ValueError("Please supply github organization")

    orgrepo_url = "https://api.github.com/orgs/{0:s}/repos?per_page={1:d}".format(org, limit)
    repos_url = "https://api.github.com/repos/{0:s}/".format(org)
    print("Examining {0:s}....".format(orgrepo_url))

    # Get a list of the repositories, watch rate limiting
    if len(repos) == 0:
        results = get_api_data(url=orgrepo_url)
    else:
        results = []
        for r in repos:
            results.append(get_api_data(url=repos_url + r))

    # This usu means there was a problem
    if 'message' in results:
        print(results)

    # no account for orgs without repos
    if len(results) > 0:
        repo_data = []
        for i in results:
            repo_names = {}
            repo_names['organization'] = org
            repo_names['name'] = i['name']
            repo_names['open_issues'] = i['open_issues']
            repo_names['stars'] = i['stargazers_count']
            try:
                repo_names['license'] = i['license']['spdx_id']
            except TypeError:
                repo_names['license'] = 'None'
            repo_names['forks'] = i['forks_count']
            repo_data.append(repo_names)

    # Loop through all the repositories to get release information
    repo_releases = []
    for rep in repo_data:
        name = rep['name']
        data = check_for_release(repos_url, name)  # returns a list of results
        # expand the release information into separate dicts
        relspecs = get_release_specs(data)
        relspecs['repo_name'] = name
        relspecs['base_url'] = "https://github.com/{0:s}/{1:s}/".format(org, name)
        if relspecs['website'] == 'Missing':
            relspecs['website'] = relspecs['base_url']
        relspecs['open_issues'] = rep['open_issues']
        relspecs['stars'] = rep['stars']
        relspecs['license'] = rep['license']
        relspecs['forks'] = rep['forks']
        relspecs['organization'] = rep['organization']
        repo_releases.append(relspecs)

    return repo_releases


def check_for_release(repos="", name=""):
    """Check for release information, not all repos may have releases.

    Parameters
    ----------
    repos: string
        the url of the repository
    name: string
        the name of the repository

    Returns
    -------
    list of repository information

    Notes
    -----
    Repositories without release information may have tag information
    that is used instead. If no tages or releases information from the
    last commit is used.
    """
    rel_url = repos + ("{0:s}/releases/latest".format(name))
    tags_url = repos + ("{0:s}/tags".format(name))
    commit_url = repos + ("{0:s}/commits".format(name))

    print("Checking latest information for: {0:s}".format(name))

    jdata = get_api_data(url=rel_url)

    # no release information, check tags
    if 'message' in jdata.keys():
        jdata = get_api_data(url=tags_url)
        if 'message' in jdata:
            print(jdata['message'])
            raise ValueError
        if len(jdata) >= 1:
            jdata = jdata.pop(0)  # get the assumed latest
            jdata['html_url'] = jdata['commit']['url']
            jdata['tag_name'] = jdata['name']
            jdata['name'] = name
            more_data = get_api_data(url=jdata['commit']['url'])
            jdata['author'] = {'login': more_data["author"]["login"],
                               'html_url': more_data["author"]["html_url"]}
            jdata['published_at'] = more_data["commit"]["author"]["date"]
        else:
            # not even tag information, get last commit information
            jdata = {'name': name}
            more_data = get_api_data(url=commit_url)
            more_data = more_data.pop(0)
            jdata['author'] = {'login': more_data["author"]["login"],
                               'html_url': more_data["author"]["html_url"]}
            jdata['published_at'] = more_data["commit"]["author"]["date"]

    return jdata


if __name__ == "__main__":
    """Create an example output from the test repository."""

    url = "https://api.github.com/repos/sosey/repo-summary/releases"
    test = get_api_data(url=url)
    specs = get_release_specs(test.pop())  # just send in the one dict
    specs['name'] = 'repo-summary'
    make_summary_page([specs], 'repo-summary.html')
