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


def MakeSummaryPage(data=[], outpage=""):
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

    b = '''
    <html>
      <head>  <title>Github Organization Package Release Information </title>
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
            data.addColumn("string", "Release Information / CHANGES ");
            data.addColumn("string", "Last Released");
            data.addColumn("string", "Release Author")
            data.addRows([
    '''
    html.write(b)

    for repo in data:
        # below is the google table code
        software = repo['repo_name']
        version = repo['version']
        if repo['release_notes'] != 'Missing':
            descrip = RenderHTML(repo['release_notes'])
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

        html.write("[\"{}\",\"{}\",\'<a href=\"{}\">{}</a>\',{}{}{},\"{}\",\'<a href=\"{}\">{}</a>\'],\n".format(
                   software, version, website, "Code Repository", chr(96), descrip, chr(96), date, author_page, author))

    ee = '''  ]);
    var table = new google.visualization.Table(document.getElementById("table_div"));
    table.draw(data, {showRowNumber: true, allowHtml: true});
    }
    </script>
    </head>
    <body><br>
    <br><p align="center" size=10pt>Click on the column fields to sort </p>
    <br><br>
    <p align="left">
    Missing Version means no release or tag was found for the repository.<br>
    If there hasn't been a github release or tag commmit then no author will be found and that field will be N/A
    </p>
    <div id="table_div"></div>
    </body>
    </html>
    '''
    html.write(ee)
    html.close()


def RenderHTML(md=""):
    """Turn markdown string into beautiful soup structure."""
    if not md:
        return ValueError("Supply a string with markdown")
    m = mistune.markdown(md)
    return m


def GetAPIData(url=""):
    """Return the JSON load from the request."""
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()
    res = buffer.getvalue().decode('iso-8859-1')
    return json.loads(res)  # list of dicts


def GetReleaseSpecs(data=None):
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


def ReadResponseFile(response=""):
    """Read a JSON response file."""
    if not response:
        raise ValueError("Please specify json file to read")
    with open(response, 'r') as f:
        data = json.load(f)
    return data


def GetAllReleases(org="", limit=10):
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

    # Get a list of the repositories
    results = GetAPIData(url=orgrepo_url)

    # This usu means there was a problem
    if 'message' in results:
        print(results['message'])
    repo_names = []
    if len(results) > 0:
        for repo in results:
            repo_names.append(repo['name'])
    # Loop through all the repositories to get release information
    # Repositories may have multiple releases
    repo_releases = []
    for name in repo_names:
        data = CheckForRelease(repos_url, name)  # returns a list of results
        # expand the release information into separate dicts
        relspecs = GetReleaseSpecs(data)
        relspecs['repo_name'] = name
        relspecs['base_url'] = "https://github.com/{0:s}/{1:s}/".format(org, name)
        if relspecs['website'] == 'Missing':
            relspecs['website'] = relspecs['base_url']
        repo_releases.append(relspecs)

    return repo_releases


def CheckForRelease(repos="", name=""):
    """Check for release information, not all repos may have releases.

    Repositories without release information may have tag information
    that is used instead
    """
    print("Checking latest information for: {}".format(name))
    rel_url = repos + ("{0:s}/releases/latest".format(name))
    tags_url = repos + ("{0:s}/tags".format(name))
    commit_url = repos + ("{0:s}/commits".format(name))

    jdata = GetAPIData(url=rel_url)

    # no release information ,check tags
    if 'message' in jdata.keys():
        jdata = GetAPIData(url=tags_url)
        if 'message' in jdata:
            print(jdata['message'])
        if len(jdata) >= 1:
            jdata = jdata.pop(0)  # get the assumed latest
            jdata['html_url'] = jdata['commit']['url']
            jdata['tag_name'] = jdata['name']
            jdata['name'] = name
            # check the commits url for more information
            more_data = GetAPIData(url=commit_url)
            more_data = more_data.pop(0)
            jdata['author'] = {'login': more_data["author"]["login"],
                               'html_url': more_data["author"]["html_url"]}
            jdata['published_at'] = more_data["commit"]["author"]["date"]
        else:
            jdata = {'name': name}

    return jdata


if __name__ == "__main__":
    """Create and example output from just the test repository."""

    url = "https://api.github.com/repos/sosey/repo-summary/releases"
    test = GetAPIData(url=url)
    specs = GetReleaseSpecs(test.pop())  # just send in the one dict
    specs['name'] = 'repo-summary'
    MakeSummaryPage([specs], 'repo-release_summary.html')
