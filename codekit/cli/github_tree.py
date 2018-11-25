#!/usr/bin/env python3

from codekit.codetools import debug, error
from codekit import codetools, pygithub
from requests import get
from time import sleep
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

            {prog} --org lsst --repo lsst_distrib --team "Data Management"
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
    parser.add_argument(
        '--team',
        action='append',
        help='include only git repos that are part of the provided team(s)')
    parser.add_argument(
        '--exclusion-file', '-exf',
        default='exclusions.txt',
        dest='exclusion_file',
        help='the file where all packages to exclude are listed')
    parser.add_argument('-v', '--version', action=codetools.ScmVersionAction)
    return parser.parse_args()


def check_team(providedT, repoT):
    if not repoT:
       #print("a  --  Team error, return true")
       return(False)
    for t1 in providedT:
       for t2 in repoT:
          #print(">"+t1+"<", ">"+t2.name+"<")
          if t1==t2.name:
             #print("b  --  Team match, return True")
             return(True)
    #print("c  --  NO Team match, return False")
    return(False)


def get_reposy():

    global g
    global reyali

    RYo='lsst'
    RYr='repos'

    reyali = [[]] 

    try:
        lorgobj = g.get_organization(RYo)
        print(".", end="")
        sleep(1)
    except:
        print("Problem accessing organization ", RYo)
        raise
    else:
        try:
            lrepoobj = lorgobj.get_repo(RYr)
            print(".", end="")
            sleep(1)
        except:
            print("Problem accessing repository ", RYr)
        else:
            ymlfile = "etc/repos.yaml"
            rawfile = lrepoobj.get_file_contents(ymlfile).decoded_content
            print(".", end="")
            sleep(1)
            utf8file = rawfile.decode("utf-8")
            listfile = utf8file.split('\n')
            F = 'F'
            l = 0
            for line in listfile:
                #print(len(line), ' -> ', line)
                if len(line) != 0:
                  if line[0] != '#':
                    if F == 'T':
                      spline = line.split(':')
                      if spline[0] == '  url':
                         spl2 = spline[2].split('/')
                         reyali = reyali + [[tmpname, spl2[3], spl2[4].replace('.git', '')]]
                         #print(reyali[l][0], '  --  ', reyali[l][1], '  --  ', reyali[l][2])
                      else:
                         #print('skip')
                         F = 'F'
                         l = l + 1
                    else:
                      spline = line.split(':')
                      if len(spline) == 3:
                         spl2 = spline[2].split('/')
                         reyali = reyali + [[spline[0], spl2[3], spl2[4].replace('.git', '')]]
                         #print(reyali[l][0], '  --  ', reyali[l][1], '  --  ', reyali[l][2])
                         l = l + 1
                      else:
                         tmpname = spline[0]
                         F = 'T'

    return(reyali)


def get_index(e):
    global reyali

    l = 0
    for line in reyali:
       if len(line) != 0:
          if line[0] == e:
             return(l+1)
          else:
             l = l + 1
    return(-1)


def get_deps(git_repo):
    global swpkg
    global excluded_pkgs
    global i
    global Ptree
    global pkgtree


    pkgdeps = []

    depfile = "ups/" + git_repo.name + ".table"
    #
    try:
        table = git_repo.get_file_contents(depfile).decoded_content
        print(".", end="")
        sleep(1)
    except:
        return()
    else:
       #
       table1 = table.decode("utf-8")
       #
       table2=table1.split('\n')
       #print(table2)
       #

       parent = git_repo.name

       print('\r Analyzing... '.format(i)+str(i)+' ('+parent+')', end='', file=sys.stdout, flush=True)
       for line in table2:

         nodes=line.split('(')
         if nodes[0] in ("setupRequired", "setupOptional"):
           tmp=nodes[1].split(')')
           child=tmp[0]
           tmp=child.split(' ')
           child=tmp[0]
           idx = get_index(child)
           if idx == -1:
              Corg=deforg
           else:
              child=reyali[idx][2]
              Corg=reyali[idx][1]
           if [child, parent] not in Ptree:
             try:
                 COobj = g.get_organization(Corg)
                 print(".", end="")
                 sleep(1)
             except:
                 print('Warning: Invalid dependency organization '+Corg+'-'+child+' in parent '+parent)
             else:
                 #if child != "sconsUtils":
                 if child not in excluded_pkgs:
                   #print('>', parent, ' -> ', child)
                   try:
                      depOBJ=COobj.get_repo(child)
                      print(".", end="")
                      sleep(1)
                   except:
                      print('Warning: Invalid dependency '+child+' in parent '+parent)
                   else:
                      if not Ts:
                         pkgdeps.append(child)
                         i = i+1
                         Ptree = Ptree + [[child, parent]]
                         if child not in swpkg:
                            swpkg.append(child)
                            get_deps(depOBJ)
                      else:
                         #print("  ", child, end="")
                         try:
                             rteams=list(depOBJ.get_teams())
                             print(".", end="")
                             sleep(1)
                         except:
                             rteams=[]
                         CK=check_team(Ts, rteams)
                         if CK:
                            pkgdeps.append(child)
                            i = i+1
                            Ptree = Ptree + [[child, parent]]
                            if child not in swpkg:
                               swpkg.append(child)
                               get_deps(depOBJ)
    pkgtree[parent] = pkgdeps
    return()


def dump(Rname):
    global Ptree
    global folder
    fname=folder+Rname+".dot"
    print("Saving information in "+fname)
    F=open(fname, "w")
    F.write("digraph G {\n")
    F.write("    node [shape=box];\n")
    #print(len(Ptree))
    for record in Ptree:
       if len(record)!=0:
          F.write('    "'+record[1]+'" -> "'+record[0]+'";\n')
    F.write("}\n")
    F.close()

def get_exclusions(input_file):
    f = open(input_file, 'r')

    excluded = []
 
    for line in f:
        #print(line)
        excluded.append(line.rstrip())
    f.close()
    return(excluded)


def order_pkg(pkg):
    global pkg_parents
    global ordered_pkgs

    for lpkg in pkg_parents:
        if pkg == lpkg:
            if pkg_parents[pkg] not in ordered_pkgs:
                order_pkg(pkg_parents[pkg])
                ordered_pkgs.append(pkg)
                #print(pkg, 'parent: ', pkg_parents[pkg])
            else:
                if pkg not in ordered_pkgs:
                    ordered_pkgs.append(pkg)
                    #print(pkg, 'parent: ', pkg_parents[pkg])


def makeTree(product):
    global pkgtree
    global swpkg
    global folder
    global pkg_parents
    global ordered_pkgs

    ordered_pkgs = []
    ordered_pkgs.append(product)
    pkg_parents = {}

    lpkgs = []
    lpkgtree = {}

    # remove duplicated dependencies
    for parent in pkgtree:
        ldeps = []
        for pkg in pkgtree[parent]:
            #print(parent, ' - ', pkg)
            if pkg not in lpkgs:
                ldeps.append(pkg)
                lpkgs.append(pkg)
                pkg_parents[pkg] = parent
        lpkgtree[parent] = ldeps

    for pkg in pkg_parents:
        if pkg_parents[pkg] not in ordered_pkgs:
            order_pkg(pkg_parents[pkg])
            ordered_pkgs.append(pkg)
            #print(pkg, 'parent: ', pkg_parents[pkg])
        else:
            if pkg not in ordered_pkgs:
                ordered_pkgs.append(pkg)
                #print(pkg, 'parent: ', pkg_parents[pkg])

    fname = folder + product + '.tree.csv'
    F = open(fname, 'w')
    F.write('"#","product key","short name","Parent","","","","","",""\n')
    #F.write('"1","' + product + '","' + product + '","","","","","","",""\n')
    count = 1
    for pkg in ordered_pkgs:
        if pkg == product:
            line='"' + str(count) + '","' + pkg + '","' + pkg + '","","","","","","",""\n'
        else:
            line='"' + str(count) + '","' + pkg + '","' + pkg + '","' + pkg_parents[pkg] + '","","","","","",""\n'
        #F.write('"' + str(count) + '","' + pkg + '","' + pkg + '","' + pkg_parents[pkg] + '","","","","","",""\n')
        print(line)
        F.write(line)
        count = count + 1
    #for parent in pkgtree:
    #    #print(parent, ' - ', lpkgtree[parent])
    #    for pkg in pkgtree[parent]:
    #        F.write('"' + str(count) + '","' + pkg + '","' + pkg + '","' + parent + '","","","","","",""\n')
    #        count = count + 1
    F.close()

def run():
    """List repos dependencies"""
    args = parse_args()


    codetools.setup_logging(args.debug)

    global g
    global org
    global i
    global Ptree
    global reyali
    global deforg
    global Ts
    global swpkg
    global folder
    global excluded_pkgs
    global pkgtree

    pkgtree = {}

    if os.path.isfile(args.exclusion_file):
        print('Excluded pkgs in ', args.exclusion_file)
        excluded_pkgs = get_exclusions(args.exclusion_file)
    else:
        print('No exclusions found (', args.exclusion_file,')')
        excluded_pkgs = []

    #print('Excldue: ', excluded_pkgs)

    folder = "dot_files/"

    try:
        if not os.path.exists(folder):
            os.makedirs(folder)
    except OSError:
        print ('Error: Creating directory. ' +  folder)

    swpkg = []
    g = pygithub.login_github(token_path=args.token_path, token=args.token)

    deforg = args.organization

    Ts=args.team

    get_reposy()   

    rind = get_index(args.repository)

    #print(rind, ' : ',reyali[rind][0], ' - ',reyali[rind][1], ' - ',reyali[rind][2])

    if rind == -1:
       Norg=args.organization
       Nrep=args.repository
    else: 
       Norg = reyali[rind][1]
       Nrep = reyali[rind][2]

    try:
        org = g.get_organization(Norg)
        sleep(1)
    except:
        print("Invalid organization ", Norg)
    else:
        try:
            repo =  org.get_repo(Nrep)
            sleep(1)
        except:
            print("Invalid repository ", Nrep)
        else:
            Ptree = [[]]
            i = 0
            print(i, Nrep, "ORG-"+Norg)
            #Ptree =  [[Nrep, "ORG-"+Norg]]
            swpkg.append(Nrep)
            get_deps(repo)
            print('\rFound ', len(Ptree)-1, 'DM dependencies and ', len(swpkg), 'SW products, ')
            dump(Nrep)
            makeTree(Nrep)
    swfile=folder+Nrep+".pkg.txt"
    FP=open(swfile, 'w')
    for pkg in swpkg:
       FP.write(pkg+'\n')
    FP.close()
    apfile=folder+Nrep+"All.pkg.txt"


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
