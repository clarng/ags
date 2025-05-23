<!-- curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin/:$PATH"
uv venv .venv --python 3.11 && source .venv/bin/activate
export PATH="$HOME/.local/bin/:$PATH"
uv pip install --upgrade pip
uv pip install vllm==0.7.2
uv pip install setuptools && uv pip install flash-attn --no-build-isolation -->

<!-- git clone https://github.com/huggingface/open-r1.git
cd open-r1
GIT_LFS_SKIP_SMUDGE=1 uv pip install -e ".[dev]"

## MANUAL STEPS
huggingface-cli login
wandb login -->
