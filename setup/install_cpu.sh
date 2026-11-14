#!/bin/bash
# Install CPU-only PyTorch and ExecuTorch on the Raspberry Pi 5 (no NVIDIA/CUDA packages).
set -x
. ~/selfcheck-env/bin/activate
pip list --format=freeze 2>/dev/null | grep -iE "^(nvidia|cuda|triton)" | cut -d= -f1 | xargs -r pip uninstall -y
pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
pip install executorch==1.6.0 huggingface_hub
python -c "from executorch.extension.llm.custom_ops import custom_ops; from executorch.kernels import quantized; from executorch.extension.llm.runner import TextLLMRunner, GenerationConfig; import torch; print('IMPORT_OK torch', torch.__version__)"
echo INSTALL_EXIT $?
pip list --format=freeze 2>/dev/null | grep -icE "^(nvidia|cuda)" | sed 's/^/CUDA_PACKAGES_LEFT /'
