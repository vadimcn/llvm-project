//===------------------ RustDemangleTest.cpp ------------------------------===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//

#include "llvm/Demangle/Demangle.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

#include <cstdlib>

TEST(RustDemangle, Success) {
  char *Demangled = llvm::rustDemangle("_RNvC1a4main");
  EXPECT_STREQ(Demangled, "a::main");
  std::free(Demangled);
}

TEST(RustDemangle, Invalid) {
  char *Demangled = nullptr;

  // Invalid prefix.
  Demangled = llvm::rustDemangle("_ABCDEF");
  EXPECT_EQ(Demangled, nullptr);

  // Correct prefix but still invalid.
  Demangled = llvm::rustDemangle("_RRR");
  EXPECT_EQ(Demangled, nullptr);
}

TEST(RustDemangle, Legacy) {

  auto check = [](const char *Mangled, const char *Expected) {
    char *Demangled = llvm::rustLegacyDemangle(Mangled);
    EXPECT_STREQ(Demangled, Expected) << "Mangled: " << Mangled;
    std::free(Demangled);
  };

  // clang-format off
  check("_ZN4testE", "test");
  check("_ZN4test1a2bcE", "test::a::bc");
  // demangle_dollars
  check("_ZN4$RP$E", ")");
  check("_ZN8$RF$testE", "&test");
  check("_ZN8$BP$test4foobE", "*test::foob");
  check("_ZN9$u20$test4foobE", " test::foob");
  check("_ZN35Bar$LT$$u5b$u32$u3b$$u20$4$u5d$$GT$E", "Bar<[u32; 4]>");
  check("_ZN13test$u20$test4foobE", "test test::foob");
  check("_ZN12test$BP$test4foobE", "test*test::foob");
  // demangle_osx
  check("__ZN5alloc9allocator6Layout9for_value17h02a996811f781011E",
        "alloc::allocator::Layout::for_value");
  check("__ZN38_$LT$core..option..Option$LT$T$GT$$GT$6unwrap18_MSG_FILE_LINE_COL17haf7cb8d5824ee659E",
        "<core::option::Option<T>>::unwrap::_MSG_FILE_LINE_COL");
  check("__ZN4core5slice89_$LT$impl$u20$core..iter..traits..IntoIterator$u20$for$u20$$RF$$u27$a$u20$$u5b$T$u5d$$GT$9into_iter17h450e234d27262170E",
        "core::slice::<impl core::iter::traits::IntoIterator for &'a [T]>::into_iter");
  // demangle_windows
  check("ZN4testE", "test");
  check("ZN13test$u20$test4foobE", "test test::foob");
  check("ZN12test$RF$test4foobE", "test&test::foob");
  // demangle_elements_beginning_with_underscore
  check("_ZN13_$LT$test$GT$E", "<test>");
  check("_ZN28_$u7b$$u7b$closure$u7d$$u7d$E", "{{closure}}");
  check("_ZN15__STATIC_FMTSTRE", "__STATIC_FMTSTR");
  // demangle_trait_impls
  check(
      "_ZN71_$LT$Test$u20$$u2b$$u20$$u27$static$u20$as$u20$foo..Bar$LT$Test$GT$$GT$3barE",
      "<Test + 'static as foo::Bar<Test>>::bar");
  // demangle_without_hash_edgecases
  // One element, no hash.
  check("_ZN3fooE", "foo");
  // Two elements, no hash.
  check("_ZN3foo3barE", "foo::bar");
  // Longer-than-normal hash.
  check("_ZN3foo20h05af221e174051e9abcE", "foo::h05af221e174051e9abc");
  // Shorter-than-normal hash.
  check("_ZN3foo5h05afE", "foo::h05af");
  // Valid hash, but not at the end.
  check("_ZN17h05af221e174051e93fooE", "h05af221e174051e9::foo");
  // Not a valid hash, missing the 'h'.
  check("_ZN3foo16ffaf221e174051e9E", "foo::ffaf221e174051e9");
  // Not a valid hash, has a non-hex-digit.
  check("_ZN3foo17hg5af221e174051e9E", "foo::hg5af221e174051e9");
  // handle_assoc_types
  check("_ZN151_$LT$alloc..boxed..Box$LT$alloc..boxed..FnBox$LT$A$C$$u20$Output$u3d$R$GT$$u20$$u2b$$u20$$u27$a$GT$$u20$as$u20$core..ops..function..FnOnce$LT$A$GT$$GT$9call_once17h69e8f44b3723e1caE",
        "<alloc::boxed::Box<alloc::boxed::FnBox<A, Output=R> + 'a> as core::ops::function::FnOnce<A>>::call_once");
  // handle_bang
  check("_ZN88_$LT$core..result..Result$LT$$u21$$C$$u20$E$GT$$u20$as$u20$std..process..Termination$GT$6report17hfc41d0da4a40b3e8E",
        "<core::result::Result<!, E> as std::process::Termination>::report");
  // demangle_issue_60925
  check("_ZN11issue_609253foo37Foo$LT$issue_60925..llv$u6d$..Foo$GT$3foo17h059a991a004536adE",
        "issue_60925::foo::Foo<issue_60925::llvm::Foo>::foo");
  // clang-format on

  auto demangle = [](const char *Mangled) {
    char *Demangled = llvm::rustLegacyDemangle(Mangled);
    std::free(Demangled);
  };

  // dont_panic
  demangle("_ZN2222222222222222222222EE");
  demangle("_ZN5*70527e27.ll34csaғE");
  demangle("_ZN5*70527a54.ll34_$b.1E");
  demangle("\
             _ZN5~saäb4e\n\
             2734cOsbE\n\
             5usage20h)3\0\0\0\0\0\0\07e2734cOsbE\
             ");
}
