#!/usr/bin/env python3

from codekit.codetools import debug, error
from codekit import codetools, pygithub
from requests import get
import argparse
import github
import os
import sys
import textwrap



def parse_args():
    """Parse command-line arguments"""
    prog = 'github-tree'

    parser = argparse.ArgumentParser(
        prog=prog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
        List downstream dependencies from a given github repo.

        Examples:

            {prog} --org lsst --repo lsst_distrib
        """).format(prog=prog),
        epilog='Part of codekit: https://github.com/lsst-sqre/sqre-codekit')
    parser.add_argument(
        '-o', '--org',
        dest='organization',
        help='GitHub Organization name',
        required=True)
    parser.add_argument(
        '-r', '--repo',
        dest='repository',
        help='GitHub Repository name',
        required=True)
    parser.add_argument(
        '--token-path',
        default='~/.sq_github_token',
        help='Use a token (made with github-auth) in a non-standard loction')
    parser.add_argument(
        '--token',
        default=None,
        help='Literal github personal access token string')
    parser.add_argument(
        '-d', '--debug',
        action='count',
        default=os.getenv('DM_SQUARE_DEBUG'),
        help='Debug mode (can specify several times)')
    parser.add_argument('-v', '--version', action=codetools.ScmVersionAction)
    return parser.parse_args()


def get_deps(git_repo):
    depfile = "ups/" + git_repo.name + ".table"
    #
    table = git_repo.get_file_contents(depfile).decoded_content
    #
    table1 = table.decode("utf-8")
    #
    table2=table1.split('\n')
    #print(table2)
    #
    ltree = []
    ldeps = []
    for line in table2:
      nodes=line.split('(')
      #if nodes[0] == "setupRequired":
      if nodes[0] in ("setupRequired", "setupOptional"):
        print(nodes[1].replace(')','')+",", git_repo.name+",")
        ltree.append(nodes[1].replace(')',''))
        depOBJ=org.get_repo(nodes[1].replace(')',''))
        ldeps.append(get_deps(depOBJ))
    return(ltree, ldeps)

def run():
    """List repos and teams"""
    args = parse_args()

    codetools.setup_logging(args.debug)

    global g
    g = pygithub.login_github(token_path=args.token_path, token=args.token)

    global org
    org = g.get_organization(args.organization)

    repo =  org.get_repo(args.repository)

    tree = get_deps(repo)


#    try:
#        repos = list(org.get_repos())
#    except github.RateLimitExceededException:
#        raise
#    except github.GithubException as e:
#        msg = 'error getting repos'
#        raise pygithub.CaughtOrganizationError(org, e, msg) from None
#
#    for r in repos:
#        try:
#            teamnames = [t.name for t in r.get_teams()
#                         if t.name not in args.hide]
#        except github.RateLimitExceededException:
#            raise
#        except github.GithubException as e:
#            msg = 'error getting teams'
#            raise pygithub.CaughtRepositoryError(r, e, msg) from None
#
#        maxt = args.maxt if (args.maxt is not None and
#                             args.maxt >= 0) else len(teamnames)
#        if args.debug:
#            print("MAXT=", maxt)
#
#        if args.mint <= len(teamnames) <= maxt:
#            print(r.name.ljust(40) + args.delimiter.join(teamnames))


def main():
    try:
        try:
            run()
        except codetools.DogpileError as e:
            error(e)
            n = len(e.errors)
            sys.exit(n if n < 256 else 255)
        else:
            sys.exit(0)
        finally:
            if 'g' in globals():
                pygithub.debug_ratelimit(g)
    except SystemExit as e:
        debug("exit {status}".format(status=str(e)))
        raise e


if __name__ == '__main__':
    main()
