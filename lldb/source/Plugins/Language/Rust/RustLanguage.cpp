//===-- RustLanguage.cpp ----------------------------------------*- C++ -*-===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//

// C Includes
#include <string.h>
// C++ Includes
#include <functional>
#include <mutex>

// Other libraries and framework includes
#include "llvm/ADT/StringRef.h"
#include "llvm/Support/Threading.h"

// Project includes
#include "Plugins/TypeSystem/Rust/TypeSystemRust.h"
#include "RustLanguage.h"
#include "lldb/Core/PluginManager.h"
#include "lldb/DataFormatters/DataVisualization.h"
#include "lldb/DataFormatters/FormattersHelpers.h"
#include "lldb/Utility/ConstString.h"

using namespace lldb;
using namespace lldb_private;
using namespace lldb_private::formatters;

LLDB_PLUGIN_DEFINE(RustLanguage)

void RustLanguage::Initialize() {
  PluginManager::RegisterPlugin(GetPluginNameStatic(), "Rust Language",
                                CreateInstance);
}

void RustLanguage::Terminate() {
  PluginManager::UnregisterPlugin(CreateInstance);
}

llvm::StringRef RustLanguage::GetPluginNameStatic() { return "Rust"; }

llvm::StringRef RustLanguage::GetPluginName() { return GetPluginNameStatic(); }

Language *RustLanguage::CreateInstance(lldb::LanguageType language) {
  if (language == eLanguageTypeRust)
    return new RustLanguage();
  return nullptr;
}

bool RustLanguage::IsSourceFile(llvm::StringRef file_path) const {
  return file_path.endswith(".rs");
}

bool RustLanguage::SymbolNameFitsToLanguage(Mangled name) const {
  const char *mangled_name = name.GetMangledName().GetCString();
  if (!mangled_name)
    return false;

  Mangled::ManglingScheme scheme = Mangled::GetManglingScheme(mangled_name);
  return scheme == Mangled::ManglingScheme::eManglingSchemeRustLegacy ||
         scheme == Mangled::ManglingScheme::eManglingSchemeRustV0;
}
