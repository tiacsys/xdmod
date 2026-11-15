# Docs build of xdmod: the XDMOD manual and the curatrix reference (D13, doc-architecture.md §2).
# Run from the workspace root: `curatrix docs xdmod` (strict, output in build/xdmod/docs/).
cmake_minimum_required(VERSION 3.20.0)
project(xdmod-docs LANGUAGES)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE} COMPONENTS doc)
execute_process(COMMAND west topdir OUTPUT_VARIABLE WEST_TOPDIR
                OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
include(${WEST_TOPDIR}/xdmod/cmake/xdmod-docs.cmake)
xdmod_docs(REGISTRY ${CMAKE_CURRENT_LIST_DIR}/documents.yaml PROJECT_BASE ${CMAKE_CURRENT_LIST_DIR}/..)
