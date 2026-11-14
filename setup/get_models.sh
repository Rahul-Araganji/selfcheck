#!/bin/bash
# Download the ExecuTorch model files (run once, while online).
. ~/selfcheck-env/bin/activate
cd ~/selfcheck
hf download software-mansion/Llama-3.2-ExecuTorch 1b/xnnpack/llama_3_2_1b_xnnpack_spinquant.pte tokenizer.json tokenizer_config.json --local-dir models/llama
echo LLAMA_EXIT $?
hf download software-mansion/Qwen3-ExecuTorch 0_6b/xnnpack/qwen_3_0_6b_xnnpack_8da4w.pte tokenizer.json tokenizer_config.json --local-dir models/qwen
echo QWEN_EXIT $?
find models -type f -name "*.pte" -o -type f -name "tokenizer*" | xargs ls -la
echo MODELS_DONE
