cmake_minimum_required(VERSION 3.12.0)
project(build-lldb)

set(PYTHON_STANDALONE FALSE CACHE PATH "")
set(RELEASE_PACKAGE FALSE CACHE BOOL "")

include(ExternalProject)

if (${CMAKE_SYSTEM_NAME} STREQUAL "Windows" AND NOT CMAKE_TOOLCHAIN_FILE)
    set(CMAKE_TOOLCHAIN_FILE ${CMAKE_CURRENT_SOURCE_DIR}/toolchain-x86_64-windows-msvc.cmake)
    include(${CMAKE_TOOLCHAIN_FILE})
endif()

if (NOT TARGET_TRIPLE)
    if (${CMAKE_SYSTEM_NAME} STREQUAL "Darwin")
        set(TARGET_TRIPLE ${CMAKE_SYSTEM_PROCESSOR}-apple-darwin)
    else()
        set(TARGET_TRIPLE ${CMAKE_SYSTEM_PROCESSOR}-$<LOWER_CASE:${CMAKE_SYSTEM_NAME}>-gnu)
    endif()
endif()

set(WithEnv ${CMAKE_COMMAND} -E env)

externalproject_add(swig
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

externalproject_add(libxml2
    GIT_REPOSITORY https://github.com/robotology-dependencies/libxml2-cmake-buildsystem.git
    GIT_TAG master
    UPDATE_COMMAND ""
    CMAKE_ARGS
        -DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE}
        -DCMAKE_BUILD_TYPE=MinSizeRel
        -DCMAKE_C_COMPILER_LAUNCHER=${CMAKE_C_COMPILER_LAUNCHER}
        -DCMAKE_CXX_COMPILER_LAUNCHER=${CMAKE_CXX_COMPILER_LAUNCHER}
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

# Python
set(PythonDist ${CMAKE_BINARY_DIR}/python-dist)
if (${CMAKE_SYSTEM_NAME} STREQUAL "Linux")
    if (CMAKE_CROSSCOMPILING)
        set(Python3_EXECUTABLE ${CMAKE_BINARY_DIR}/host_python/install/bin/python3)
        set(Python3_INCLUDE_DIRS ${CMAKE_BINARY_DIR}/python/install/include/python3.8)
        set(Python3_LIBRARIES ${PythonDist}/lib/libpython38.so)

        add_custom_command(OUTPUT ${PythonDist}/lib/libpython38.so
            DEPENDS ${CMAKE_SOURCE_DIR}/packaging/python.py
            COMMAND zstd -dcf ${PYTHON_STANDALONE}/cpython-*-x86_64-*.tar.zst | tar --directory=${CMAKE_BINARY_DIR} -xf -
            COMMAND rm -rf ${CMAKE_BINARY_DIR}/host_python
            COMMAND mv ${CMAKE_BINARY_DIR}/python ${CMAKE_BINARY_DIR}/host_python
            COMMAND zstd -dcf ${PYTHON_STANDALONE}/cpython-*-${CMAKE_SYSTEM_PROCESSOR}-*.tar.zst | tar --directory=${CMAKE_BINARY_DIR} -xf -
            COMMAND ${WithEnv} PYTHONPATH=${CMAKE_SOURCE_DIR}
                        ${Python3_EXECUTABLE} -m packaging.python
                            --python_dist=${CMAKE_BINARY_DIR}/python
                            --target=${TARGET_TRIPLE}
                            --cc=${CMAKE_C_COMPILER}
                            --strip=${CMAKE_STRIP}
                            --output=${PythonDist}
        )
    else()
        set(Python3_EXECUTABLE ${CMAKE_BINARY_DIR}/python/install/bin/python3)
        set(Python3_INCLUDE_DIRS ${CMAKE_BINARY_DIR}/python/install/include/python3.8)
        set(Python3_LIBRARIES ${PythonDist}/lib/libpython38.so)

        add_custom_command(OUTPUT ${PythonDist}/lib/libpython38.so
            DEPENDS ${CMAKE_SOURCE_DIR}/packaging/python.py
            COMMAND zstd -dcf ${PYTHON_STANDALONE}/cpython-*-x86_64-*.tar.zst | tar --directory=${CMAKE_BINARY_DIR} -xf -
            COMMAND ${WithEnv} PYTHONPATH=${CMAKE_SOURCE_DIR}
                        ${Python3_EXECUTABLE} -m packaging.python
                            --python_dist=${CMAKE_BINARY_DIR}/python
                            --target=${TARGET_TRIPLE}
                            --cc=${CMAKE_C_COMPILER}
                            --strip=${CMAKE_STRIP}
                            --output=${PythonDist}
        )
    endif()
    add_custom_target(python DEPENDS ${PythonDist}/lib/libpython38.so)
elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Darwin")
    set(Python3_EXECUTABLE ${CMAKE_BINARY_DIR}/python/install/bin/python3)
    set(Python3_INCLUDE_DIRS ${CMAKE_BINARY_DIR}/python/install/include/python3.8)
    set(Python3_LIBRARIES ${PythonDist}/lib/libpython38.dylib)

    add_custom_command(OUTPUT ${PythonDist}/lib/libpython38.dylib
        DEPENDS ${CMAKE_SOURCE_DIR}/packaging/python.py
        COMMAND zstd -dcf ${PYTHON_STANDALONE}/cpython-*-x86_64-*.tar.zst | tar --directory=${CMAKE_BINARY_DIR} -xf -
        COMMAND ${WithEnv} PYTHONPATH=${CMAKE_SOURCE_DIR}
                    ${Python3_EXECUTABLE} -m packaging.python
                        --python_dist=${CMAKE_BINARY_DIR}/python
                        --target=${TARGET_TRIPLE}
                        --output=${PythonDist}
    )
    add_custom_target(python DEPENDS ${PythonDist}/lib/libpython38.dylib)
elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Windows")
    set(Python3_EXECUTABLE ${CMAKE_BINARY_DIR}/python/install/python.exe)
    set(Python3_INCLUDE_DIRS ${CMAKE_BINARY_DIR}/python/install/include)
    set(Python3_LIBRARIES ${CMAKE_BINARY_DIR}/python/install/libs/python38.lib)

    add_custom_command(OUTPUT ${PythonDist}/bin/python38.dll
        DEPENDS ${CMAKE_SOURCE_DIR}/packaging/python.py
        COMMAND zstd -dcf ${PYTHON_STANDALONE}/cpython-*-x86_64-*.tar.zst | tar --directory=${CMAKE_BINARY_DIR} -xf -
        COMMAND ${WithEnv} PYTHONPATH=${CMAKE_SOURCE_DIR}
                    ${Python3_EXECUTABLE} -m packaging.python
                        --target=${TARGET_TRIPLE}
                        --python_dist=${CMAKE_BINARY_DIR}/python
                        --output=${PythonDist}
    )
    add_custom_target(python DEPENDS ${PythonDist}/bin/python38.dll)
endif()
    

#---------------------------------------------------------------------

set(LLVM_ENABLE_PROJECTS clang libcxx lldb)
set(LLVM_TARGETS_TO_BUILD X86 AArch64 ARM)
set(LIBXML2_INCLUDE_DIR ${CMAKE_BINARY_DIR}/libxml2/include/libxml2)
set(LIBXML2_LIBRARY ${CMAKE_BINARY_DIR}/libxml2/lib/libxml2.a)
set(SWIG_EXECUTABLE ${CMAKE_BINARY_DIR}/swig/swig)
set(BuildTargets lldb llvm-dwarfdump llvm-pdbutil llvm-readobj)

if (${CMAKE_SYSTEM_NAME} STREQUAL "Linux")
    set(BuildTargets ${BuildTargets} lldb-server)
    set(CMakeArgs ${CMakeArgs} 
        "-DCMAKE_CXX_FLAGS=-static-libstdc++ -static-libgcc"
        -DCMAKE_EXE_LINKER_FLAGS=-L${CMAKE_BINARY_DIR}/python/build/lib
        -DCMAKE_SHARED_LINKER_FLAGS=-L${CMAKE_BINARY_DIR}/python/build/lib
        -DLLVM_ENABLE_ZLIB=FORCE_ON
    )
    if (CMAKE_CROSSCOMPILING)
        set(CMakeArgs ${CMakeArgs} 
            -DCMAKE_CROSSCOMPILING=${CMAKE_CROSSCOMPILING}
            -DLLVM_TARGET_ARCH=${CMAKE_SYSTEM_PROCESSOR}
            -DLLVM_HOST_TRIPLE=${TARGET_TRIPLE}
        )
    endif()
elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Darwin")
    set(CMakeArgs ${CMakeArgs} 
        -DLLDB_USE_SYSTEM_DEBUGSERVER=TRUE
        -DLLVM_ENABLE_ZLIB=FORCE_ON
    )
elseif (${CMAKE_SYSTEM_NAME} STREQUAL "Windows")
    set(LIBXML2_LIBRARY ${CMAKE_BINARY_DIR}/libxml2/lib/xml2.lib)
endif()

string(JOIN "$<SEMICOLON>" LLVM_ENABLE_PROJECTS ${LLVM_ENABLE_PROJECTS})
string(JOIN "$<SEMICOLON>" LLVM_TARGETS_TO_BUILD ${LLVM_TARGETS_TO_BUILD})
string(JOIN "$<SEMICOLON>" Python3_INCLUDE_DIRS ${Python3_INCLUDE_DIRS})
string(JOIN "$<SEMICOLON>" Python3_LIBRARIES ${Python3_LIBRARIES})

set(CMakeArgs ${CMakeArgs}
    -DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE}
    -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
    -DCMAKE_C_COMPILER_LAUNCHER=${CMAKE_C_COMPILER_LAUNCHER}
    -DCMAKE_CXX_COMPILER_LAUNCHER=${CMAKE_CXX_COMPILER_LAUNCHER}
    -DLLVM_ENABLE_PROJECTS=${LLVM_ENABLE_PROJECTS}
    -DLLVM_TARGETS_TO_BUILD=${LLVM_TARGETS_TO_BUILD}
    -DLLVM_PARALLEL_LINK_JOBS=1
    -DLLVM_VERSION_SUFFIX=-custom
    -DLLVM_APPEND_VC_REV=FALSE
    -DLLVM_ENABLE_TERMINFO=FALSE
    -DLLVM_ENABLE_LIBXML2=FORCE_ON
    -DLLVM_LIBXML2_ENABLED=TRUE
    -DLLDB_ENABLE_PYTHON=TRUE
    -DLLDB_EMBED_PYTHON_HOME=TRUE
    -DLLDB_PYTHON_HOME=..
    -DLLDB_PYTHON_RELATIVE_PATH=lib/lldb-python
    -DLLDB_ENABLE_LIBEDIT=FALSE
    -DLLDB_ENABLE_CURSES=FALSE
    -DLLDB_ENABLE_LZMA=FALSE
    -DPYTHON_EXECUTABLE=${Python3_EXECUTABLE}
    -DPYTHON_INCLUDE_DIRS=${Python3_INCLUDE_DIRS}
    -DPYTHON_LIBRARIES=${Python3_LIBRARIES}
    -DSWIG_EXECUTABLE=${SWIG_EXECUTABLE}
    -DSWIG_DIR=${CMAKE_BINARY_DIR}/swig
    -DLIBXML2_INCLUDE_DIR=${LIBXML2_INCLUDE_DIR}
    -DLIBXML2_LIBRARY=${LIBXML2_LIBRARY}
)

message("CMakeArgs: ${CMakeArgs}")

set(CROSS_TOOLCHAIN_FLAGS_NATIVE 
    -DLLDB_ENABLE_LIBEDIT=FALSE
    -DLLDB_ENABLE_CURSES=FALSE
    -DLLDB_ENABLE_PYTHON=FALSE
)
string(JOIN "$<SEMICOLON>" CROSS_TOOLCHAIN_FLAGS_NATIVE ${CROSS_TOOLCHAIN_FLAGS_NATIVE})


foreach(Target ${BuildTargets})
    set(BuildCommands ${BuildCommands} 
        COMMAND ${CMAKE_COMMAND} -E env "SWIG_LIB=${CMAKE_BINARY_DIR}/swig/Lib" 
                ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR}/lldb --target ${Target} -- -v)
endforeach()

externalproject_add(lldb
    DEPENDS python libxml2 swig
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

add_custom_target(package_lldb DEPENDS python lldb
    COMMAND ${WithEnv} PYTHONPATH=${CMAKE_SOURCE_DIR} 
                ${Python3_EXECUTABLE} -m packaging.lldb
                    --lldb_root=${CMAKE_BINARY_DIR}/lldb 
                    --python_dist=${PythonDist}
                    --target=${TARGET_TRIPLE}  
                    --strip=${CMAKE_STRIP} $<$<BOOL:${RELEASE_PACKAGE}>:--release_package>
                    --output=${CMAKE_BINARY_DIR}/lldb--${TARGET_TRIPLE}.zip 
                    --debug_output=${CMAKE_BINARY_DIR}/lldb-debug--${TARGET_TRIPLE}.zip
)
