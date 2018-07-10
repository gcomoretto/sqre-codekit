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
    global i
    global Ptree
    ltree = []
    ldeps = []
    for line in table2:
      nodes=line.split('(')
      #if nodes[0] == "setupRequired":
      if nodes[0] in ("setupRequired", "setupOptional"):
        child = nodes[1].replace(')','')
        parent = git_repo.name
        if [child, parent] not in Ptree:
          i = i+1
          print(i, child+",", parent)
          Ptree = Ptree + [[child, parent]]
          try:
              depOBJ=org.get_repo(child)
          except:
              print('Warning: Invalid dependency '+child+' in parent '+parent)
          else:
              get_deps(depOBJ)

    return()



def run():
    """List repos and teams"""
    args = parse_args()

    codetools.setup_logging(args.debug)

    global g
    global org
    global i
    global Ptree

    g = pygithub.login_github(token_path=args.token_path, token=args.token)

    try:
        org = g.get_organization(args.organization)
    except:
        print("Invalid organization ", args.organization)

    try:
        repo =  org.get_repo(args.repository)
    except:
        print("Invalid repository ", args.repository)
    else:
        Ptree = [[]]
  
        i = 0

        print(i, args.repository, "ORG-"+args.organization)
        Ptree =  [[args.repository, "ORG-"+args.organization]]
        get_deps(repo)

        print(len(Ptree))


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
