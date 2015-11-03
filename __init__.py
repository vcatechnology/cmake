#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import sys
import json
import errno
import platform
import fileinput
import subprocess

from datetime import datetime, timezone

try:
    import requests
except ImportError:
    raise ImportError(
        'Failed to import \'requests\', run \'pip install requests\'')

try:
    import pystache
except ImportError:
    raise ImportError(
        'Failed to import \'pystache\', run \'pip install pystache\'')


class ReleaseError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ExecuteCommandError(Exception):
    def __init__(self, message, cmd, code, out, err):
        self.message = message
        self.cmd = cmd
        self.code = code
        self.out = out
        self.err = err

    def __str__(self):
        return self.message


class EmptyLogger(object):
    '''Provides an implementation of an empty logging function'''

    def debug(self, *k, **kw):
        pass

    def info(self, *k, **kw):
        pass

    def warn(self, *k, **kw):
        pass

    def error(self, *k, **kw):
        pass

    def critical(self, *k, **kw):
        pass

    def setLevel(self, *k, **kw):
        pass


class Version(object):
    '''Represents a version number'''

    def __init__(self, *k, **kw):
        '''
        A version number can be instantiate with:

            - a dot-separated string
                - Version('1.2.3')
            - an iterable
                - Version([1, 2, 3])
            - seperate arguments
                - `Version(1, 2, 3)`
            - another version class
                - `Version(Version(1, 2, 3))`
            - a dictionary
                - `Version({'minor':2,'major':1,'patch':3})`
            - keywords
                - `Version(minor = 2,major = 1, patch = 3)`
        '''
        try:
            version = (k[0].major, k[0].minor, k[0].patch)
        except (AttributeError, TypeError):
            try:
                version = (kw['major'], kw['minor'], kw['patch'])
            except (KeyError, TypeError):
                try:
                    version = (k[0]['major'], k[0]['minor'], k[0]['patch'])
                except (KeyError, TypeError):
                    if isinstance(k[0], str):
                        version = k[0].split('.')
                    else:
                        try:
                            version = (k[0][0], k[0][1], k[0][2])
                        except (IndexError, TypeError):
                            version = k
        self.major = int(version[0])
        self.minor = int(version[1])
        self.patch = int(version[2])

    def bump(self, category):
        '''
        Bumps the version number depending on the category
        '''
        setattr(self, category, getattr(self, category) + 1)
        if category == 'major':
            self.minor = 0
            self.patch = 0
        elif category == 'minor':
            self.patch = 0

    def __gt__(self, other):
        return tuple(self) > tuple(other)

    def __ge__(self, other):
        return tuple(self) >= tuple(other)

    def __lt__(self, other):
        return tuple(self) < tuple(other)

    def __le__(self, other):
        return tuple(self) <= tuple(other)

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __ne__(self, other):
        return tuple(self) != tuple(other)

    def __getitem__(self, index):
        '''
        Allows iteration of the version number
        '''
        if index == 0:
            return self.major
        elif index == 1:
            return self.minor
        elif index == 2:
            return self.patch
        else:
            raise IndexError('version index out of range')

    def __repr__(self):
        '''
        Provides a dot-separated string representation of the version number
        '''
        return '%i.%i.%i' % (self.major, self.minor, self.patch)


class GitVersion(Version):
    '''A git repository version number'''

    def __init__(self, *k, **kw):
        '''
        A git version number can be instantiate with:

            - a dot-separated string
                - Version('1.2.3.ef3aa43d-dirty')
            - an iterable
                - Version([1, 2, 3, 'ef3aa43d', True])
            - seperate arguments
                - `Version(1, 2, 3, 'ef3aa43d', True)`
            - another version class
                - `Version(Version(1, 2, 3, 'ef3aa43d', True))`
            - a dictionary
                - `Version({'minor':2,'major':1,'patch':3, 'commit': 'ef3aa43d', 'dirty', True})`
            - keywords
                - `Version(minor = 2,major = 1, patch = 3, commit ='ef3aa43d', dirty =True)`
        '''
        super(GitVersion, self).__init__(*k, **kw)
        try:
            version = (k[0].commit, k[0].dirty)
        except (AttributeError, TypeError):
            try:
                version = (kw['commit'], kw['dirty'])
            except (KeyError, TypeError):
                try:
                    version = (k[0]['commit'], k[0]['dirty'])
                except (KeyError, TypeError):
                    if isinstance(k[0], str):
                        version = k[0].split('.')[3]
                    else:
                        try:
                            version = (k[0][3], k[0][4])
                        except (IndexError, TypeError):
                            version = k[3:]
            self.commit = str(version[0])
            try:
                self.dirty = bool(version[1])
            except:
                try:
                    split = self.commit.split('-')
                    self.dirty = (split[1] == 'dirty')
                    self.commit = split[0]
                except:
                    self.dirty = False
            try:
                int(self.commit, 16)
            except ValueError:
                raise ValueError('The git commit string is not hexidecimal: %s'
                                 % self.commit)

    def __repr__(self):
        '''
        Provides a dot-separated string representation of the version number
        '''
        string = '%s.%s' % (super(GitVersion, self).__repr__(),
                            self.commit[:8])
        if self.dirty:
            string += '-dirty'
        return string


def find_exe_in_path(filename, path=None):
    '''
    Finds an executable in the PATH environment variable
    '''
    if platform.system() == 'Windows':
        filename += '.exe'
    if path is None:
        path = os.environ.get('PATH', '')
    if type(path) is type(''):
        pathlist = path.split(os.pathsep)
    return list(filter(os.path.exists, map(lambda dir, filename=filename: os.path.join(dir, filename), pathlist)))


def execute_command(cmd,
                    error_message='Failed to run external program',
                    expected=0,
                    cwd=os.getcwd()):
    p = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         universal_newlines=True,
                         cwd=cwd)
    (out, err) = p.communicate()
    if expected != None and p.returncode != expected:
        raise ExecuteCommandError(error_message, cmd, p.returncode, out, err)
    return (p.returncode, out, err)


def close_milestone(number, repo, token, logger=EmptyLogger()):
    logger.debug('Closing milestone #%d for %s' % (number, repo))
    number = int(number)
    r = requests.patch('https://api.github.com/repos/%s/milestones/%d' %
                       (repo, number),
                       params={
                           'access_token': token,
                       },
                       json={
                           'state': 'closed',
                       })
    if r.status_code != 200:
        json = r.json()
        message = json['message']
        errors = json.get('errors', [])
        for e in errors:
            message += '\n  - %s: %s: %s' % (e.get('resource', 'unknown'),
                                             e.get('field', 'unknown'),
                                             e.get('code', 'unknown'))
        raise ReleaseError('Failed to close github milestone #%d: %s' %
                           (number, message))
    logger.info('Closed milestone #%d' % number)
    return r.json()


def get_milestones(repo, token, logger=EmptyLogger()):
    logger.debug('Retrieving milestones for %s' % repo)
    r = requests.get('https://api.github.com/repos/%s/milestones' % repo,
                     params={
                         'access_token': token,
                     })
    if r.status_code != 200:
        raise ReleaseError('Failed to retrieve github milestones from %s: %s' %
                           (repo, r.json()['message']))
    return r.json()


def get_git_tag_version(path,
                        git_executable=find_exe_in_path('git'),
                        logger=EmptyLogger()):
    if isinstance(git_executable, list):
        git_executable = git_executable[0]

    logger.debug('Getting latest git tag version')

    # Get the head commit
    cmd = [git_executable, 'rev-parse', 'HEAD']
    _, out, _ = execute_command(cmd,
                                'Failed to get HEAD revision of repository',
                                cwd=path)
    commit = out.split('\n')[0].strip()
    if commit == 'HEAD' or not commit:
        commit = '0000000000000000000000000000000000000000'

    # Check if dirty
    dirty = False
    cmd = [git_executable, 'diff-index', '--name-only', 'HEAD']
    if execute_command(
            cmd,
            'Failed to check if the project had local modifications',
            cwd=path)[1]:
        dirty = True
    cmd = [git_executable, 'status', '--porcelain']
    if '?? ' in execute_command(
            cmd,
            'Failed to check if the project had local modifications',
            cwd=path)[1]:
        dirty = True

    # Find the latest tag
    cmd = [git_executable, 'describe', '--match=v[0-9]*', 'HEAD']
    code, out, _ = execute_command(cmd, expected=None, cwd=path)
    if code:
        return GitVersion(0, 0, 0, commit, dirty)

    # Parse the tag
    re_tag = re.compile('^v([0-9]+)\.([0-9]+)\.([0-9]+)(-[0-9]+-g[a-f0-9]+)?')
    matches = re_tag.match(out)
    major = int(matches.group(1))
    minor = int(matches.group(2))
    revision = int(matches.group(3))
    version = GitVersion(major, minor, revision, commit, dirty)
    logger.info('Latest git tag version %s' % version)
    return version


re_remote_fetch_url = re.compile(
    r'Fetch URL: (?:(?:(git)(?:@))|(?:(https)(?:://)))([^:/]+)[:/]([^/]+/[^.]+)(?:\.git)?')


def get_repo(path=os.getcwd(), git_executable=find_exe_in_path('git')):
    if isinstance(git_executable, list):
        git_executable = git_executable[0]
    cmd = [git_executable, 'remote', 'show', '-n', 'origin']
    code, out, err = execute_command(
        cmd,
        'Failed to get repository remote information',
        cwd=path)
    match = re_remote_fetch_url.search(out)
    if not match:
        raise ExecuteCommandError('Failed to match fetch url', cmd, code, out,
                                  err)
    protocol = match.group(1) or match.group(2)
    server = match.group(3)
    if server != 'github.com':
        raise ExecuteCommandError('Repository is not from github', cmd, code,
                                  out, err)
    repo = match.group(4)
    return repo


def get_git_version(git_executable=find_exe_in_path('git'),
                    logger=EmptyLogger()):
    if isinstance(git_executable, list):
        git_executable = git_executable[0]
    logger.debug('Getting git version')
    _, out, _ = execute_command([git_executable, '--version'])
    git_version = Version(out.replace('git version ', ''))
    logger.debug('Using git %s' % git_version)
    return git_version

changelog_template = \
    '## [v{{version.to}}](https://github.com/{{repo}}/tree/v{{version.to}}) ({{date}})\n' \
    '{{#version.from}}' \
    '[Full Changelog](https://github.com/{{repo}}/compare/v{{version.from}}...v{{version.to}})' \
    '{{/version.from}}' \
    '{{#milestone}}' \
    '{{#version.from}} {{/version.from}}' \
    '[Milestone]({{html_url}})' \
    '{{/milestone}}\n' \
    '\n' \
    '{{description}}\n' \
    '\n' \
    '**Closed issues:**\n' \
    '{{#issues}}\n' \
    '\n' \
    '  - {{title}} [\#{{number}}]({{html_url}})\n' \
    '{{/issues}}\n' \
    '{{^issues}}\n' \
    '\n' \
    '_None_\n' \
    '{{/issues}}\n' \
    '\n' \
    '**Merged pull requests:**\n' \
    '{{#pullrequests}}\n' \
    '\n' \
    '  - {{title}} [\#{{number}}]({{pull_request.html_url}})\n' \
    '{{/pullrequests}}\n' \
    '{{^pullrequests}}\n' \
    '\n' \
    '_None_\n' \
    '{{/pullrequests}}\n'


def get_closed_issues(repo,
                      token=os.environ.get('GITHUB_TOKEN', None),
                      since=None,
                      logger=EmptyLogger()):
    logger.debug('Getting issues for %s' % (repo))
    if not token:
        raise ReleaseError('Must provide a valid GitHub API token')
    issues = []
    params = {'state': 'closed', 'sort': 'asc', 'access_token': token, }
    if since:
        since = since.astimezone(timezone.utc)
        params['since'] = since.isoformat()[:19] + 'Z'
    r = requests.get('https://api.github.com/repos/%s/issues' % repo,
                     params=params)
    if r.status_code != 200:
        raise ReleaseError('Failed to retrieve github issues from %s: %s' %
                           (repo, r.json()['message']))
    issues = r.json()
    logger.debug('Retrieved %i closed issues for %s' % (len(issues), repo))
    return issues


def create_changelog(current_version,
                     previous_version,
                     repo,
                     milestone=None,
                     token=os.environ.get('GITHUB_TOKEN', None),
                     description=None,
                     since=None,
                     date=datetime.utcnow(),
                     template=changelog_template,
                     logger=EmptyLogger()):
    logger.debug('Creating changelog for %s from %s' % (current_version, repo))
    description = description or 'The v%s release of %s' % (current_version,
                                                            repo.split('/')[1])
    issues = get_closed_issues(repo=repo,
                               token=token,
                               since=since,
                               logger=logger)
    if milestone:
        milestone[
            'html_url'] = 'https://github.com/%s/issues?q=milestone%%3Av%s+is%%3Aall' % (
                repo, current_version)
    data = {
        'version': {
            'from': str(previous_version)
            if previous_version > (0, 0, 0) else None,
            'to': str(current_version),
        },
        'milestone': milestone,
        'date': date.isoformat()[:10],
        'repo': repo,
        'description': description,
        'issues': [i for i in issues if not i.get('pull_request', None)],
        'pullrequests': [i for i in issues if i.get('pull_request', None)],
    }
    renderer = pystache.Renderer()
    parsed = pystache.parse(template)
    changelog = renderer.render(parsed, data)
    logger.info('Rendered changelog')
    return changelog


def write_changelog(path, changelog, logger=EmptyLogger()):
    try:
        for line in fileinput.input(path, inplace=True):
            sys.stdout.write(line)
            if line.startswith('# Changelog'):
                print()
                sys.stdout.write(changelog)
        logger.info('Updated %s' % os.path.basename(path))
    except EnvironmentError as e:
        if e.errno == errno.ENOENT:
            with open(path, 'w') as f:
                f.write('# Changelog\n\n')
                f.write(changelog)
            logger.info('Created %s' % os.path.basename(path))
        else:
            raise


def get_git_root(path, git_executable=find_exe_in_path('git')):
    abspath = os.path.abspath(path)
    if os.path.isfile(abspath):
        abspath = os.path.dirname(abspath)
    cmd = [git_executable, 'rev-parse', '--show-toplevel']
    _, out, _ = execute_command(cmd,
                                'Failed to find root of repository',
                                cwd=abspath)
    return out.strip()


def commit_file(path,
                message,
                git_executable=find_exe_in_path('git'),
                logger=EmptyLogger()):
    if isinstance(git_executable, list):
        git_executable = git_executable[0]
    logger.debug('Commiting %s' % path)
    cwd = get_git_root(path, git_executable=git_executable)
    path = os.path.relpath(path, cwd)
    cmd = [git_executable, 'add', path]
    execute_command(cmd, 'Failed to add file %s' % path, cwd=cwd)
    cmd = [git_executable, 'commit', '-m', message]
    execute_command(cmd, 'Failed to commit file %s' % path, cwd=cwd)
    logger.info('Committed %s' % path)


def get_tag_date(tag,
                 path=os.getcwd(),
                 git_executable=find_exe_in_path('git')):
    if isinstance(git_executable, list):
        git_executable = git_executable[0]
    cwd = get_git_root(path, git_executable=git_executable)
    cmd = [git_executable, 'log', '-1', '--format=%ai', tag]
    _, out, _ = execute_command(cmd,
                                'Failed to get tag date: %s' % tag,
                                cwd=cwd)
    out = out.strip()
    return datetime.strptime(out, '%Y-%m-%d %H:%M:%S %z')


def create_git_version_tag(version,
                           message=None,
                           path=os.getcwd(),
                           git_executable=find_exe_in_path('git'),
                           logger=EmptyLogger()):
    if isinstance(git_executable, list):
        git_executable = git_executable[0]
    if not isinstance(version, Version):
        raise ValueError('must provide a version class')
    version = Version(version)
    logger.debug('Tagging %s' % version)
    message = message or 'The v%s release of the project' % version
    cwd = get_git_root(path, git_executable=git_executable)
    cmd = [git_executable, 'tag', '-a', 'v%s' % version, '-m', message]
    execute_command(cmd, 'Failed to create version tag %s' % version, cwd=cwd)
    logger.info('Tagged %s' % version)


def create_release(repo,
                   version,
                   description,
                   token=os.environ.get('GITHUB_TOKEN', None),
                   files=[],
                   path=os.getcwd(),
                   git_executable=find_exe_in_path('git'),
                   logger=EmptyLogger()):
    if isinstance(git_executable, list):
        git_executable = git_executable[0]
    if not isinstance(version, Version):
        raise ValueError('must provide a version class')
    logger.debug('Creating github release %s' % version)
    r = requests.post('https://api.github.com/repos/%s/releases' % repo,
                      params={
                          'access_token': token,
                      },
                      json={
                          'tag_name': 'v%s' % version,
                          'name': str(version),
                          'body': description,
                      })
    if r.status_code != 201:
        json = r.json()
        message = json['message']
        errors = json.get('errors', [])
        for e in errors:
            message += '\n  - %s: %s: %s' % (e.get('resource', 'unknown'),
                                             e.get('field', 'unknown'),
                                             e.get('code', 'unknown'))
        raise ReleaseError('Failed to create github release %s: %s' %
                           (repo, message))
    logger.info('Created GitHub release')


def release(category='patch',
            path=os.getcwd(),
            git_executable=find_exe_in_path('git'),
            token=os.environ.get('GITHUB_TOKEN', None),
            repo=None,
            date=datetime.utcnow(),
            description=None,
            changelog='CHANGELOG.md',
            template=changelog_template,
            logger=EmptyLogger(),
            hooks={}):
    '''
    Performs the release of a repository on GitHub.
    '''
    if isinstance(git_executable, list):
        git_executable = git_executable[0]

    logger.debug('Starting %r release' % category)

    git_version = get_git_version(git_executable=git_executable, logger=logger)
    if git_version < (1, 0, 0):
        raise ReleaseError('The version of git is too old %s' % git_version)

    previous_version = get_git_tag_version(path=path,
                                           git_executable=git_executable,
                                           logger=logger)

    if previous_version.dirty:
        raise ReleaseError(
            'Cannot release a dirty repository. Make sure all files are committed')

    current_version = Version(previous_version)
    previous_version = Version(current_version)
    current_version.bump(category)
    logger.debug('Previous version %r' % previous_version)
    logger.debug('Bumped version %r' % current_version)

    repo = repo or get_repo(path=path, git_executable=git_executable)
    description = description or 'The v%s release of %s' % (current_version,
                                                            repo.split('/')[1])

    milestones = get_milestones(repo=repo, token=token, logger=logger)
    try:
        milestone = [
            m
            for m in milestones
            if m['title'] == ('v%s' % current_version) and m['state'] == 'open'
        ][0]
        open_issues = milestone['open_issues']
        if open_issues:
            raise ReleaseError('The v%s milestone has %d open issues' %
                               (current_version, open_issues))
    except IndexError:
        milestone = None

    try:
        previous_date = get_tag_date('v%s' % previous_version,
                                     path=path,
                                     git_executable=git_executable)
    except ExecuteCommandError:
        previous_date = None
    changelog_data = create_changelog(description=description,
                                      repo=repo,
                                      date=date,
                                      token=token,
                                      current_version=current_version,
                                      previous_version=previous_version,
                                      template=template,
                                      since=previous_date,
                                      logger=logger,
                                      milestone=milestone)

    changelog_data = hooks.get('changelog', lambda d: d)(changelog_data)

    write_changelog(path=os.path.join(path, changelog),
                    changelog=changelog_data,
                    logger=logger)

    commit_file(changelog,
                'Updated changelog for v%s' % current_version,
                git_executable=git_executable,
                logger=logger)

    create_git_version_tag(current_version,
                           message=description,
                           path=path,
                           git_executable=git_executable,
                           logger=logger)

    logger.debug('Pushing branch to remote')
    cwd = get_git_root(path, git_executable=git_executable)
    cmd = [git_executable, 'push']
    execute_command(cmd, 'Failed to push to remote', cwd=cwd)
    logger.info('Pushed branch to remote')

    logger.debug('Pushing tags to remote')
    cwd = get_git_root(path, git_executable=git_executable)
    cmd = [git_executable, 'push', '--tags']
    execute_command(cmd, 'Failed to push tags to remote', cwd=cwd)
    logger.info('Pushed tags to remote')

    files = []

    create_release(path=path,
                   version=current_version,
                   description=changelog_data,
                   git_executable=git_executable,
                   repo=repo,
                   logger=logger,
                   files=files,
                   token=token)

    if milestone:
        close_milestone(number=milestone['number'],
                        repo=repo,
                        token=token,
                        logger=logger)

    logger.info('Released %s' % current_version)
