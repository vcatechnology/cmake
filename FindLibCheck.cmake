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
# This module defines :prop_tgt:`IMPORTED` target ``Check::LibCheck``, if
# LIBCHECK has been found. On certain systems the
# :prop_tgt:`IMPORTED` target ``Check::LibCompat`` is also defined
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
#
# Hints
# ^^^^^
#
# A user may set ``LIBCHECK_ROOT`` to a check installation root to tell this
# module where to look.

include(FindPackageHandleStandardArgs)

find_path(LIBCHECK_INCLUDE_DIRS
  NAMES check.h
  PATHS ${LIBCHECK_ROOT}/include/
)
find_library(LIBCHECK_LIBRARY
  NAMES check
  PATHS ${LIBCHECK_ROOT}/lib/
)
find_package_handle_standard_args(LibCheck DEFAULT_MSG LIBCHECK_LIBRARY LIBCHECK_INCLUDE_DIRS)

if(WIN32)
  find_path(LIBCOMPAT_INCLUDE_DIRS
    NAMES compat.h
    PATHS ${LIBCHECK_ROOT}/include/
  )
  find_library(LIBCOMPAT_LIBRARY
    NAMES compat
    PATHS ${LIBCHECK_ROOT}/lib/
  )
  find_package_handle_standard_args(LibCompat DEFAULT_MSG LIBCOMPAT_LIBRARY LIBCOMPAT_INCLUDE_DIRS)
endif()

# Build from source if not found
if(NOT LIBCHECK_FOUND)
  # We need a version of libcheck to build if not found
  set(LIBCHECK_VERSION 0.10.0 CACHE STRING
    "The version of Check unit testing framework to build and include statically")
  set_property(CACHE LIBCHECK_VERSION PROPERTY VALUE ${LIBCHECK_VERSION})
  mark_as_advanced(LIBCHECK_VERSION)

  # The hash of the downloaded data
  set(LIBCHECK_MD5_HASH 53c5e5c77d090e103a17f3ed7fd7d8b8 CACHE STRING
    "The hash of Check unit testing framework archive to be downloaded")
  set_property(CACHE LIBCHECK_MD5_HASH PROPERTY VALUE ${LIBCHECK_MD5_HASH})
  mark_as_advanced(LIBCHECK_MD5_HASH)

  # Remove the previously set variables
  unset(LIBCHECK_LIBRARY)
  unset(LIBCHECK_INCLUDE_DIRS)
  unset(LIBCOMPAT_LIBRARY)
  unset(LIBCOMPAT_INCLUDE_DIRS)

  # Determine if the user would like to see the build
  if(CMAKE_ENABLE_THIRD_PARTY_OUTPUT)
    set(THIRD_PARTY_LOGGING 0)
  else()
    set(THIRD_PARTY_LOGGING 1)
  endif()

  # The user can specify an output location
  if(CMAKE_THIRD_PARTY_DIR)
    set(THIRD_PARTY_DIR "${CMAKE_THIRD_PARTY_DIR}")
  else()
    set(THIRD_PARTY_DIR third-party)
  endif()

  # Build libcheck
  include(ExternalProject)
  message(STATUS "Building check from source - ${LIBCHECK_VERSION}")
  ExternalProject_Add(libcheck
    URL "https://downloads.sourceforge.net/project/check/check/${LIBCHECK_VERSION}/check-${LIBCHECK_VERSION}.tar.gz"
    URL_MD5 ${LIBCHECK_MD5_HASH}
    PREFIX ${THIRD_PARTY_DIR}
    BUILD_IN_SOURCE 1
    CMAKE_ARGS
      "-DCMAKE_BUILD_TYPE=Release"
      "-DCMAKE_C_COMPILER=${CMAKE_C_COMPILER}"
      "-DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>"
    LOG_DOWNLOAD ${THIRD_PARTY_LOGGING}
    LOG_UPDATE ${THIRD_PARTY_LOGGING}
    LOG_CONFIGURE ${THIRD_PARTY_LOGGING}
    LOG_BUILD ${THIRD_PARTY_LOGGING}
    LOG_TEST ${THIRD_PARTY_LOGGING}
    LOG_INSTALL ${THIRD_PARTY_LOGGING})

  # Set up the root of the project
  ExternalProject_Get_Property(libcheck INSTALL_DIR)
  set(LIBCHECK_ROOT ${INSTALL_DIR})
  unset(INSTALL_DIR)

  # Create the folders so that the find_package command succeeds
  file(MAKE_DIRECTORY ${LIBCHECK_ROOT}/include/)
  file(MAKE_DIRECTORY ${LIBCHECK_ROOT}/lib/)

  # Set the include directories
  set(LIBCHECK_INCLUDE_DIRS "${LIBCHECK_ROOT}/include")

  # We cannot use find_libary here because the libcheck isn't actually built until build time so will fail
  if (WIN32 AND MINGW)
    set(LIBCHECK_LIBRARY "${LIBCHECK_ROOT}/lib/libcheck.a")
    set(LIBCOMPAT_LIBRARY "${LIBCHECK_ROOT}/lib/libcompat.a")
    set(LIBCOMPAT_INCLUDE_DIRS ${LIBCHECK_INCLUDE_DIRS})
  elseif (WIN32)
    set(LIBCHECK_LIBRARY "${LIBCHECK_ROOT}/lib/check.lib;")
    set(LIBCOMPAT_LIBRARY "${LIBCHECK_ROOT}/lib/compat.lib")
    set(LIBCOMPAT_INCLUDE_DIRS ${LIBCHECK_INCLUDE_DIRS})
  else()
    set(LIBCHECK_LIBRARY "${LIBCHECK_ROOT}/lib/libcheck.a")
  endif()

  # Do the normal finding of the package
  find_package_handle_standard_args(LibCheck DEFAULT_MSG LIBCHECK_LIBRARY LIBCHECK_INCLUDE_DIRS)
  if(WIN32)
    find_package_handle_standard_args(LibCompat DEFAULT_MSG LIBCOMPAT_LIBRARY LIBCOMPAT_INCLUDE_DIRS)
  endif()
endif()

# Set up the libraries list correctly with all dependencies
set(LIBCHECK_LIBRARIES ${LIBCHECK_LIBRARY})
if(NOT LIBCOMPAT_FOUND)
  list(APPEND LIBCHECK_LIBRARIES ${LIBCOMPAT_LIBRARY})
endif()
find_package(LibM)
if (LIBM_FOUND)
  list(APPEND LIBCHECK_LIBRARIES ${LIBM_LIBRARIES})
endif()
find_package(LibRt)
if (LIBRT_FOUND)
  list(APPEND LIBCHECK_LIBRARIES ${LIBRT_LIBRARIES})
endif()

# Make these variables as advanced as they shouldn't really be modified
mark_as_advanced(LIBCHECK_BUILT_FROM_SOURCE LIBCHECK_INCLUDE_DIRS LIBCHECK_LIBRARIES)

# Set up the imported target for libcheck
if(NOT TARGET Check::LibCheck)
  add_library(Check::LibCheck STATIC IMPORTED)
  set_target_properties(Check::LibCheck PROPERTIES
    IMPORTED_LOCATION ${LIBCHECK_LIBRARY}
    INTERFACE_INCLUDE_DIRECTORIES "${LIBCHECK_INCLUDE_DIRS}")
  add_dependencies(Check::LibCheck libcheck)
endif()

# Set up the imported target for libcompat if found
if((LIBCOMPAT_LIBRARY) AND (NOT TARGET Check::LibCompat))
  add_library(Check::LibCompat STATIC IMPORTED)
  set_target_properties(Check::LibCompat PROPERTIES
    IMPORTED_LOCATION ${LIBCOMPAT_LIBRARY}
    INTERFACE_INCLUDE_DIRECTORIES "${LIBCOMPAT_INCLUDE_DIRS}")
  add_dependencies(Check::LibCompat libcheck)
endif()

# Remove the library variables as the user can use the IMPORTED_* variable from the imported target libraries
unset(LIBCHECK_LIBRARY)
unset(LIBCOMPAT_LIBRARY)
