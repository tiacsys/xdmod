# Shared zdocs consumer block for every repo that uses XDMOD (port of the spike's mbse-docs.cmake).
#
# In <repo>/docs/CMakeLists.txt:
#   cmake_minimum_required(VERSION 3.20.0)
#   project(<repo>-docs LANGUAGES)
#   find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE} COMPONENTS doc)
#   execute_process(COMMAND west topdir OUTPUT_VARIABLE WEST_TOPDIR
#                   OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
#   include(${WEST_TOPDIR}/xdmod/cmake/xdmod-docs.cmake)
#   xdmod_docs(REGISTRY ${CMAKE_CURRENT_LIST_DIR}/documents.yaml PROJECT_BASE ${CMAKE_CURRENT_LIST_DIR}/..)
#
# Strict build (D64c): `curatrix docs` passes -DZDOCS_STRICT=ON when the zdocs checkout supports it
# (zdocs PR #36, strict mode reported in the doc-check gate), else -W --keep-going as Sphinx
# options plus `ninja -k 0`, so every document reports. A plain cmake call without curatrix gets
# -W --keep-going by default.
if(NOT DEFINED ZDOCS_STRICT)
  set(ZDOCS_SPHINXOPTS_EXTRA "-W;--keep-going" CACHE STRING "Extra Sphinx options (strict, D64c)")
endif()

function(xdmod_docs)
  cmake_parse_arguments(A "" "REGISTRY;PROJECT_BASE" "" ${ARGN})
  execute_process(COMMAND west topdir OUTPUT_VARIABLE WEST_TOPDIR
                  OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
  set(ZDOCS_PROJECT_BASE ${A_PROJECT_BASE})
  set(ZDOCS_WEST_TOPDIR ${WEST_TOPDIR})
  # One shared needs configuration for every document (trace-model.md §1 principle 7).
  set(ZDOCS_NEEDS_CONFIG ${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../needs/needs_config.toml)
  list(APPEND CMAKE_MODULE_PATH ${ZEPHYR_ZDOCS_MODULE_DIR}/cmake)
  include(zdocs)
  add_docs_from_registry(REGISTRY ${A_REGISTRY})
  add_doc_check(REGISTRY ${A_REGISTRY})
endfunction()
