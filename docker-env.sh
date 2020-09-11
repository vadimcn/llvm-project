LLVM_PROJECT_DIR=$(realpath $(dirname $BASH_SOURCE))
BUILD_DIR=${BUILD_DIR:-${LLVM_PROJECT_DIR}/build}
BUILD_TOOLS=${BUILD_TOOLS:-${LLVM_PROJECT_DIR}/../build-tools/linux}

docker run -it --privileged \
    -v ${LLVM_PROJECT_DIR}:/workspace/source:ro \
    -v ${BUILD_DIR}:/workspace/build:rw \
    -v ${BUILD_TOOLS}:/workspace/build-tools:ro \
    -e BUILD_SOURCESDIRECTORY=/workspace/source \
    -e AGENT_BUILDDIRECTORY=/workspace/build \
    -e CMAKE_BUILD_TYPE=RelWithDebInfo \
    -e SCCACHE_DIR=/workspace/build/.sccache \
    -e SCCACHE_IDLE_TIMEOUT=60 \
    -w /workspace/build \
    -u 1000:1000 \
    -v /etc/passwd:/etc/passwd \
    "$@" \
    vadimcn/linux-builder:latest \
    bash -c 'export PATH=/workspace/build-tools/bin:$PATH; bash'
