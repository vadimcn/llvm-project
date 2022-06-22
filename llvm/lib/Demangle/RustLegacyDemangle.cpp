//===--- RustLegacyDemangle.cpp ---------------------------------------*- C++ -*-===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
//
// This file defines a demangler for Rust legacy mangled symbols
//
//===----------------------------------------------------------------------===//

#include "llvm/Demangle/Demangle.h"
#include "llvm/Demangle/StringView.h"
#include "llvm/Demangle/Utility.h"

using llvm::itanium_demangle::OutputBuffer;

static inline bool isDigit(const char C) { return '0' <= C && C <= '9'; }

static inline bool isHexDigit(const char C) {
  return ('0' <= C && C <= '9') || ('a' <= C && C <= 'f');
}

// Prefix is null-terminated
static bool startsWith(const char *Prefix, const char *Start, const char *End) {
  const char *P = Prefix;
  for (const char *M = Start; M < End; ++M, ++P) {
    if (*P == 0)
      return true;
    if (*P != *M)
      return false;
  }
  return *P == 0;
}

static bool parsePathComponent(const char *M, const char *E,
                               const char **CompStart, const char **CompEnd) {
  size_t Len = 0;
  while (M < E && isDigit(*M)) {
    Len = Len * 10 + *M - '0';
    M += 1;
  }
  if (Len > 0 && M + Len <= E) {
    *CompStart = M;
    *CompEnd = M + Len;
    return true;
  }
  return false;
}

// Check whether M..E looks like a Rust hash
// i.e. 'h' followed by 16 hex digits.
static bool isRustHash(const char *M, const char *E) {
  if (E != M + 17 || M[0] != 'h')
    return false;
  for (size_t i = 1; i < 17; ++i) {
    if (!isHexDigit(M[i]))
      return false;
  }
  return true;
}

bool llvm::isRustLegacyMangling(const char *MangledName, size_t Length) {
  if (!startsWith("_ZN", MangledName, MangledName + Length))
    return false;

  const char *M = MangledName + 3;
  const char *E = MangledName + Length;
  const char *CompStart = nullptr;
  const char *CompEnd = nullptr;
  while (parsePathComponent(M, E, &CompStart, &CompEnd)) {
    M = CompEnd;
  }
  return CompStart && isRustHash(CompStart, CompEnd);
}

char *llvm::rustLegacyDemangle(const char *MangledName, char *Buf, size_t *N,
                               int *Status) {

  if (MangledName == nullptr || (Buf != nullptr && N == nullptr)) {
    if (Status != nullptr)
      *Status = demangle_invalid_args;
    return nullptr;
  }

  size_t Length = std::strlen(MangledName);
  if (!startsWith("_ZN", MangledName, MangledName + Length)) {
    if (Status != nullptr)
      *Status = demangle_invalid_mangled_name;
    return nullptr;
  }

  OutputBuffer Demangled;
  if (!initializeOutputBuffer(nullptr, nullptr, Demangled, 1024)) {
    if (Status != nullptr)
      *Status = demangle_memory_alloc_failure;
    return nullptr;
  }

  const char *M = MangledName + 3;
  const char *CompStart = nullptr;
  const char *CompEnd = nullptr;
  while (parsePathComponent(M, MangledName + Length, &CompStart, &CompEnd)) {

    if (CompEnd < MangledName + Length && CompEnd[0] == 'E' &&
        isRustHash(CompStart, CompEnd)) {
      break;
    }

    if (!Demangled.empty())
      Demangled << "::";

    M = CompStart;
    if (startsWith("_$", M, CompEnd))
      M += 1;

    while (M < CompEnd) {
      if (startsWith("..", M, CompEnd)) {
        Demangled << "::";
        M += 2;
        continue;
      } else if (M[0] == '$') {
        if (startsWith("$SP$", M, CompEnd)) {
          Demangled << '@';
          M += 4;
          continue;
        } else if (startsWith("$BP$", M, CompEnd)) {
          Demangled << '*';
          M += 4;
          continue;
        } else if (startsWith("$RF$", M, CompEnd)) {
          Demangled << '&';
          M += 4;
          continue;
        } else if (startsWith("$LT$", M, CompEnd)) {
          Demangled << '<';
          M += 4;
          continue;
        } else if (startsWith("$GT$", M, CompEnd)) {
          Demangled << '>';
          M += 4;
          continue;
        } else if (startsWith("$LP$", M, CompEnd)) {
          Demangled << '(';
          M += 4;
          continue;
        } else if (startsWith("$RP$", M, CompEnd)) {
          Demangled << ')';
          M += 4;
          continue;
        } else if (startsWith("$C$", M, CompEnd)) {
          Demangled << ',';
          M += 3;
          continue;
        } else if (startsWith("$u", M, CompEnd)) {
          const char *T = M + 2;
          uint32_t code = 0;
          while (T < CompEnd && isHexDigit(*T)) {
            code = code * 16 + (*T < 'a' ? *T - '0' : *T - 'a' + 0x0A);
            T += 1;
          }
          if (T < CompEnd && *T == '$') {
            Demangled << static_cast<char>(code);
            M = T + 1;
            continue;
          }
        }
      }

      Demangled << *M;
      M += 1;
    }

    M = CompEnd;
  }
  Demangled << '\0';

  char *DemangledBuf = Demangled.getBuffer();
  size_t DemangledLen = Demangled.getCurrentPosition();

  if (Buf != nullptr) {
    if (DemangledLen <= *N) {
      std::memcpy(Buf, DemangledBuf, DemangledLen);
      std::free(DemangledBuf);
      DemangledBuf = Buf;
    } else {
      std::free(Buf);
    }
  }

  if (N != nullptr)
    *N = DemangledLen;

  if (Status != nullptr)
    *Status = demangle_success;

  return DemangledBuf;
}
