CMake Extensions
=====================

A set of extensions to be used to enhance the functionality of CMake. Intended
to be used as a subtree in a project:

```
git subtree add -prefix cmake https://github.com/vcatechnology/cmake.git master --squash
```

Then it is possible to use the modules by adding to the `CMAKE_MODULE_PATH`:

```
# Make sure we can import CMake extensions
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
```

To update to a new version of the extensions, run the following command:

```
git subtree pull --prefix cmake https://github.com/vcatechnology/cmake.git master --squash
```

It is possible to replace the `master` in both commands with a version tag, such as `0.1.0`.
