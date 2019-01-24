LLVM_PROJECT_DIR=$(realpath $(dirname $BASH_SOURCE))
BUILD_DIR=${BUILD_DIR:-${LLVM_PROJECT_DIR}/build}

docker run -it --privileged \
    -v ${LLVM_PROJECT_DIR}:/workspace/source:ro \
    -v ${BUILD_DIR}:/workspace/build:rw \
    -e BUILD_SOURCESDIRECTORY=/workspace/source \
    -e AGENT_BUILDDIRECTORY=/workspace/build \
    -e CMAKE_BUILD_TYPE=RelWithDebInfo \
    -w /workspace/build \
    -u 1000:1000 \
    -v /etc/passwd:/etc/passwd \
    "$@" \
    vadimcn/linux-builder:latest
