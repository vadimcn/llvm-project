//===-- RustLanguageRuntime.h -----------------------------------*- C++ -*-===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//

#ifndef liblldb_RustLanguageRuntime_h_
#define liblldb_RustLanguageRuntime_h_

// C Includes
// C++ Includes
#include <vector>
// Other libraries and framework includes
// Project includes
#include "lldb/Core/PluginInterface.h"
#include "lldb/Target/LanguageRuntime.h"
#include "lldb/lldb-private.h"

namespace lldb_private {

class RustLanguageRuntime : public LanguageRuntime {
public:
  static void Initialize();

  static void Terminate();

  static lldb_private::LanguageRuntime *
  CreateInstance(Process *process, lldb::LanguageType language);

  static lldb_private::ConstString GetPluginNameStatic();

  lldb_private::ConstString GetPluginName() override;

  uint32_t GetPluginVersion() override;

  lldb::LanguageType GetLanguageType() const override {
    return lldb::eLanguageTypeRust;
  }

  bool GetObjectDescription(Stream &str, ValueObject &object) override {
    return false;
  }

  bool GetObjectDescription(Stream &str, Value &value,
                            ExecutionContextScope *exe_scope) override {
    return false;
  }

  lldb::BreakpointResolverSP CreateExceptionResolver(Breakpoint *bkpt,
                                                     bool catch_bp,
                                                     bool throw_bp) override {
    return nullptr;
  }

  lldb::ThreadPlanSP GetStepThroughTrampolinePlan(Thread &thread,
                                                  bool stop_others) override {
    return {};
  }

  TypeAndOrName FixUpDynamicType(const TypeAndOrName &type_and_or_name,
                                 ValueObject &static_value) override;

  bool CouldHaveDynamicValue(ValueObject &in_value) override;

  bool GetDynamicTypeAndAddress(ValueObject &in_value,
                                lldb::DynamicValueType use_dynamic,
                                TypeAndOrName &class_type_or_name,
                                Address &address,
                                Value::ValueType &value_type) override;

protected:
  RustLanguageRuntime(Process *process);

private:
  DISALLOW_COPY_AND_ASSIGN(RustLanguageRuntime);
};

} // namespace lldb_private

#endif // liblldb_RustLanguageRuntime_h_
