## Setup

```bash
cd ~/projects/wgong
git clone git@github.com:The-Pocket/Tutorial-Codebase-Knowledge.git

conda create -n git-tutor python=3.11
conda activate git-tutor

pip install -r requirements.txt
```

### AI Studio by Google


### Cleanup

```bash
conda env remove --name agent
conda clean --all  # remove unused env space
```