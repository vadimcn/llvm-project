//===--- RustLegacyDemangle.cpp ---------------------------------------*- C++
//-*-===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
//
// This file defines a demangler for Rust legacy mangled symbols
//
// See Rust implementation here:
// https://github.com/rust-lang/rustc-demangle/blob/af38dc6b06b5665c79a4778268e4faf5decd19df/src/legacy.rs
//
//===----------------------------------------------------------------------===//

#include "llvm/Demangle/Demangle.h"
#include "llvm/Demangle/StringViewExtras.h"
#include "llvm/Demangle/Utility.h"

using llvm::itanium_demangle::OutputBuffer;
using llvm::itanium_demangle::starts_with;

static inline bool isDigit(const char C) { return '0' <= C && C <= '9'; }

static inline bool isHexDigit(const char C) {
  return ('0' <= C && C <= '9') || ('a' <= C && C <= 'f');
}

static bool removeZNPrefix(std::string_view *Mangled) {
  if (starts_with(*Mangled, "__ZN")) {
    Mangled->remove_prefix(4);
    return true;
  } else if (starts_with(*Mangled, "_ZN")) {
    Mangled->remove_prefix(3);
    return true;
  } else if (starts_with(*Mangled, "ZN")) {
    Mangled->remove_prefix(2);
    return true;
  }
  return false;
}

static bool parsePathComponent(std::string_view Mangled,
                               std::string_view *Comp = nullptr,
                               std::string_view *Rest = nullptr) {
  size_t Len = 0;
  while (!Mangled.empty() && isDigit(Mangled[0])) {
    Len = Len * 10 + Mangled[0] - '0';
    Mangled.remove_prefix(1);
  }
  if (Len > 0 && Len <= Mangled.length()) {
    if (Comp)
      *Comp = Mangled.substr(0, Len);
    if (Rest)
      *Rest = Mangled.substr(Len);
    return true;
  }
  return false;
}

// Check whether M looks like a Rust hash, i.e. 'h' followed by 16 hex digits.
static bool isRustHash(std::string_view M) {
  if (M.length() != 17 || M[0] != 'h')
    return false;
  for (size_t i = 1; i < 17; ++i) {
    if (!isHexDigit(M[i]))
      return false;
  }
  return true;
}

bool llvm::isRustLegacyEncoding(std::string_view Mangled) {
  if (!removeZNPrefix(&Mangled))
    return false;

  if (Mangled.length() <= 18)
    return false;

  // Rust symbols end with "h<16 hex digits>E"
  Mangled.remove_prefix(Mangled.length() - 18);
  Mangled.remove_suffix(1);

  return isRustHash(Mangled);
}

char *llvm::rustLegacyDemangle(std::string_view Mangled) {
  if (!removeZNPrefix(&Mangled))
    return nullptr;

  OutputBuffer Demangled;
  std::string_view Comp;
  while (parsePathComponent(Mangled, &Comp, &Mangled)) {

    if (!Mangled.empty() && Mangled[0] == 'E' && isRustHash(Comp)) {
      break;
    }

    if (!Demangled.empty())
      Demangled << "::";

    if (starts_with(Comp, "_$"))
      Comp.remove_prefix(1);

    while (!Comp.empty()) {
      if (starts_with(Comp, "..")) {
        Demangled << "::";
        Comp.remove_prefix(2);
        continue;
      } else if (Comp[0] == '$') {
        if (starts_with(Comp, "$SP$")) {
          Demangled << '@';
          Comp.remove_prefix(4);
          continue;
        } else if (starts_with(Comp, "$BP$")) {
          Demangled << '*';
          Comp.remove_prefix(4);
          continue;
        } else if (starts_with(Comp, "$RF$")) {
          Demangled << '&';
          Comp.remove_prefix(4);
          continue;
        } else if (starts_with(Comp, "$LT$")) {
          Demangled << '<';
          Comp.remove_prefix(4);
          continue;
        } else if (starts_with(Comp, "$GT$")) {
          Demangled << '>';
          Comp.remove_prefix(4);
          continue;
        } else if (starts_with(Comp, "$LP$")) {
          Demangled << '(';
          Comp.remove_prefix(4);
          continue;
        } else if (starts_with(Comp, "$RP$")) {
          Demangled << ')';
          Comp.remove_prefix(4);
          continue;
        } else if (starts_with(Comp, "$C$")) {
          Demangled << ',';
          Comp.remove_prefix(3);
          continue;
        } else if (starts_with(Comp, "$u")) {
          Comp.remove_prefix(2);
          uint32_t code = 0;
          while (!Comp.empty() && isHexDigit(Comp[0])) {
            code = code * 16 +
                   (Comp[0] < 'a' ? Comp[0] - '0' : Comp[0] - 'a' + 0x0A);
            Comp.remove_prefix(1);
          }
          if (!Comp.empty() && Comp[0] == '$') {
            Demangled << static_cast<char>(code);
            Comp.remove_prefix(1);
            continue;
          }
        }
      }

      Demangled << Comp[0];
      Comp.remove_prefix(1);
    }
  }
  Demangled << '\0';

  return Demangled.getBuffer();
}
