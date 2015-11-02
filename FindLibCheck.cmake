#.rst:
# FindLibCheck
# --------
#
# Find the check unit testing includes and library. It will build the check library
# from source if not found.
#
# IMPORTED Targets
# ^^^^^^^^^^^^^^^^
#
# This module defines :prop_tgt:`IMPORTED` target ``LIBCHECK::LIBCHECK``, if
# LIBCHECK has been found.
#
# Result Variables
# ^^^^^^^^^^^^^^^^
#
# This module defines the following variables:
#
# ::
#
#   LIBCHECK_INCLUDE_DIRS      - where to find check.h, etc.
#   LIBCHECK_LIBRARIES         - List of libraries when using libcheck.
#   LIBCHECK_FOUND             - True if check library found.
#   LIBCHECK_VERSION           - the version of libcheck that will be built from source
#   LIBCHECK_MD5_HASH          - the hash of the downloaded source code
#   LIBCHECK_BUILT_FROM_SOURCE - True if the check library was built from source
#
# Hints
# ^^^^^
#
# A user may set ``LIBCHECK_ROOT`` to a check installation root to tell this
# module where to look.

set(LIBCHECK_VERSION 0.10.0 CACHE STRING
  "The version of Check unit testing framework to build and include statically")
set_property(CACHE LIBCHECK_VERSION PROPERTY VALUE ${LIBCHECK_VERSION})
mark_as_advanced(LIBCHECK_VERSION)

set(LIBCHECK_MD5_HASH 53c5e5c77d090e103a17f3ed7fd7d8b8 CACHE STRING
  "The hash of Check unit testing framework archive to be downloaded")
set_property(CACHE LIBCHECK_MD5_HASH PROPERTY VALUE ${LIBCHECK_MD5_HASH})
mark_as_advanced(LIBCHECK_MD5_HASH)

find_path(LIBCHECK_INCLUDE_DIRS
  NAMES check.h
  PATHS ${LIBCHECK_ROOT}/include/
)
find_library(LIBCHECK_LIBRARIES check compat
  PATHS ${LIBCHECK_ROOT}/lib/
)
include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(LibCheck DEFAULT_MSG LIBCHECK_LIBRARIES LIBCHECK_INCLUDE_DIRS)

set(LIBCHECK_BUILT_FROM_SOURCE NO)
if((NOT LIBCHECK_FOUND))
    set(LIBCHECK_BUILT_FROM_SOURCE YES)
    include(ExternalProject)
    message(STATUS "Check Unit Testing Framework Version - ${LIBCHECK_VERSION}")
    ExternalProject_Add(libcheck
        URL "https://downloads.sourceforge.net/project/check/check/${LIBCHECK_VERSION}/check-${LIBCHECK_VERSION}.tar.gz"
        URL_MD5 ${LIBCHECK_MD5_HASH}
        PREFIX third-party
        BUILD_IN_SOURCE 1
        CMAKE_ARGS
          "-DCMAKE_BUILD_TYPE=Release"
          "-DCMAKE_C_COMPILER=${CMAKE_C_COMPILER}"
          "-DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>"
        LOG_DOWNLOAD 0
        LOG_UPDATE 0
        LOG_CONFIGURE 0
        LOG_BUILD 0
        LOG_TEST 0
        LOG_INSTALL 0)
    ExternalProject_Get_Property(libcheck INSTALL_DIR)
    set(LIBCHECK_ROOT ${INSTALL_DIR})
    unset(INSTALL_DIR)
    set(LIBCHECK_INCLUDE_DIRS "${LIBCHECK_ROOT}/include")
    file(MAKE_DIRECTORY ${LIBCHECK_ROOT}/include/)
    find_path(LIBCHECK_INCLUDE_DIRS
      NAMES check.h
      PATHS ${LIBCHECK_ROOT}/include/
    )
    find_library(LIBCHECK_LIBRARIES check compat
      PATHS ${LIBCHECK_ROOT}/lib/
    )
    include(FindPackageHandleStandardArgs)
    find_package_handle_standard_args(LibCheck DEFAULT_MSG LIBCHECK_LIBRARIES LIBCHECK_INCLUDE_DIRS)
endif()

mark_as_advanced(LIBCHECK_INCLUDE_DIRS LIBCHECK_LIBRARIES)

if(NOT TARGET LIBCHECK::LIBCHECK)
  add_library(LIBCHECK::LIBCHECK UNKNOWN IMPORTED)
  set_target_properties(LIBCHECK::LIBCHECK PROPERTIES
    IMPORTED_LOCATION "${LIBCHECK_LIBRARIES}"
    INTERFACE_INCLUDE_DIRECTORIES "${LIBCHECK_INCLUDE_DIRS}")
endif()
