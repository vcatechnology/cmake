#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
A set of Python functions that perform operations in GitHub.

.. moduleauthor:: VCA Technology

'''

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
    '''
    An exception that is thrown when a release fails

    :param str message: A message that explains why the release has failed
    '''

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ExecuteCommandError(Exception):
    '''
    An exception that is thrown when a release fails

    :param str message: A message that explains why the command failed to be
        executed
    :param list cmd: The command that was attempted to be executed
    :param int code: The return code of the execution
    :param str out: The messages that were print to :code:`stdout` when the
        failed command ran
    :param str err: The :code:`stderr` output from the failed execution
    '''

    def __init__(self, message, cmd, code, out, err):
        self.message = message
        self.cmd = cmd
        self.code = code
        self.out = out
        self.err = err

    def __str__(self):
        return self.message


class HttpApiError(Exception):
    '''
    An exception that is thrown when a HTTP API fails

    :param str message: A message that explains why the command failed to be
        executed
    :param str url: the URL that the request failed at
    :param int code: the HTTP status code returned from the request
    :param dict error: the returned data from the request
    '''

    def __init__(self, message, url, code, error):
        self.message = message
        self.url = url
        self.code = code
        self.error = error

    def __str__(self):
        return '%s (%i): %s' % (self.message, self.code, self.url)


class EmptyLogger(object):
    'A logger that swallows all messages to provide silent execution'

    def debug(self, *k, **kw):
        '''
        Messages that are more in depth and are shown usually when the scripts
        are ran in :code:`--verbose` mode
        '''
        pass

    def info(self, *k, **kw):
        '''
        Informational messages that can provide output that will be useful to
        the user
        '''
        pass

    def warn(self, *k, **kw):
        'Logs warnings that provide non-error message to the user'
        pass

    def error(self, *k, **kw):
        'Errors that have occured but do not effect the running of the script'
        pass

    def critical(self, *k, **kw):
        'Message that are output before the script must terminate'
        pass

    def setLevel(self, *k, **kw):
        'Sets the level of the logger to show a certain level of messages'
        pass


class Version(object):
    '''
    The version class represents a semantic three digit version. It has
    multiple ways to create the version:

    .. code-block:: python

       # with arguments
       version = Version(0, 2, 4)

       # with a string
       version = Version('0.2.4')

       # from another version (or named tuple)
       version = Version(version)

       # from a dictionary
       version = Version({
         'major': 0,
         'minor': 2,
         'patch': 4,
       })

       # with keywords
       version = Version(
         major = 0,
         minor = 2,
         patch = 4,
       )
    '''

    def __init__(self, *k, **kw):
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
        Bumps one of the numbers in the version

        :param str category: Must be one of :code:`major`, :code:`minor` or
            :code:`patch`
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
        if index == 0:
            return self.major
        elif index == 1:
            return self.minor
        elif index == 2:
            return self.patch
        else:
            raise IndexError('version index out of range')

    def __repr__(self):
        return '%i.%i.%i' % (self.major, self.minor, self.patch)


class GitVersion(Version):
    '''
    A version class that represents a version of a git repository. It can
    contain the latest semantic version of the repository, the commit hash
    and a boolean determining if the repository is dirty (has changed
    files). It can be constructed in various ways:

    .. code-block:: python

       # with arguments
       version = GitVersion(0, 2, 4, '4ed39a87')
       version = GitVersion(0, 2, 4, '4ed39a87-dirty')
       version = GitVersion(0, 2, 4, '4ed39a87', True)

       # with a string
       version = GitVersion('0.2.4.4ed39a87')
       version = GitVersion('0.2.4.4ed39a87-dirty')

       # from another version (or named tuple)
       version = GitVersion(version)

       # from a dictionary
       version = GitVersion({
         'major': 0,
         'minor': 2,
         'patch': 4,
         'commit': '4ed39a87',
         'dirty': True,
       })

       # with keywords
       version = GitVersion(
         major = 0,
         minor = 2,
         patch = 4,
         commit = '4ed39a87',
         dirty = True,
       )
    '''

    def __init__(self, *k, **kw):
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
        string = '%s.%s' % (super(GitVersion, self).__repr__(),
                            self.commit[:8])
        if self.dirty:
            string += '-dirty'
        return string


def find_exe_in_path(filename, path=None):
    '''
    Finds an executable in the system :code:`PATH` environment variable

    .. code-block:: python

       paths = pygh.find_exe_in_path('git')
       paths = pygh.find_exe_in_path('ls', '/usr/bin:/my-custom-folder')
       paths = pygh.find_exe_in_path('dir', r'C:\windows;D:\my custom folder')

    :param str filename: the file name of the executable to find, for
        example :code:`git`
    :param str path: a set of paths to search for the executable seperated by
        the operating system path seperator, overrides the :code:`PATH`
        environment variable if specified
    :returns: list of absolute paths to any matching executables
    '''
    if platform.system() == 'Windows':
        filename += '.exe'
    if path is None:
        path = os.environ.get('PATH', '')
    if type(path) is type(''):
        pathlist = path.split(os.pathsep)
    return list(filter(os.path.exists,
        map(lambda dir, filename=filename:
            os.path.join(dir, filename), pathlist)))


def execute_command(cmd,
                    error_message='Failed to run external program',
                    expected=0,
                    cwd=os.getcwd()):
    '''
    Executes a command in the shell and returns the result of the execution.

    .. code-block:: python

       # Get the stdout
       _, out, _ = pygh.execute_command(['ls'], 'Failed to list directory')

       # do not throw an exception, we want the return code
       code, _, _ = pygh.execute_command(['false'], expected = None)


    :param list cmd: the command to execute, all arguments will be correctly
        forwarded on to the shell
    :param str error_message: the message that will be added to the
        :class:`ExecuteCommandError` if the returned status code does not equal
        :code:`expected`
    :param int expected: the status code that is expected from the execution of
        the :code:`cmd`, can be set to :code:`None` to ignore the return code
    :param str cwd: the path to execute the command in
    :returns: a tuple of :code:`(status_code, stdout, stderr)`
    :raises ExecuteCommandError: if the command fails and :code:`expected` does
        not equal :code:`None`
    '''
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
    '''
    Closes a milestone on GitHub.

    :param int number: the number of the milestone to close
    :param str repo: the GitHub repository to close the milestone on,
        e.g. :code:`vcatechnology/pygh`
    :token str token: either the environment variable to read the token from or
        a 40 digit hexidecimal number
    :param Logger logger: the logging class to use for providing status updates
    :returns: the returned JSON from the request parsed into a python
        :code:`dict`
    :raises HttpApiError: if the request fails
    '''
    logger.debug('Closing milestone #%d for %s' % (number, repo))
    token = get_api_token(token)
    number = int(number)
    url = 'https://api.github.com/repos/%s/milestones/%d' % (repo, number)
    r = requests.patch(url,
                       params={
                           'access_token': token,
                       },
                       json={
                           'state': 'closed',
                       })
    if r.status_code != 200:
        raise HttpApiError('Failed to close github milestone #%d' % number,
                           url, r.status_code, r.json())
    logger.info('Closed milestone #%d' % number)
    return r.json()


def get_milestones(repo, token, logger=EmptyLogger()):
    '''
    Returns the open milestones on a GitHub repository

    :param str repo: the GitHub repository to close the milestone on,
        e.g. :code:`vcatechnology/pygh`
    :token str token: either the environment variable to read the token from or
        a 40 digit hexidecimal number
    :param Logger logger: the logging class to use for providing status updates
    :returns: the returned JSON from the request parsed into a python
        :code:`dict`
    :raises HttpApiError: if the request fails
    '''
    logger.debug('Retrieving milestones for %s' % repo)
    token = get_api_token(token)
    url = 'https://api.github.com/repos/%s/milestones' % repo
    r = requests.get(url, params={'access_token': token, })
    if r.status_code != 200:
        raise HttpApiError('Failed to retrieve github milestones from %s' %
                           repo, url, r.status_code, r.json())
    return r.json()


def get_version_milestone(version, repo, token, logger=EmptyLogger()):
    '''
    Retrieves a milestone that matches a version number. The title must be
    a semantic version number :code:`vX.X.X` that matches :code:`version`

    :param Version version: the version of the milestone to be found
    :param str repo: the GitHub repository to close the milestone on,
        e.g. :code:`vcatechnology/pygh`
    :token str token: either the environment variable to read the token from or
        a 40 digit hexidecimal number
    :returns: the milestone JSON data as a python :code:`dict` or :code:`None`
        if no matching milestone was found
    :raises ValueError: if the :code:`version` parameter is not a
        :class:`Version`
    '''
    if not isinstance(version, Version):
        raise ValueError('must provide a version class')
    try:
        milestones = get_milestones(repo=repo, token=token, logger=logger)
        return [
            m
            for m in milestones
            if m['title'] == ('v%s' % version) and m['state'] == 'open'
        ][0]
    except IndexError:
        return None


def get_git_exe():
    '''
    Returns the first found git executable in the system path

    :returns: the filesystem location of the git executable
    '''
    try:
        return find_exe_in_path('git')[0]
    except IndexError:
        raise ValueError('Failed to find git in system path, is it installed?')


def get_latest_git_tag_version(path,
                               git_executable=get_git_exe(),
                               logger=EmptyLogger()):
    '''
    Returns the latest tagged semantic version for a repository.

    :param str path: the path of the repository to find the tag in
    :param str git_executable: the filesystem location of the
        :code:`git` executable to use
    :param Logger logger: the logging class to use for providing status updates
    :returns: a :class:`GitVersion` representing the state of the repository
    :raises ExecuteCommandError: if any of the :code:`git` commands fail
    '''
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


def get_github_repo(path, git_executable=get_git_exe()):
    '''
    Retrieves the GitHub repository from a local git repository remote string.
    For example, if the remote is :code:`git@github.com:vcatechnology/pygh.git`
    then the returned GitHub repository is :code:`vcatechnology/pygh`

    :param str path: the local filesystem location of the git repository to
        inspect
    :param str git_executable: the filesystem location of the
        :code:`git` executable to use
    :returns: the GitHub repository string
    :raises ExecuteCommandError: if any of the :code:`git` commands fail
    '''
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


def get_git_version(git_executable=get_git_exe(), logger=EmptyLogger()):
    '''
    Retrieves the version of a :code:`git` executable

    :param str path: the local filesystem location of the git repository to
        inspect
    :param str git_executable: the filesystem location of the
        :code:`git` executable to use
    :param Logger logger: the logging class to use for providing status updates
    :returns: a :class:`Version`
    :raises ExecuteCommandError: if the :code:`git` command fails
    '''
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

re_api_token = re.compile(r'^[0-9a-f]{40}$')


def get_api_token(token='GITHUB_TOKEN'):
    '''
    Retrieves a GitHub API from the environment or returns the token given

    :token str token: either the environment variable to read the token from or
        a 40 digit hexidecimal number
    :returns: the GitHub token
    :raises ValueError: if the GitHub token is not a valid 40 digit hexidecimal
        token
    '''
    token = os.environ.get(token, token)
    if not re_api_token.match(token):
        raise ValueError('Failed to find a valid GitHub token: %s' % token)
    return token


def get_issues(repo,
               state,
               since=None,
               token='GITHUB_TOKEN',
               logger=EmptyLogger()):
    '''
    Returns the closed issues for a GitHub repository. Useful for building a
    changelog.

    :param str repo: the GitHub repository to get the issues for,
        e.g. :code:`vcatechnology/pygh`
    :param str state: either :code:`closed`, :code:`open` or :code:`all`
    :param datetime since: only return issues that have been updated since this
        timestamp
    :token str token: either the environment variable to read the token from or
        a 40 digit hexidecimal number
    :param Logger logger: the logging class to use for providing status updates
    :returns: the returned JSON from the request parsed into a python
        :code:`dict`
    :raises HttpApiError: if the request fails
    '''
    logger.debug('Getting issues for %s' % (repo))
    token = get_api_token(token)
    issues = []
    params = {'state': state, 'sort': 'asc', 'access_token': token, }
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
                     path,
                     repo=None,
                     description=None,
                     template=changelog_template,
                     token='GITHUB_TOKEN',
                     git_executable=get_git_exe(),
                     date=datetime.utcnow(),
                     logger=EmptyLogger()):
    '''
    Creates a changelog markdown entry for a certain version.

    :param Version current_version: the version to be released
    :param Version previous_version: the last version that was released which is
        is used to retrieved closed issues and pull requests since the last
        release
    :param str path: the local filesystem location
    :param str repo: the GitHub repository to work against, e.g.
        :code:`vcatechnology/pygh`
    :param str description: the description of the release, such as major
        features implemented
    :param str template: a mustache template that will be formatted into the
        changelog
    :token str token: either the environment variable to read the token from or
        a 40 digit hexidecimal number
    :param str git_executable: the filesystem location of the
        :code:`git` executable to use
    :param datetime date: the date the release occurred
    :param Logger logger: the logging class to use for providing status updates
    :raises HttpApiError: if a GitHub API request fails
    '''
    repo = repo or get_github_repo(path=path, git_executable=git_executable)
    logger.debug('Creating changelog for %s from %s' % (current_version, repo))
    description = description or 'The v%s release of %s' % (current_version,
                                                            repo.split('/')[1])

    try:
        since = get_tag_date('v%s' % previous_version,
                             path=path,
                             git_executable=git_executable)
    except ExecuteCommandError:
        since = None

    issues = get_issues(repo=repo,
                        state='closed',
                        since=since,
                        token=token,
                        logger=logger)

    milestone = get_version_milestone(version=current_version,
                                      repo=repo,
                                      token=token,
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


def write_version(path, version, logger=EmptyLogger()):
    '''
    Writes the version number to a file at :code:`path`

    :param str path: the filesystem location of the file to write
    :param Version version: the version number to write
    :param Logger logger: the logging class to use for providing status updates
    :raises ValueError: if the :code:`version` parameter is not a
        :class:`Version`
    :raises EnvironmentError: if the IO fails
    '''
    if not isinstance(version, Version):
        raise ValueError('must provide a version class')
    version = Version(version)
    with open(path, 'w') as f:
        f.write('%s' % version)
    logger.info('Wrote %s' % os.path.basename(path))


def write_changelog(path, changelog, logger=EmptyLogger()):
    '''
    Writes, or updates the changelog at :code:`path`

    :param str path: the filesystem location of the file to write
    :param str changelog: the markdown formatted changelog
    :param Logger logger: the logging class to use for providing status updates
    :raises EnvironmentError: if the IO fails
    '''
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


def get_git_root(path, git_executable=get_git_exe()):
    '''
    Retrieves the root of a git repository if :code:`path` is a filesystem
    location inside it. Can be useful to get relative paths to files inside a
    git repository

    :param str path: the filesystem location to inspect
    :param str git_executable: the filesystem location of the
        :code:`git` executable to use
    :param Logger logger: the logging class to use for providing status updates
    :returns: the filesystem path
    :raises ExecuteCommandError: if the :code:`git` command fails
    '''
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
                git_executable=get_git_exe(),
                logger=EmptyLogger()):
    '''
    Commits a file that is inside a repository

    :param str path: the location of the file to commit
    :param str message: the commit message
    :param str git_executable: the filesystem location of the
        :code:`git` executable to use
    :param Logger logger: the logging class to use for providing status updates
    :raises ExecuteCommandError: if the :code:`git` command fails
    '''
    logger.debug('Commiting %s' % path)
    cwd = get_git_root(path, git_executable=git_executable)
    path = os.path.relpath(path, cwd)
    cmd = [git_executable, 'add', path]
    execute_command(cmd, 'Failed to add file %s' % path, cwd=cwd)
    cmd = [git_executable, 'commit', '-m', message]
    execute_command(cmd, 'Failed to commit file %s' % path, cwd=cwd)
    logger.info('Committed %s' % path)


def get_tag_date(tag, path, git_executable=get_git_exe()):
    '''
    Gets a :code:`datetime` object for a git tag.

    :param str tag: the tag name to get the date for
    :param str path: the location of the repository
    :param str git_executable: the filesystem location of the
        :code:`git` executable to use
    :raises ExecuteCommandError: if the :code:`git` command fails
    '''
    cwd = get_git_root(path, git_executable=git_executable)
    cmd = [git_executable, 'log', '-1', '--format=%ai', tag]
    _, out, _ = execute_command(cmd,
                                'Failed to get tag date: %s' % tag,
                                cwd=cwd)
    out = out.strip()
    return datetime.strptime(out, '%Y-%m-%d %H:%M:%S %z')


def create_git_version_tag(version,
                           path,
                           message=None,
                           git_executable=get_git_exe(),
                           logger=EmptyLogger()):
    '''
    Creates a annotated semantic version tag in a git repository

    :param Version version: the version to tag
    :param str message: the tag message
    :param str path: the location of the repository
    :param str git_executable: the filesystem location of the
        :code:`git` executable to use
    :param Logger logger: the logging class to use for providing status updates
    :raises ExecuteCommandError: if the :code:`git` command fails
    '''
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
                   path,
                   token='GITHUB_TOKEN',
                   files=[],
                   logger=EmptyLogger()):
    '''
    Creates a GitHub release that attaches the changelog to the tagged version
    on GitHub.

    :param str repo: the GitHub repository to work against, e.g.
        :code:`vcatechnology/pygh`
    :param Version version: the version to be released
    :param str description: the description of the release, such as major
        features implemented
    :param str path: the location of the local github repository
    :token str token: either the environment variable to read the token from or
        a 40 digit hexidecimal number
    :param list files: the files to be attached to the release
    :param Logger logger: the logging class to use for providing status updates
    :raises HttpApiError: if a GitHub API request fails
    '''
    if not isinstance(version, Version):
        raise ValueError('must provide a version class')
    logger.debug('Creating github release %s' % version)
    token = get_api_token(token)
    url = 'https://api.github.com/repos/%s/releases' % repo
    r = requests.post(url,
                      params={
                          'access_token': token,
                      },
                      json={
                          'tag_name': 'v%s' % version,
                          'name': str(version),
                          'body': description,
                      })
    if r.status_code != 201:
        raise HttpApiError('Failed to create github release %s' % repo, url,
                           r.status_code, r.json())
    logger.info('Created GitHub release')


def release(category,
            path,
            description=None,
            changelog='CHANGELOG.md',
            version='VERSION',
            template=changelog_template,
            hooks={},
            token='GITHUB_TOKEN',
            git_executable=get_git_exe(),
            repo=None,
            date=datetime.utcnow(),
            logger=EmptyLogger()):
    '''
    Performs a release of a GitHub local repository. This automatically does the
    following steps:

        - Retrieves the git executable version and checks it is new enough
        - Gets the previous semantic version tag on the repository
        - Bumps the version according to the :code:`category`
        - Checks that no milestone is open in GitHub that corresponds to the
            version number and has open issues
        - Automatically creates a changelog with the :code:`description` and
            all closed issues and pull requests since the last release
        - Writes, or updates, the :code:`CHANGELOG.md` file
        - Writes the newly released version number to `VERSION`
        - Commits the changes and creates and annotated tag of the repository
        - Pushes the new commits and tag to GitHub
        - Creates a GitHub release attaching the changelog to the release tag
        - Closes the milestone that is associated with the version

    The following is sample output of a release of the :code:`pygh` project::

        TODO!

    :param str category: Must be one of :code:`major`, :code:`minor` or
        :code:`patch`
    :param str path: the path to the local repository to release
    :param str git_executable: the filesystem location of the
        :code:`git` executable to use
    :token str token: either the environment variable to read the token from or
        a 40 digit hexidecimal number
    :param str repo: the GitHub repository to close the milestone on,
        e.g. :code:`vcatechnology/pygh`. If set to :code:`None` it will be
        automatically detected from the :code:`origin` remote
    :param datetime date: the date the release occurred
    :param str description: the main description for the release,this will be
        included in the changelog, so should include major features and changes
        that have occurred since the last release
    :param str changelog: the name of the changelog file to write or update
    :param str version: the name of the version file to write or update
    :param str template: the mustache template to use for creating the changelog
    :param Logger logger: the logging class to use for providing status updates
    :param dict hooks: a set of function hooks that will be invoked as the
        release function runs:

            - :code:`changelog`: ran when the changelog has been generated
    '''
    logger.debug('Starting %r release' % category)

    git_version = get_git_version(git_executable=git_executable, logger=logger)
    if git_version < (1, 0, 0):
        raise ReleaseError('The version of git is too old %s' % git_version)

    previous_version = get_latest_git_tag_version(
        path=path,
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

    repo = repo or get_github_repo(path=path, git_executable=git_executable)
    description = description or 'The v%s release of %s' % (current_version,
                                                            repo.split('/')[1])

    milestone = get_version_milestone(version=current_version,
                                      repo=repo,
                                      token=token,
                                      logger=logger)
    if milestone:
        open_issues = milestone['open_issues']
        if open_issues:
            raise ReleaseError('The v%s milestone has %d open issues' %
                               (current_version, open_issues))

    changelog_data = create_changelog(description=description,
                                      path=path,
                                      repo=repo,
                                      date=date,
                                      token=token,
                                      git_executable=git_executable,
                                      current_version=current_version,
                                      previous_version=previous_version,
                                      template=template,
                                      logger=logger)

    changelog_data = hooks.get('changelog', lambda d: d)(changelog_data)

    write_changelog(path=os.path.join(path, changelog),
                    changelog=changelog_data,
                    logger=logger)

    commit_file(changelog,
                'Updated changelog for v%s' % current_version,
                git_executable=git_executable,
                logger=logger)

    write_version(path=os.path.join(path, version),
                  version=current_version,
                  logger=logger)

    commit_file(version,
                'Updated version to v%s' % current_version,
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
