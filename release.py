"""
Get the package release information for a specific organization

# SSLError: Can't connect to HTTPS URL because the SSL module is not available.
# using pycurl for now as an example
"""

import json
import mistune
import os
import pycurl
from io import BytesIO
import urllib3
import urllib3.contrib.pyopenssl
import certifi
from time import gmtime, strftime


def make_summary_page(data=[], outpage=""):
    """Make a summary HTML page from a list of repos with release information.

    Data should be a list of dictionaries
    """
    urllib3.contrib.pyopenssl.inject_into_urllib3()
    http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())

    if not isinstance(data, list):
        raise TypeError("Expected data to be a list of dictionaries")
    if not outpage:
        outpage = ("repository_summary.html")
    print("Saving to {0:s}".format(outpage))

    # print them to a web page we can display for ourselves,
    print("Checking for older html file before writing {0:s}".format(outpage))
    if os.access(outpage, os.F_OK):
        os.remove(outpage)
    html = open(outpage, 'w')

    # this section includes the javascript code and google calls for the
    # interactive features (table sorting)

    header = '''
    <html>
      <head>  <title>Github Organization Package Summary Information </title>
       <meta charset="utf-8">
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
            data.addColumn("number", "Open Issues");
            data.addColumn("number", "Forks");
            data.addColumn("number", "Watchers");
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
        watchers = repo['watchers']
        license = repo['license']

        html.write("[\"{}\",\"{}\",\'<a href=\"{}\">{}</a>\',{}{}{},\"{}\",\'<a href=\"{}\">{}</a>\',{},{},{},\"{}\"],\n".format(
                    software, version, website, "Code Repository", chr(96), descrip, chr(96), date, author_page, author,
                    issues, forks, watchers, license))

    page = '''  ]);
    var table = new google.visualization.Table(document.getElementById("table_div"));
    table.draw(data, {showRowNumber: true, allowHtml: true});
    }
    </script>
    </head>
    <body><br>
    <br><p align="center" size=10pt>Click on the column fields to sort </p>
    <br><br>
    <p align="left">
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
    """Turn markdown string into beautiful soup structure."""
    if not md:
        return ValueError("Supply a string with markdown")
    m = mistune.markdown(md)
    return m


def get_api_data(url=""):
    """Return the JSON load from the request."""
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()
    res = buffer.getvalue().decode('iso-8859-1')
    return json.loads(res)  # list of dicts


def get_release_specs(data=None):
    """parse out the release information from the json object.

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
    """Read a JSON response file."""
    if not response:
        raise ValueError("Please specify json file to read")
    with open(response, 'r') as f:
        data = json.load(f)
    return data


def get_all_releases(org="", limit=10, repos=[]):
    """Get the release information for all repositories in an organization.

    Returns a list of dictionaries with information on each repository
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
            results.append(get_api_data(url=repos_url+r))

    # This usu means there was a problem
    if 'message' in results:
        print(results)

    # no account for orgs without repos
    if len(results) > 0:
        repo_data = []
        for i in results:
            repo_names = {}
            repo_names['name'] = i['name']
            repo_names['open_issues'] = i['open_issues']
            repo_names['watchers'] = i['watchers_count']
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
        relspecs['watchers'] = rep['watchers']
        relspecs['license'] = rep['license']
        relspecs['forks'] = rep['forks']
        repo_releases.append(relspecs)

    return repo_releases


def check_for_release(repos="", name=""):
    """Check for release information, not all repos may have releases.

    Repositories without release information may have tag information
    that is used instead. If no tages or releases information from the
    last commit is used.
    """
    rel_url = repos + ("{0:s}/releases/latest".format(name))
    tags_url = repos + ("{0:s}/tags".format(name))
    commit_url = repos + ("{0:s}/commits".format(name))

    print("Checking latest information for: {0:s}".format(name))

    jdata = get_api_data(url=rel_url)

    # no release information ,check tags
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
    """Create and example output from just the test repository."""

    url = "https://api.github.com/repos/sosey/repo-summary/releases"
    test = get_api_data(url=url)
    specs = get_release_specs(test.pop())  # just send in the one dict
    specs['name'] = 'repo-summary'
    make_summary_page([specs], 'repo-release_summary.html')
