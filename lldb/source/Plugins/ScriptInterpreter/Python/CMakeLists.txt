if(NOT LLDB_PYTHON_RELATIVE_PATH)
  message(FATAL_ERROR "LLDB_PYTHON_RELATIVE_PATH is not set.")
endif()
add_definitions(-DLLDB_PYTHON_RELATIVE_LIBDIR="${LLDB_PYTHON_RELATIVE_PATH}")

if (NOT CMAKE_SYSTEM_NAME MATCHES "Windows")
  set(PYTHON_LIBRARY "") # Don't actually link to the python lib, except on Windows.
endif()

add_lldb_library(lldbPluginScriptInterpreterPython PLUGIN
  PythonDataObjects.cpp
  PythonExceptionState.cpp
  PythonReadline.cpp
  ScriptInterpreterPython.cpp

  LINK_LIBS
    lldbBreakpoint
    lldbCore
    lldbDataFormatters
    lldbHost
    lldbInterpreter
    lldbTarget
    ${PYTHON_LIBRARY}

  LINK_COMPONENTS
    Support
  )
