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
import datetime
import numpy as np
from dateutil import parser
from time import gmtime, strftime
from collections import OrderedDict
from getpass import getpass, GetPassWarning


# some base api urls for reference
_orgrepo_base = "https://api.github.com/orgs/{0:s}/repos?per_page={1:d}type={2:s}"
_repo_base = "https://api.github.com/repos/{0:s}/{1:s}"
_rel_url = _repo_base + ("/releases/latest")  # latest release only
_tags_url = _repo_base + ("/tags")  # tags unordered
_commit_url = _repo_base + ("/commits")  # all commits
_contributors_url = _repo_base + ("/contributors?anon=1")  # contrib sorted by commit
_open_pulls_url = _repo_base + ("/pulls?state=open")
_all_issues_url = _repo_base + ("/issues?state=all&sort=created")

# Non-github addresses
_travis_base = "https://img.shields.io/travis/{0:s}/{1:s}.svg"
_rtd_base = "https://readthedocs.org/projects/{0:s}/badge/?version=latest"
_pulse_month = "https://github.com/{0:s}/{1:s}/pulse/monthly"
_pulse_week = "https://github.com/{0:s}/{1:s}/pulse/weekly"

__repo_stats_key = '.repostats-key'


def get_auth():
    """get authentication information from user read-only file.

    Parameters
    ----------
    None

    Notes
    -----
    The file stores the encryted user information.
    """
    try:
        with open(__repo_stats_key, 'r') as f:
            key = f.read().strip()
        return key
    except FileNotFoundError:
        raise FileNotFoundError("No authorization available, use write_auth()")


def write_auth():
    """Write GitHub token authorization information to local disk.

    Parameters
    ----------
    None

    Notes
    -----
    This attempts to be more secure at using the OAuth
    keys for Github. It will prompt for a username and token
    string and save the encripted string to the users current working
    directory in a readonly file, without displaying the token on the terminal.

    If the token is entered incorrectly, an error will likely be returned when
    the request executes. The user needs to delete the
    password file (.repostats-key) and save a new one using write_auth().
    """

    if os.access(__repo_stats_key, os.F_OK):
            raise IOError("Remove previous file: {0:s}", __repo_stats_key)
    try:
        user = input("Github username:")
        token = getpass(prompt="Github token:")
    except GetPassWarning:
        raise ValueError("Not using PTY-compliant device")

    headers = urllib3.util.make_headers(basic_auth='{}:{}'.format(user, token))
    with open(__repo_stats_key, 'w') as f:
        f.write(headers['authorization'])
    os.chmod(__repo_stats_key, 0o400)


def _get_html_header():
    """Return an HTML header with the appropriate CSS and google api calls.

    Parameters
    ----------
    None

    """
    header = """
        <html>
        <head>
         <title>Made by repostats </title>
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
                background-color: #F0F1F2;
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
                             ("Archived", "string"),
                             ("Astroconda-dev", "string"),
                             ("Astroconda-contrib", "string"),
                             ("Version", "string"),
                             ("Pulse", "string"),
                             ("Release/Tag/Commit--Information", "string"),
                             ("Last Released", "string"),
                             ("Author", "string"),
                             ("Last Commit", "string"),
                             ("Top commits", "string"),
                             ("Contributors", "number"),
                             ("Travis-CI", "string"),
                             ("RTD-latest", "string"),
                             ("Open Issues", "number"),
                             ("Closed Last Week", "number"),
                             ("Closed Last Month", "number"),
                             ("Avg issue time (days)", "number"),
                             ("Open PRs", "number"),
                             ("Commits per week", "number"),
                             ("Commits per month", "number"),
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
        as created by get_repo_info()
    columns: OrderedDict (optional)
        a dictionary of the table column names and their google types
    outpage: string (optional)
        the name of the output html file

    Notes
    -----
    This function is currently meant to work with the default list of colums,
    a new function could be coded to create a page with different columns.
    This one may be edited in the future to be more general. And the
    code dealing with the columns and writing the data to the header
    of the html page could cbe refactoed to handle this.

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

    html_string += ("\ndata.addRows([")
    html.write(html_string)

    # create the table rows for each repository entry
    for repo in repo_data:
        software = repo['name']
        archived = repo['archived']
        url = repo['html_url']
        open_issues = repo['open_issues_count']
        forks = repo['forks_count']
        stars = repo['stargazers_count']

        total_contributors = 0
        if repo['contributors']:
            total_contributors = len(repo['contributors'])
            try:
                top_commits_name1 = repo['contributors'][0]['login']
            except KeyError:
                top_commits_name1 = repo['contributors'][0]['name']
            top_comitts_com1 = repo['contributors'][0]['contributions']

            if (total_contributors > 1):
                try:
                    top_commits_name2 = repo['contributors'][1]['login']
                except KeyError:
                    top_commits_name2 = repo['contributors'][1]['name']
                top_comitts_com2 = repo['contributors'][1]['contributions']
            else:
                top_commits_name2 = 'N/A'
                top_comitts_com2 = 0

        commit_week = 0
        commit_month = 0
        prs = 0
        last_commit = "N/A"
        avg_issue_time = 0

        # record the last commit to the repo
        if (repo['commit_info']):
            last_commit = repo['commit_info']['commit']['author']['date']

        if repo['statistics']:
            closed_last_week = len(repo['statistics']['closed_last_week'])
            closed_last_month = len(repo['statistics']['closed_last_month'])
            avg_issue_time = repo['statistics']['average_issue_time']
            # commits
            if repo['statistics']['weekly_commits']:
                if len(repo['statistics']['weekly_commits']['all']) > 0:
                    commit_week = np.sum(repo['statistics']['weekly_commits']['all'][-1])
                    commit_month = np.sum(repo['statistics']['weekly_commits']['all'][-4])
            # PRs
            if repo['statistics']['open_pulls']:
                prs = len(repo['statistics']['open_pulls'])

        pulse_month = _pulse_month.format(repo['organization'], software)
        pulse_week = _pulse_week.format(repo['organization'], software)
        travis = _travis_base.format(repo['organization'], software)

        # RTD badge
        rtd = scrap_rtd_badge(repo['organization'], software)
        if rtd is None:  # Brute force it
            rtd = _rtd_base.format(software)

        if repo['license'] is None:
            license = "None Found"
        else:
            # Was: repo['license']['spdx_id']
            license = repo['license']['name'].replace('"', "'")

        try:
            astroconda_contrib = repo['astroconda-rel']
            astroconda_dev = repo['astroconda-dev']
        except KeyError:
            astroconda_contrib = 'N/A'
            astroconda_dev = 'N/A'

        # now the variable ones
        if (repo['release_info']):
            rtcname = 'N/A'
            date = 'N/A'
            author = 'N/A'
            author_url = 'N/A'
            descrip = 'N/A'
        else:
            if repo['release_info'] is None:
                if ((repo['tag_info'] is None) or (not repo['tag_info'])):
                    rtcname = "latest commit"
                    if (repo['commit_info']):
                        date = repo['commit_info']['commit']['author']['date']
                        try:
                            author = repo['commit_info']['author']['login']
                        except TypeError:
                            author = repo['commit_info']['commit']['author']['name']
                        author_url = "http://github.com/{0:s}".format(author)
                        descrip = render_html(repo['commit_info']['commit']['message']).strip()
                    else:
                        date = 'N/A'
                        author = 'N/A'
                        author_url = 'N/A'
                        descrip = 'N/A'
                else:
                    rtcname = repo['tag_info'][-1]['name']  # most recent
                    try:
                        date = repo['tag_info'][-1]['commit_info']['commit']['author']['date']
                    except TypeError:
                        date = "N/A"
                    try:
                        author = repo['tag_info'][-1]['commit_info']['author']['login']
                    except:
                        author = "N/A"
                    try:
                        author_url = repo['tag_info'][-1]['commit_info']['author']['html_url']
                    except TypeError:
                        author_url = "http://github.com/{0:s}".format(author)
                    descrip = render_html(repo['tag_info'][-1]['commit_info']['commit']['message'])

            else:
                rtcname = repo['release_info']['name']
                date = repo['release_info']['created_at']
                author = repo['release_info']['author']['login']
                author_url = repo['release_info']['author']['html_url']
                descrip = render_html(repo['release_info']['body'])

        html_string = ("[\'<a href=\"{}\">{}</a>\',"
                       "\"{}\","
                       "\"{}\","
                       "\"{}\","
                       "\"{}\","
                       "\'<a href=\"{}\">{}</a><br><br>"
                       "<a href=\"{}\">{}</a>\',"
                       "{}{}{},"
                       "\"{}\","
                       "\'<a href=\"{}\">{}</a>\',"
                       "\"{}\","
                       "\'{}: {}<br>"
                       "{}: {}\',"
                       "{},"
                       "\'<img src=\"{}\">\',\'<img src=\"{}\">\',"
                       "{},{},{},"
                       "{},{},{},{},"
                       "{},{},\"{}\"],\n".format(url, software,
                                           archived,
                                           astroconda_contrib,
                                           astroconda_dev,
                                           rtcname,
                                           pulse_month, "Month Stats",
                                           pulse_week, "Week Stats",
                                           chr(96), descrip, chr(96),
                                           date,
                                           author_url, author,
                                           last_commit,
                                           top_commits_name1, top_comitts_com1,
                                           top_commits_name2, top_comitts_com2,
                                           total_contributors,
                                           travis, rtd,
                                           open_issues, closed_last_week, closed_last_month,
                                           avg_issue_time, prs, commit_week, commit_month,
                                           forks, stars, license))
        html.write(html_string)

    page = '''  ]);

    var table = new google.visualization.Table(document.getElementById("table_div"));
    table.draw(data, {showRowNumber: true, allowHtml: true, frozenColumns: 1,
                      cssClassNames: cssClassNames, height: "500px"});
    }
    </script>
    </head>
    <body>
    <p align="center" size=10pt><strong>Click on the column header name to sort by that column </strong></p>
    <br>
    <p align="left" size=10pt>
    <ul>
    <li>If there hasn't been any github release or tag  then the information is taken from the last commit to that repository
    <li>The issues count includes PRs becuase the API doesn't separate them, the avg open issue time has been corrected for this.
    <li>Top contributors are listed for maintenance reference, no relation to quality or size of commits
    <li>RTD-latest: guesses that the docs are named in RTD using the package name, 'unknown', most likely means the RTD docs, if they exist, are not using the GitHub package name
    </ul>
    </p><br>
    Last Updated: '''

    page += ("{0:s} GMT<br><br> <div id='table_div'></div>\n</body></html>".format(strftime("%a, %d %b %Y %H:%M:%S", gmtime())))
    html.write(page)
    html.close()
    print("Created {0:s}".format(outpage))


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
        The url for query

    Returns
    -------
    Returns a json payload response or None if it wasn't successful
    """
    headers = {'User-Agent': 'repostats-tool',
               'Accept': 'application/vnd.github.v3+json'}

    # limit read of the auth file
    if 'Authorization' not in headers.keys():
        try:
            headers['Authorization'] = get_auth()
        except FileNotFoundError:
            write_auth()
            headers['Authorization'] = get_auth()

    urllib3.contrib.pyopenssl.inject_into_urllib3()
    http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',
                               ca_certs=certifi.where())
    try:
        response = http.request('GET', url, headers=headers, retries=False)
    except urllib3.exceptions.NewConnectionError:
        raise OSError('Connection to GitHub failed.')

    resp_header = response.getheaders()
    try:
        status = resp_header['status']
        if '200' not in status:
            if '409 Conflict' in status:
                print("Conflict, empty repository")
            return None
        else:
            data = json.loads(response.data.decode('iso-8859-1'))
            # deal with pagination
            if 'Link' in resp_header.keys():
                links = response.getheaders()['Link'].split(',')
                if links:
                    next_url = links[0].split(";")[0].strip()[1:-2]
                    total = int(links[1].split(";")[0].strip()[-2]) + 1
                    for i in range(2, total, 1):
                        url = next_url + str(i)
                        response = http.request('GET', url, headers=headers, retries=False)
                        data += json.loads(response.data.decode('iso-8859-1'))
            return data
    except KeyError:
        for k,v in resp_header:
            print(k,v)
        return None


def get_statistics(org="", name=""):
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
    weekly_commits = (_repo_base.format(org, name)) + "stats/participation"

    # empty = b'{"all":[],"owner":[]}'
    response = get_api_data(weekly_commits)
    stats = {'weekly_commits': response}

    # get pull requests that are still open
    open_pulls = _open_pulls_url.format(org, name)
    response = get_api_data(open_pulls)
    stats['open_pulls'] = response

    # information on all open issues
    all_issues = _all_issues_url.format(org, name)
    response = get_api_data(all_issues)
    stats['all_issues'] = response

    find_closed_issues(stats)

    return stats


def find_closed_issues(stats=None):
    """calculated closed issue information.

    Parameters
    ----------
    stats: dict
        dictionary of stats
    """

    if not isinstance(stats, dict):
        raise TypeError("Expected stats to be a dictionary")

    try:
        all_issues = stats['all_issues']
    except:
        KeyError("Dictionary missing all_issues entry")

    closed = [i for i in all_issues if i['state'] == 'closed']
    stats['closed_issues_count'] = len(closed)

    # The endpoint may also return pull requests in the response.
    # If an issue is a pull request, the object will include a pull_request key.
    avg_time = 0.
    times = 0.
    icount = 0.
    days = 3600. * 24.
    for i in closed:
        try:
            i['pull_request']
        except KeyError:
            created = parser.parse(i['created_at'])
            resolved = parser.parse(i['closed_at'])
            times += (resolved - created).total_seconds()
            icount += 1
    if icount:
        avg_time = times / (days * icount)
    stats['average_issue_time'] = avg_time  # in days

    # calculate the number of issues closed in the last week and month
    stats['closed_last_week'] = 0
    stats['closed_last_month'] = 0

    now = datetime.datetime.now(datetime.timezone.utc)
    delta_week = now - datetime.timedelta(7)  # last_week = now - 7 days
    delta_30 = now - datetime.timedelta(30)
    closed_last_week = [i for i in closed if parser.parse(i['closed_at']) > delta_week]
    closed_last_30 = [i for i in closed if parser.parse(i['closed_at']) > delta_30]
    stats['closed_last_week'] = closed_last_week
    stats['closed_last_month'] = closed_last_30


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
    if stats['weekly_commits']:
        last_week = np.sum(stats['weekly_commits']['all'][-1])
        last_month = np.sum(stats['weekly_commits']['all'][-4])
    else:
        last_week = 0
        last_month = 0

    # PRs
    if stats['open_pulls']:
        prs = len(stats['open_pulls'])
    else:
        prs = 0

    # open issues
    open_issues = len([i for i in stats['all_issues'] if i['state'] == 'open'])
    closed_last_week = len(stats['closed_last_week'])
    closed_last_month = len(stats['closed_last_month'])

    # print to screen
    if stats['all_issues']:
        print("\nReport for {0:s}".format(': '.join(stats['all_issues'][0]['repository_url'].split("/")[-2:])))
        print("Open issues: {:3}\n"
              "Closed issues this week: {:3}\n"
              "Closed issues this month: {:3}\n"
              "Commits in last week: {:3}\n"
              "Commits in last month: {:3}\n".format(open_issues,
                                                     closed_last_week,
                                                     closed_last_month,
                                                     last_week, last_month))
        if prs > 0:
            print("Open Pull Requests: {:3}\n".format(prs))
            print("{:<7}{:<70}{:<22}{:22}".format("Number", "Title", "Created", "Last Updated"))
            for opr in stats['open_pulls']:
                print("{:<7}{:<70}{:<22}{:22}".format(opr['number'], opr['title'],
                                                      opr['created_at'], opr['updated_at']))
        else:
            print("No open pull requests")
    else:
        print("No stats available")


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


def date_handler(obj):
    """make datetime object json serializable.

    Notes
    -----
    Taken from here: https://tinyurl.com/yd84fqlw
    """
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        raise TypeError


def write_response_file(data=None, filename=None):
    """Write a json response out to file.

    Parameters
    ----------
    filename: string
        The name of the json file to write to disk
    """
    if filename is None:
        filename = "git_response.json"

    if ((data is None) or (not isinstance(data, list))):
        raise TypeError("Expected data to be a list")

    with open(filename, 'w') as f:
        json.dump(data, f, default=date_handler)
    os.chmod(filename, 0o400)


def get_all_repositories(org="", limit=10, pub_only=True):
    """Return a list of repositories in the organization.

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
        rtype = "all"  # public and private

    if limit > 100:
        limit = 100  # max supported

    print("Getting list of {0:s} repos for {1:s}...".format(rtype, org))
    url = _orgrepo_base.format(org, limit, rtype)
    results = get_api_data(url=url)
    if results is None:
        raise ValueError("No repositories found")

    names = []
    for repo in results:
        names.append(repo['name'])
    return names


def _chunk_list(listname=None, size=None):
    """return the list in chunks of size."""
    for i in range(0, len(listname), size):
        yield listname[i:i + size]


def get_repo_info(org="", limit=10, repos=None, pub_only=True,
                  astroconda=True):
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
    if not org:
        raise ValueError("Please supply the name of a GitHub organization")

    # Get a list of the repositories
    if limit > 100:
        limit = 100  # max allowed
    if (repos is None):
        repos = get_all_repositories(org, limit=limit, pub_only=pub_only)
    else:
        if not isinstance(repos, list):
            raise TypeError("Expected repos to be list")

    print("Found {0} repositories".format(len(repos)))

    # get summary information for each repo
    repo_data = []
    for r in repos:
        repdata = get_api_data(_repo_base.format(org, r))
        repdata['organization'] = org
        repo_data.append(repdata)

    # speed up the large querry
    for repo in repo_data:
        print(repo['name'])
        _querry_for_info(org, repo)

    if astroconda:
        astro_dev = get_astroconda_list(flavor='dev')
        astro_contrib = get_astroconda_list(flavor='contrib')
        for repo in repo_data:
            repo['astroconda-dev'] = str(get_astroconda_membership(repo['name'], astro_dev))
            repo['astroconda-rel'] = str(get_astroconda_membership(repo['name'], astro_contrib))

    return repo_data


def _querry_for_info(org=None, repo=None):
    """Make querries for more information on the summary repo_data.

    Parameters
    ----------
    repo_data: list[dicts]
        A list of repositories with basic information. The repo
        dictionariers are updated with the additional information.

    Notes
    -----
    Reconsider updating the dictionaries like this if the
    returned information becomes large.
    """
    if org is None:
        raise ValueError("Need name of organization")
    repo['release_info'] = check_for_release(org=org, name=repo['name'], latest=True)
    repo['tag_info'] = check_for_tags(org=org, name=repo['name'])
    repo['commit_info'] = check_for_commits(org=org, name=repo['name'], latest=True)
    repo['statistics'] = get_statistics(org=org, name=repo['name'])
    repo['contributors'] = get_contributors(org=org, name=repo['name'])


def get_contributors(org=None, name=None):
    """return the list of contributors in descending order.

    Parameters
    ----------
    org: string
        The name of the organization
    name: string
        The name of the repository

    Returns
    -------
    List of contributors, ranked in descending order by number of commits
    """
    if ((org is None) or (name is None)):
        raise TypeError("Need strings for org and repository name")

    url = _contributors_url.format(org, name)
    return get_api_data(url)


def check_for_tags(url=None, org=None, name=None):
    """Check for tag information, not alll repos may have tags.

    Parameters
    ----------
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

    Parameters
    ----------
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

    results = get_api_data(commit_url)
    if latest and results is not None:
        return results[0]
    else:
        return results


def check_for_release(url=None, org=None, name=None, latest=True):
    """Check for release information, not all repos may have releases.

    Parameters
    ----------
    repos_url: string
        the url of the repos release api
    name: string
        the name of the repository
    latest: bool
        return the latest release

    Returns
    -------
    list of release information if latest is False

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
        if latest:
            rel_url += "/latest"
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

    Parameters
    ----------
    ld_name: list[dict]
        list of dictionaries
    keyname: str
        dictionary key to use for sorting
    """
    if (ld_name is None or not isinstance(ld_name, list)):
        raise TypeError("Expected list of dictionaries")
    return sorted(ld_name, key=lambda k: k[keyname])


def get_astroconda_list(flavor="dev"):
    """return the list of astroconda packages.

    Parameters
    ----------
    flavor: string
        The sub type of astroconda distribution
    """
    if flavor not in ["dev", "contrib"]:
        raise ValueError("Only dev and contrib flavors currently exist")

    astroconda_url = "https://api.github.com/repos/astroconda/astroconda-{0:s}/contents".format(flavor)

    # Get the list of packages, which is just the directory listing for astroconda
    return get_api_data(astroconda_url)


def get_astroconda_membership(name="", data=""):
    """Return whether the repo is a member of the named astroconda release.

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


def scrap_rtd_badge(repoorg, reponame):
    import base64
    import re

    content = None
    badge = None

    # TODO: Add more possibilities as needed.
    readme_files = ('README', 'README.md', 'README.rst', 'README.txt')

    for filename in readme_files:
        url = (_repo_base.format(repoorg, reponame) +
               '/contents/{}'.format(filename))
        try:
            json = get_api_data(url)
            if json is not None:
                content = base64.b64decode(json['content']).decode('utf-8')
        except Exception:
            pass
        else:
            if content is not None:
                break

    if content is None:
        return badge

    # Regex magic by Craig Jones.
    m = re.search('(http[s]:\/\/readthedocs.*version=[\w]+)', content)
    if m is None:
        return badge
    badge = m.group(0)

    return badge


if __name__ == "__main__":
    """Create an example output from the test repository."""

    org = 'spacetelescope'
    name = 'PyFITS'
    stats = get_statistics(org=org, name=name)
    print_text_summary(stats)

    repos = [name, 'synphot_refactor', 'asdf', 'stginga']
    repo_data = get_repo_info(
        org=org, repos=repos, pub_only=True, astroconda=True)
    make_summary_page(repo_data)
