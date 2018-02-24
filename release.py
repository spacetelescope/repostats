"""
Library for gleaning information from GitHub through APIv3
This tool currently requires the use of an OAuth token
"""

from __future__ import print_function, division, absolute_import

import os
import json
import mistune
import urllib3
import urllib3.contrib.pyopenssl
import certifi
import numpy as np
from dateutil import parser
from time import gmtime, strftime
from collections import OrderedDict
from getpass import getpass, GetPassWarning


# some base api urls for reference
_org_base = "https://api.github.com/repos/{0:s}/"
_repo_base = _org_base + ("{1:s}")
_rel_url = _org_base + ("{1:s}/releases/latest")  # latest release only
_tags_url = _org_base + ("{1:s}/tags")  # tags unordered
_commit_url = _org_base + ("{1:s}/commits")  # all commits
_travis_base = "https://img.shields.io/travis/{0:s}/{1:s}.svg"
_rtd_base = "https://readthedocs.org/projects/{0:s}/badge/?version=latest"
_pulse_month = "https://github.com/{0:s}/{1:s}/pulse/monthly"
_pulse_week = "https://github.com/{0:s}/{1:s}/pulse/weekly"


def get_auth():
    """get authentication information from user read-only file.

    Notes
    -----
    The file stores the b64 hashed information
    """
    filename = '.repo-summary-key'
    try:
        with open(filename, 'r') as f:
            key = f.read().strip()
        return key
    except FileNotFoundError:
        raise FileNotFoundError("No authorization available, use write_auth()")


def write_auth():
    """Write authorization information to local disk.

    Notes
    -----
    This attempts to be more secure at using the OAuth
    keys for Github. It will prompt for a username and token
    string and save the b64 encripted string to the users cwd
    in a readonly file without displaying the token on the terminal
    """

    filename = '.repo-summary-key'
    try:
        user = input("Github username:")
        token = getpass(prompt="Github token:")
    except GetPassWarning:
        raise ValueError("Not using PTY-compliant device")

    headers = urllib3.util.make_headers(basic_auth='{}:{}'.format(user, token))
    with open(filename, 'w') as f:
        f.write(headers['authorization'])
    os.chmod(filename, 400)


def _get_html_header():
    """return the html header"""
    header = """
        <html>
        <head>
         <title>Made by repo-summary </title>
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

        </script>
        """
    return header


def _set_table_column_names(names=None):
    """Define the table data columns to use in the html header.

    Parameters
    ----------
    names: collections.OrderedDict
        The dictionary of string column header names and their types
        Their types are the accepted google types
    """
    if (not isinstance(names, (OrderedDict)) and names is not None):
        raise TypeError("Expected names to be an OrderedDict")

    if names is None:
        names = OrderedDict([("Package Name", "string"),
                             ("Astroconda-dev", "string"),
                             ("Version", "string"),
                             ("Pulse", "string"),
                             ("Release Information", "string"),
                             ("Last Released", "string"),
                             ("Author", "string"),
                             ("Travis-CI", "string"),
                             ("RTD-latest", "string"),
                             ("Open Issues", "number"),
                             ("Forks", "number"),
                             ("Stars", "number"),
                             ("License", "string")])
    return names


def make_summary_page(repo_data=None, columns=None, outpage=None):
    """Make a summary HTML page from a list of repositories in the organization.

    Parameters
    ----------
    repo_data: list[dict{}]
        a list of dictionaries that contains information about each repository
    columns: OrderedDict (optional)
        a dictionary of the table column names and their google types
    outpage: string (optional)
        the name of the output html file

    """
    if not isinstance(repo_data, list):
        raise TypeError("Expected data to be a list of dictionaries")

    if outpage is None:
        outpage = "repository_summary.html"

    if ((not isinstance(columns, OrderedDict)) or (columns is None)):
        columns = _set_table_column_names()

    # print to a web page we can display for ourselves,
    print("Checking for older html file before writing {0:s}".format(outpage))
    if os.access(outpage, os.F_OK):
        os.remove(outpage)
    html = open(outpage, 'w')

    # write the basic header that the page needs
    html.write(_get_html_header())

    # this section includes the javascript code and google calls for the
    # interactive features (table and sorting)
    html_string = """

        <script type="text/javascript">
          google.load("visualization", "1", {packages:["table"]});
          google.setOnLoadCallback(drawTable);
          function drawTable() {
            var data = new google.visualization.DataTable();

        """

    for k, v in columns.items():
        html_string += ('\t\tdata.addColumn(\"{0}\", \"{1}\");\n'.format(v, k))

    html_string += "data.addRows(["
    html.write(html_string)

    # create the table rows for each repository entry
    for repo in repo_data:
        software = repo['name']

        if repo['release_name'] is None:
            if repo['tag_name'] is None:
                rtcname = 'None'
            else:
                rtcname = repo['tag_name']
        else:
            rtcname = repo['release_name']
            if repo['release_notes'] is not None:
                descrip = render_html(repo['release_notes'])
            else:
                file_url = "{0:s}/blob/master/CHANGES.rst".format(repo['base_url'])
                response = get_api_data(file_url)
                if response.status == 200:
                    descrip = ("\'<a href=\"{0:s}\">Link to package CHANGES</a>\'".format(file_url))
                else:
                    descrip = ("No CHANGES file or release notes available")

        url = repo['base_url']
        date = repo['date']
        author = repo['author']
        author_url = repo['author_url']
        if author_url is None:
            author_url = repo['base_url']
        issues = repo['open_issues']
        forks = repo['forks']
        stars = repo['stars']
        license = repo['license']
        astroconda = repo['astroconda']
        travis = _travis_base.format(repo['organization'], software)
        rtd = _rtd_base.format(software)
        pulse_month = _pulse_month.format(repo['organization'], software)
        pulse_week = _pulse_week.format(repo['organization'], software)

        html.write("[\'<a href=\"{}\">{}</a>\',"
                   "\"{}\","
                   "\"{}\","
                   "\'<a href=\"{}\">{}</a><br><br>"
                   "<a href=\"{}\">{}</a>\',"
                   "{},{},{},"
                   "\"{}\","
                   "\'<a href=\"{}\">{}</a>\',"
                   "\'<img src=\"{}\">\',\'<img src=\"{}\">\',"
                   "{},{},{},"
                   "\"{}\"],\n".format(url, software,
                                       astroconda,
                                       rtcname,
                                       pulse_month, "Month Stats",
                                       pulse_week, "Week Stats",
                                       chr(96), descrip, chr(96),
                                       date,
                                       author_url, author,
                                       travis, rtd,
                                       issues, forks, stars,
                                       license))

    page = '''  ]);

    var table = new google.visualization.Table(document.getElementById("table_div"));
    table.draw(data, {showRowNumber: true, allowHtml: true, cssClassNames: cssClassNames,});
    }
    </script>
    </head>
    <body>
    <br><p align="center" size=10pt>Click on the column header name to sort by that column </p>
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
    The translated markdown -> html 
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
    headers = {'User-Agent': 'repo-summary-tool'}
    headers['Authorization'] = get_auth()
    urllib3.contrib.pyopenssl.inject_into_urllib3()
    http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',
                               ca_certs=certifi.where())
    try:
        response = http.request('GET', url, headers=headers, retries=False)
    except urllib3.exceptions.NewConnectionError:
        raise OSError('Connection to GitHub failed.')

    # print(response.status)
    # if response.status != 200:
    #    message = ("status: {0}\nRate limiting in effect\n"
    #               "message: {1}\n"
    #               "responses remaining: {2} of {3}".format(response.status,
    #                                                        response.message,
    #                                                        response.headers['X-RateLimit-Remaining'],
    #                                                        response.headers['X-RateLimit-Limit']))
    #    raise ValueError(message)
    if 'message' in response.getheaders().keys():
        return None
    else:
        return json.loads(response.data.decode('iso-8859-1'))


def get_statistics(org="", repo=""):
    """Get pulse statistics for the repository.

    Parameters
    ----------
    org: string
        The name of the organization
    repo: string
        The name of the repository

    Notes
    -----
    The returned dictionary can be used to create any reports the user wants
    See print_text_stats() to print a simple text report to the screen
    """
    # weekly commits for the whole year
    weekly_commits = "https://api.github.com/repos/{0:s}/{1:s}/stats/participation".format(org, repo)
    response = get_api_data(weekly_commits)
    stats = {'weekly_commits': response}

    # get pull requests that are still open
    open_pulls = "https://api.github.com/repos/{0:s}/{1:s}/pulls?state=open".format(org, repo)
    response = get_api_data(open_pulls)
    stats['open_pulls'] = response

    # information on all issues regardless of state
    all_issues = "https://api.github.com/repos/{0:s}/{1:s}/issues?state=all".format(org, repo)
    response = get_api_data(all_issues)
    stats['all_issues'] = response

    return stats


def print_text_summary(stats=None):
    """Print a text report from the dict created by get_statistics.

    Parameters
    ----------
    stats: dict
        dictionary of stats created by get_statistics()
    """
    if ((stats is None) or not isinstance(stats, dict)):
        raise TypeError("Expected stats to be a dictionary")

    # commits
    last_week = np.sum(stats['weekly_commits']['all'][-1])
    last_month = np.sum(stats['weekly_commits']['all'][-4])

    # PRs
    prs = len(stats['open_pulls'])

    # open issues
    open_issues = [i for i in stats['all_issues'] if i['state'] == 'open']
    oi = len(open_issues)

    # print to screen
    print("\nReport for {0:s}".format(': '.join(stats['all_issues'][0]['repository_url'].split("/")[-2:])))
    print("Open issues: {:3}\n"
          "Commits in last week: {:3}\n"
          "Commits in last month: {:3}\n".format(oi, last_week, last_month))
    if prs > 0:
        print("Open Pull Requests: {:3}\n".format(prs))
        print("{:<7}{:<70}{:<22}{:22}".format("Number", "Title", "Created", "Last Updated"))
        for opr in stats['open_pulls']:
            print("{:<7}{:<70}{:<22}{:22}".format(opr['number'], opr['title'], opr['created_at'], opr['updated_at']))
    else:
        print("No open pull requests")


def normalize_repo_specs(data=None):
    """Normalize the collected repository information

    Parameters
    ----------
    data: dict
        The dictionary of repository information as created by
        the get_repo_info function

    Notes
    -----
    This assumes data is a dictionary and makes standard dict entries
    independent of the type of api request
    """
    if ((data is None) or (not isinstance(data, dict))):
        raise TypeError("Wrong input data type, expected dict")

    specs = {}
    try:
        specs['release_notes'] = data['body']
    except KeyError:
        # No release notes were formalized so link to the
        # CHANGES.rst file that should exist.
        specs['release_notes'] = None

    try:
        specs['release_name'] = data['release_name']
    except KeyError:
        specs['release_name'] = None

    try:
        specs['tag_name'] = data['tag_name']
    except KeyError:
        specs['tag_name'] = None
    try:
        specs['date'] = data['published_at']
    except KeyError:
        specs['date'] = None
    try:
        specs['website'] = data['html_url']
    except KeyError:
        specs['website'] = None
    try:
        specs['author'] = data['author']['login']
    except KeyError:
        specs['author'] = "N/A"
    try:
        specs['author_url'] = data['author']['html_url']
    except KeyError:
        specs['author_url'] = None
    return specs


def read_response_file(filename=None):
    """Read a JSON response file.

    Parameters
    ----------
    response: string
        name of the json file to read

    Returns
    -------
    The interpreted json file. This may be useful later for storing response files with lots
    of data locally, so that they can be analyzed later by multiple sources
    """
    if filename is None:
        raise ValueError("Please specify json file to read")

    with open(filename, 'r') as f:
        data = json.load(f)
    return data


def write_response_file(data=None, filename=None):
    """Write a json response out to file.

    Parameters
    ----------
    filename: string
        The name of the json file to write to disk
    """
    if filename is None:
        filename = "git_response.json"

    if ((data is None) or (not isinstance(data, dict))):
        raise TypeError("Expected data to be a dictionary")
    with open(filename, 'w') as f:
        json.dump(data, f)


def get_all_repositories(org="", limit=10, pub_only=True):
    """Return the list of repositories in the organization.

    Parameters
    ----------
    org: string
        The name of the organization
    pub_only: bool
        If False, then the private repositories are also returned

    Notes
    -----
    Limiting the type of repo to returns helps users not
    accidentally display private org information publicly
    """
    if pub_only:
        rtype = "public"
    else:
        rtype = "all"

    print("Getting list of all {0:s} for {1:s}...".format(rtype, org))
    orgrepo_url = "https://api.github.com/orgs/{0:s}/repos?per_page={1:d}type={2:s}".format(org,
                                                                                            limit,
                                                                                            rtype)
    results = get_api_data(url=orgrepo_url)
    if results is None:
        raise ValueError("No repositories found")
    names = []
    for repo in results:
        names.append(repo['name'])
    return names


def get_repo_info(org="", limit=10, repos=None, pub_only=True,
                  astroconda=True, astroconda_flavor="dev"):
    """Get the release information for all repositories in an organization.

    Parameters
    ----------
    org: string
        the name of the github organization
    limit: int
        the github response rate limit
    repos: list
        the list of repositories to search, this will only
        return results for the repositories listed
    pub_only: bool
        If False, then the private repositories are also returned
    astroconda: bool
        Check for repo membership in astroconda distribution
    astroconda_flavor: string
        Check this flavor of dist (either dev or release)

    Returns
    -------
    a list of dictionaries with information on each repository
    The github API only returns the first 30 repos by default.
    At most it can return 100 repos at a time. Multiple calls
    need to be made for more. Some of the api entrants ignore
    the per_page directive though which is set using the limit parameter.

    Notes
    -----
    Limiting the type of repo to return helps users not
    accidentally display private org information publicly
    """
    flavors = ["dev", "release"]

    if not org:
        raise ValueError("Please supply the name of a GitHub organization")

    # Get a list of the repositories
    if ((repos is None) or (not isinstance(repos, list))):
        repos = get_all_repositories(org, limit=limit, pub_only=pub_only)

    repo_data = []
    for r in repos:
        repo_data.append(get_api_data(_repo_base.format(org, r)))

    if repo_data:
        print("Found {0} repositories".format(len(repo_data)))
        for repo in repo_data:
            repo['organization'] = org
            if astroconda:
                if astroconda_flavor not in flavors:
                    raise ValueError("No astroconda-{0:s} distribution".format(astroconda_flavor))
                else:
                    repo['astroconda'] = str(get_astroconda_membership(repo['name'],
                                                                       get_astroconda_list()))
            repo['release_info'] = check_for_release(org=org, name=repo['name'])
            repo['tag_info'] = check_for_tags(url=repo['tags_url'])
            # if there were no tags in the repository, get the latest commit information
            if not repo['tag_info']:
                repo['commit_info'] = check_for_commits(org=org, name=repo['name'], latest=True)
    else:
        raise ValueError("No repositories found")

    return repo_data


def check_for_tags(url=None, org=None, name=None):
    """Check for tag information, not alll repos may have tags.

    Paramters
    ---------
    tags_url: string
        url for the tags api
    name: string
        The name of the repository, use if calling this function by itself
    """
    if url is None:
        if (org is None):
            raise ValueError("Expected organziation name")
        if (name is None):
            raise ValueError("Expected repository name")
        tags_url = _tags_url.format(org, name)
    else:
        tags_url = url

    tags_data = get_api_data(url=tags_url)

    if tags_data:
        # sort the tags by date to be nice
        tags_data = _update_tags_with_commits(tags_data, sort_data=True, keyname='datetime')

    return tags_data


def check_for_commits(url=None, name=None, org=None, latest=True):
    """Check for commit information.

    Paramters
    ---------
    commmit_url: string
        url for the tags api
    name: string
        The name of the repository, use if calling this function by itself
    org: string
        The name of the organization
    latest: bool
        Just return the latest commit, otherwise return all commits.
        If False, it will return by default the last 30 commits
    """
    if url is None:
        if (org is None):
            raise ValueError("Expected organziation name")
        if (name is None):
            raise ValueError("Expected repository name")
        commit_url = _commit_url.format(org, name)
    else:
        commit_url = url

    if latest:
        commit_url += "/master"

    return get_api_data(commit_url)


def check_for_release(url=None, org=None, name=None):
    """Check for release information, not all repos may have releases.

    Parameters
    ----------
    repos_url: string
        the url of the repos api
    name: string
        the name of the repository

    Returns
    -------
    list of relese information

    Notes
    -----
    Repositories without release information may have tag information
    that is used instead. If no tags or releases exist then information from the
    last commit is used.
    """
    if url is None:
        if (org is None):
            raise ValueError("Expected organziation name")
        if (name is None):
            raise ValueError("Expected repository name")
        rel_url = _rel_url.format(org, name)
    else:
        rel_url = url

    # print("Checking release information for:\n{0:s}".format(rel_url))

    # get a json payload return or empty list
    return get_api_data(url=rel_url)


def _update_tags_with_commits(tags_data=None, sort_data=False, keyname='datetime',
                              print_summary=False):
    """ Update the tag dictionary with commit information.

    Parameters
    ----------
    tags_data: list[dict]
        list of dictionaries with tag information
    sort_data: bool
        True will sort the return list by the key value
    key: str
        dictionary key value to use for sorting the returned list
    print_summary: bool
        True will print out a summary of tag, date as it goes

    Returns
    -------
    List of dictionaries with added information

    Notes
    -----
    The tag data contain basic commit information, but not dates or authors
    and is unordered. This gets information from the commit for the tag and
    adds it to the input dictionary along with creating a new date key for
    easy sorting.

    """
    if ((tags_data is None) or (not isinstance(tags_data, (list)))):
        raise TypeError("Expected tags data to be a list of dictionaries")

    # get the commit information for all tages
    for tag in tags_data:
        tag['commit_info'] = get_api_data(tag['commit']['url'])
        tag['date'] = tag['commit_info']['commit']['author']['date']
        tag['datetime'] = parser.parse(tag['date'])

        if print_summary:
            print(tag['name'], tag['date'])

    if sort_data:
        if keyname not in tags_data[0].keys():
            raise KeyError("Key not found")
        tags_data = sorted(tags_data, key=lambda k: k[keyname])

    return tags_data


def _sort_list_dict_by(ld_name=None, keyname=None):
    """sort a list of dictionaries by key.

    Paramters
    ---------
    ld_name: list[dict]
        list of dictionaries
    keyname: str
        dictionary key to use for sorting
    """
    if (ld_name is None or not isinstance(ld_name, list)):
        raise TypeError("Expected list of dictionaries")
    return sorted(ld_name, key=lambda k: k[keyname])


def get_astroconda_list(flavor="dev"):
    """return the list of astroconda packages."""
    if flavor not in ["dev", "release"]:
        raise ValueError("Only dev and release flavors exist")

    astroconda_url = "https://api.github.com/repos/astroconda/astroconda-{0:s}/contents".format(flavor)

    # Get the list of packages, which is just the directory listing for astroconda
    return get_api_data(astroconda_url)


def get_astroconda_membership(name="", data=""):
    """Return whether the repo is a member of the astroconda release.

    Parameters
    ----------
    name: string
        name of the repository
    data: list
        The list of the packages in astroconda repository

    Returns
    -------
    status: boolean
        True if the repository is included in astroconda-dev

    Notes
    -----
    Done this way so that the call to get the list can be made separately
    from the membership decision.

    Based on the return results for the contents entry
    """
    for item in data:
        if (item['html_url'].split("/")[-1] == name):
            return True
    return False


if __name__ == "__main__":
    """Create an example output from the test repository."""

    url = "https://api.github.com/repos/sosey/repo-summary/releases"
    test = get_api_data(url=url)
    specs = normalize_repo_specs(test.pop())  # just send in the one dict
    specs['name'] = 'repo-summary'
    make_summary_page([specs], 'repo-summary.html')
