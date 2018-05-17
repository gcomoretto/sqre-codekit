#!/usr/bin/env python3

from codekit import pygithub
from .. import codetools
from .. import info, debug
import argparse
import github
import logging
import re
import sys
import textwrap

logger = logging.getLogger('codekit')
logging.basicConfig()


def parse_args():
    """Parse command-line arguments"""
    prog = 'github-tag-teams'

    parser = argparse.ArgumentParser(
        prog=prog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""

        Tag the head of the default branch of all repositories in a GitHub org
        which belong to the specified team(s).

        Examples:
        {prog} --org lsst --team 'DM Auxilliaries' --tag w.2015.33

        Note that the access token must have access to these oauth scopes:
            * read:org
            * repo

        The token generated by `github-auth --user` should have sufficient
        permissions.
        """).format(prog=prog),
        epilog='Part of codekit: https://github.com/lsst-sqre/sqre-codekit'
    )

    parser.add_argument(
        '--tag',
        action='append',
        required=True,
        help="tag to apply to HEAD of repo (can specify several times")
    parser.add_argument(
        '--org',
        required=True,
        help="Github organization")
    parser.add_argument(
        '--team',
        action='append',
        required=True,
        help="team whose repos may be tagged (can specify several times")
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument(
        '--user',
        help='Name of person making the tag - defaults to gitconfig value')
    parser.add_argument(
        '--email',
        help='Email address of tagger - defaults to gitconfig value')
    parser.add_argument(
        '--token-path',
        default='~/.sq_github_token_delete',
        help='Use a token (made with github-auth) in a non-standard location')
    parser.add_argument(
        '--token',
        default=None,
        help='Literal github personal access token string')
    parser.add_argument(
        '-d', '--debug',
        action='count',
        help='Debug mode')
    parser.add_argument('-v', '--version', action=codetools.ScmVersionAction)
    return parser.parse_args()


def find_repos_missing_tags(repos, tags):
    debug("looking for repos WITHOUT {tags}".format(tags=tags))
    need = {}
    for r in repos:
        has_tags = find_tags_in_repo(r, tags)
        debug("has_tags {t}".format(t=has_tags))
        missing_tags = [x for x in tags if x not in has_tags]
        debug("missing_tags {t}".format(t=missing_tags))
        if missing_tags:
            need[r.full_name] = {
                'repo': r,
                'need_tags': missing_tags,
            }

    return need


def find_tags_in_repo(repo, tags):
    debug(textwrap.dedent("""\
        looking for tag(s): {tags}
          in repo: {repo}\
        """).format(
        tags=tags,
        repo=repo.full_name
    ))
    found_tags = []
    for t in tags:
        ref = pygithub.find_tag_by_name(repo, t)
        if ref and ref.ref:
            debug("  found: {tag}".format(tag=t))
            found_tags.append(re.sub(r'^refs/tags/', '', ref.ref))
            continue

        debug("  not found: {tag}".format(tag=t))

    return found_tags


cached_teams = {}


def find_repo_teams(repo):
    # Repository objects are unhashable, so we can't use memoization ;(
    if repo.full_name in cached_teams:
        return cached_teams[repo.full_name]

    # flatten iterator so the results are cached
    teams = list(repo.get_teams())
    cached_teams[repo.full_name] = teams

    return teams


def tag_repo(repo, tags, tagger, dry_run=False):
    # tag the head of the designated "default branch"
    # XXX this probably should be resolved via repos.yaml
    default_branch = repo.default_branch
    head = repo.get_git_ref("heads/{ref}".format(
        ref=default_branch))

    debug(textwrap.dedent("""\
        tagging {repo} @
          default branch: {db}
          type: {obj_type}
          sha: {obj_sha}\
        """).format(
        repo=repo.full_name,
        db=default_branch,
        obj_type=head.object.type,
        obj_sha=head.object.sha
    ))

    for t in tags:
        debug("  adding tag {t}".format(t=t))
        if dry_run:
            debug('    (noop)')
            continue

        tag_obj = repo.create_git_tag(
            t,
            "Version {t}".format(t=t),  # fmt similar to github-tag-version
            head.object.sha,
            head.object.type,
            tagger=tagger
        )
        debug("  created tag object {tag_obj}".format(tag_obj=tag_obj))

        ref = repo.create_git_ref("refs/tags/{t}".format(t=t), tag_obj.sha)
        debug("  created ref: {ref}".format(ref=ref))


def main():
    args = parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    if args.debug > 1:
        github.enable_console_debug_logging()

    gh_org_name = args.org
    tags = args.tag

    git_email = codetools.lookup_email(args)
    git_user = codetools.lookup_user(args)

    tagger = github.InputGitAuthor(
        git_user,
        git_email,
        codetools.current_timestamp()
    )
    debug(tagger)

    g = pygithub.login_github(token_path=args.token_path, token=args.token)
    org = g.get_organization(gh_org_name)
    debug("tagging repos by team in org: {o}".format(o=org.login))

    teams = org.get_teams()

    debug("looking for teams: {teams}".format(teams=args.team))
    tag_teams = [t for t in teams if t.name in args.team]
    debug("found teams: {teams}".format(teams=tag_teams))

    if not tag_teams:
        raise RuntimeError('No teams found')

    # flatten generator to list so it can be itererated over multiple times
    target_repos = list(pygithub.get_repos_by_team(tag_teams))

    # find length of longest repo name to nicely format output
    names = [r.full_name for r in target_repos]
    max_name_len = len(max(names, key=len))

    info('found repo [teams]:')
    for r in target_repos:
        # list only teams which were used to select the repo as a candiate
        # for tagging
        m_teams = [t.name for t in find_repo_teams(r)
                   if t.name in args.team]
        info("  {repo: >{w}} {teams}".format(
            w=max_name_len,
            repo=r.full_name,
            teams=m_teams)
        )

    # dict
    untagged_repos = find_repos_missing_tags(target_repos, tags)
    # list
    tagged_repos = [r for r in target_repos
                    if r.full_name not in untagged_repos]

    info('already tagged repos:')
    for r in tagged_repos:
        info("  {repo}".format(repo=r.full_name))

    if not untagged_repos:
        sys.exit('no untagged repos -- nothing to do')

    info('missing repo [tags]:')
    max_name_len = len(max(untagged_repos, key=len))
    for k in untagged_repos:
        info("  {repo: >{w}} {tags}".format(
            w=max_name_len,
            repo=k,
            tags=untagged_repos[k]['need_tags']
        ))

    for k in untagged_repos:
        r = untagged_repos[k]['repo']
        tags = untagged_repos[k]['need_tags']
        tag_repo(r, tags, tagger, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
