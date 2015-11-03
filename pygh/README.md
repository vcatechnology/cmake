pygh
====

A set of GitHub related scripts that can perform certain useful tasks:

  - Release:
    - The scripts can perform a release of a GitHub project creating the
      necessary updated changelog and the release data on GitHub

Installation
------------

The script can be added to projects as a subtree to provide release capability
local to the project

```
git subtree add --squash --prefix pygh https://github.com/vcatechnology/pygh.git master
```

To update to a new version of the script, run the following command:

```
git subtree pull --squash --prefix pygh https://github.com/vcatechnology/pygh.git master
```

It is possible to replace the `master` in both commands with a version tag,
such as `v0.1.0`. If you would like to keep the whole history, omit the
`--squash` argument.

Usage
-----

Usually once the scripts have been imported a `release` python script is
created in the repository that performs the release. It does this by
`import pygh` and then using the `pygh.release` function. There is an
example script in the repository that performs the release for the `pygh`
project. The script will generally be used like so:

```
# Will bump the version from 1.2.2 to 1.2.3
./release patch
# Will bump the version from 1.2.2 to 1.3.0
./release minor
# Will bump the version from 1.2.2 to 2.0.0
./release major
```
