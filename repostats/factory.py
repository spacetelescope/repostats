#!/usr/bin/env python

import logging

logger = logging.getLogger('') # <--- Probable a good idea to name your logger. '' is the 'root' logger
sysHandler = logging.StreamHandler()
sysHandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(sysHandler)
logger.setLevel(logging.INFO)

import argparse
import typing

from repostats import get_repo_info, make_summary_page

logger = logging.getLogger(__name__)

def capture_options() -> typing.Any:
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--repos', nargs="+", default=[])
    parser.add_argument('-p', '--public-only', action="store_false", default=True)
    parser.add_argument('-l', '--repo-limit', type=int, default=50)
    parser.add_argument('-o', '--github-organization', type=str, default="")
    parser.add_argument('-u', '--outpage', type=str, default="spacetelescope.html")
    return parser.parse_args()

def run_application():
    options = capture_options()
    data = get_repo_info(org=options.github_organization, limit=options.repo_limit, pub_only=options.public_only, repos=options.repos)
    make_summary_page(data, outpage=options.outpage)
    logger.info(f'Page[{options.outpage}] ready')

if __name__ == '__main__':
    run_application()

