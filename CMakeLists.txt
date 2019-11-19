cmake_minimum_required(VERSION 3.12.0)
project(build-lldb)

include(ExternalProject)
include(FindPythonInterp)


if (${CMAKE_SYSTEM_NAME} STREQUAL "Linux" AND ${CMAKE_SYSTEM_PROCESSOR} STREQUAL "aarch64")
    set(CMakeTargetCompiler
        -DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc
        -DCMAKE_CXX_COMPILER=aarch64-linux-gnu-g++
    )
elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Windows")
    set(CMakeTargetCompiler 
        -DCMAKE_C_COMPILER=cl
        -DCMAKE_CXX_COMPILER=cl
    )
endif()

ExternalProject_Add(swig
    GIT_REPOSITORY https://github.com/vadimcn/swig.git
    GIT_TAG py3-stable-abi
    SOURCE_DIR ${CMAKE_BINARY_DIR}/swig
    UPDATE_COMMAND ""
    CONFIGURE_COMMAND bash ./autogen.sh
              COMMAND bash ./configure --prefix=${CMAKE_BINARY_DIR}/swig
    BUILD_COMMAND make
    BUILD_IN_SOURCE ON
    INSTALL_COMMAND ""
    STEP_TARGETS configure build
    USES_TERMINAL_CONFIGURE TRUE
    USES_TERMINAL_BUILD TRUE
)

ExternalProject_Add(libxml2
    GIT_REPOSITORY https://github.com/robotology-dependencies/libxml2-cmake-buildsystem.git
    GIT_TAG master
    UPDATE_COMMAND ""
    CMAKE_ARGS 
        ${CMakeTargetCompiler}
        -DCMAKE_SYSTEM_NAME=${CMAKE_SYSTEM_NAME}
        -DCMAKE_SYSTEM_PROCESSOR=${CMAKE_SYSTEM_PROCESSOR}
        -DCMAKE_BUILD_TYPE=MinSizeRel
        $<$<NOT:$<PLATFORM_ID:Windows>>:-DCMAKE_C_FLAGS=-fPIC>
        -DCMAKE_INSTALL_PREFIX=${CMAKE_BINARY_DIR}/libxml2
        -DBUILD_SHARED_LIBS=OFF 
        -DLIBXML2_WITH_SAX1=ON 
        -DLIBXML2_WITH_THREADS=ON 
        -DLIBXML2_WITH_TREE=OFF
        -DLIBXML2_WITH_OUTPUT=OFF
        -DLIBXML2_WITH_XPATH=OFF
        -DLIBXML2_WITH_FEXCEPTIONS=OFF 
        -DLIBXML2_WITH_FTP=OFF 
        -DLIBXML2_WITH_HISTORY=OFF 
        -DLIBXML2_WITH_HTML=OFF 
        -DLIBXML2_WITH_HTTP=OFF 
        -DLIBXML2_WITH_ICONV=OFF 
        -DLIBXML2_WITH_ICU=OFF 
        -DLIBXML2_WITH_ISO8859X=OFF 
        -DLIBXML2_WITH_LEGACY=OFF 
        -DLIBXML2_WITH_LZMA=OFF
        -DLIBXML2_WITH_MEM_DEBUG=OFF 
        -DLIBXML2_WITH_MINIMUM=OFF 
        -DLIBXML2_WITH_MODULES=OFF 
        -DLIBXML2_WITH_PATTERN=OFF 
        -DLIBXML2_WITH_PUSH=OFF 
        -DLIBXML2_WITH_READER=OFF 
        -DLIBXML2_WITH_REGEXPS=OFF 
        -DLIBXML2_WITH_RUN_DEBUG=OFF 
        -DLIBXML2_WITH_SCHEMAS=OFF 
        -DLIBXML2_WITH_SCHEMATRON=OFF 
        -DLIBXML2_WITH_THREAD_ALLOC=OFF 
        -DLIBXML2_WITH_VALID=OFF 
        -DLIBXML2_WITH_WRITER=OFF 
        -DLIBXML2_WITH_XINCLUDE=OFF 
        -DLIBXML2_WITH_XPTR=OFF 
        -DLIBXML2_WITH_ZLIB=OFF 
    STEP_TARGETS configure build
    USES_TERMINAL_CONFIGURE TRUE
    USES_TERMINAL_BUILD TRUE
)

#---------------------------------------------------------------------

set(LLVM_ENABLE_PROJECTS clang libcxx lldb)
set(LLVM_TARGETS_TO_BUILD X86 AArch64 ARM)
set(LIBXML2_INCLUDE_DIR ${CMAKE_BINARY_DIR}/libxml2/include/libxml2)
set(LIBXML2_LIBRARY ${CMAKE_BINARY_DIR}/libxml2/lib/libxml2.a)
set(SWIG_EXECUTABLE ${CMAKE_BINARY_DIR}/swig/swig)
set(BuildTargets lldb)

find_package (Python3 COMPONENTS Interpreter Development)
if (${CMAKE_SYSTEM_NAME} STREQUAL "Linux")
    set(BuildTargets ${BuildTargets} lldb-server)
    set(CMakeArgs ${CMakeArgs} 
        "-DCMAKE_CXX_FLAGS=-static-libstdc++ -static-libgcc"
    )
    if (${CMAKE_SYSTEM_PROCESSOR} STREQUAL "aarch64")
        string(REPLACE "x86_64" "aarch64" Python3_LIBRARIES ${Python3_LIBRARIES})
        
        set(CMakeArgs ${CMakeArgs} 
            -DCMAKE_SYSTEM_NAME=${CMAKE_SYSTEM_NAME}
            -DCMAKE_SYSTEM_PROCESSOR=${CMAKE_SYSTEM_PROCESSOR}
            -DCMAKE_CROSSCOMPILING=TRUE
            -DLLVM_TARGET_ARCH=aarch64
            -DLLVM_HOST_TRIPLE=aarch64-unknown-linux-gnu
        )
    endif()
elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Darwin")
    set(CMakeArgs ${CMakeArgs} 
        -DLLDB_USE_SYSTEM_DEBUGSERVER=TRUE
    )
elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Windows")
    get_filename_component(PYTHON_HOME ${Python3_EXECUTABLE} DIRECTORY)
    set(Python3_LIBRARIES "${PYTHON_HOME}/libs/python3.lib")
    set(LIBXML2_LIBRARY ${CMAKE_BINARY_DIR}/libxml2/lib/xml2.lib)
endif()
message("Python3_EXECUTABLE: ${Python3_EXECUTABLE}  Python3_INCLUDE_DIRS: ${Python3_INCLUDE_DIRS}  Python3_LIBRARIES: ${Python3_LIBRARIES}")


string(JOIN "$<SEMICOLON>" LLVM_ENABLE_PROJECTS ${LLVM_ENABLE_PROJECTS})
string(JOIN "$<SEMICOLON>" LLVM_TARGETS_TO_BUILD ${LLVM_TARGETS_TO_BUILD})

set(CMakeArgs ${CMakeArgs}
    ${CMakeTargetCompiler}
    -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
    -DLLVM_ENABLE_PROJECTS=${LLVM_ENABLE_PROJECTS}
    -DLLVM_TARGETS_TO_BUILD=${LLVM_TARGETS_TO_BUILD}
    -DLLVM_PARALLEL_LINK_JOBS=1
    -DLLVM_VERSION_SUFFIX=-custom
    -DLLVM_APPEND_VC_REV=FALSE
    -DLLVM_ENABLE_TERMINFO=FALSE
    -DLLVM_ENABLE_LIBXML2=FORCE_ON
    -DLLVM_LIBXML2_ENABLED=TRUE
    -DLLDB_RELOCATABLE_PYTHON=TRUE
    -DLLDB_DISABLE_CURSES=TRUE
    -DLLDB_DISABLE_LIBEDIT=TRUE
    -DPYTHON_EXECUTABLE=${Python3_EXECUTABLE}
    -DPYTHON_INCLUDE_DIR=${Python3_INCLUDE_DIRS}
    -DPYTHON_LIBRARY=${Python3_LIBRARIES}
    -DSWIG_EXECUTABLE=${SWIG_EXECUTABLE}
    -DSWIG_DIR=${CMAKE_BINARY_DIR}/swig
    -DLIBXML2_INCLUDE_DIR=${LIBXML2_INCLUDE_DIR}
    -DLIBXML2_LIBRARY=${LIBXML2_LIBRARY}
)

find_program(CCACHE_PROGRAM ccache)
if(CCACHE_PROGRAM)
    set(CMakeArgs ${CMakeArgs}
        -DLLVM_CCACHE_BUILD=TRUE
        -DLLVM_CCACHE_DIR=${CMAKE_BINARY_DIR}/.ccache
    )
endif()

message("CMakeArgs: ${CMakeArgs}")

set(CROSS_TOOLCHAIN_FLAGS_NATIVE 
    -DLLDB_DISABLE_LIBEDIT=TRUE
    -DLLDB_DISABLE_CURSES=TRUE
    -DLLDB_DISABLE_PYTHON=TRUE
)
string(JOIN "$<SEMICOLON>" CROSS_TOOLCHAIN_FLAGS_NATIVE ${CROSS_TOOLCHAIN_FLAGS_NATIVE})

foreach(Target ${BuildTargets})
    set(BuildCommands ${BuildCommands} 
        COMMAND ${CMAKE_COMMAND} -E env "SWIG_LIB=${CMAKE_BINARY_DIR}/swig/Lib"
                ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR}/lldb --target ${Target} -- -v)
endforeach()

ExternalProject_Add(lldb
    DEPENDS libxml2 swig 
    SOURCE_DIR ${CMAKE_SOURCE_DIR}/llvm
    BINARY_DIR ${CMAKE_BINARY_DIR}/lldb
    CMAKE_ARGS ${CMakeArgs}
               -DCROSS_TOOLCHAIN_FLAGS_NATIVE=${CROSS_TOOLCHAIN_FLAGS_NATIVE}
    BUILD_COMMAND ${BuildCommands}
    INSTALL_COMMAND ""
    STEP_TARGETS configure build
    BUILD_ALWAYS TRUE
    USES_TERMINAL_CONFIGURE TRUE
    USES_TERMINAL_BUILD TRUE
)
