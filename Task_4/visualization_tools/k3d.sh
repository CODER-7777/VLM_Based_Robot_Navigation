#!/usr/bin/env bash
# Run a script in the kitchen3d env with every cache on /data (/home is full).
export PYTHONNOUSERSITE=1 HF_HOME=/data/robotics/toshith/k3d_cache/hf TORCH_HOME=/data/robotics/toshith/k3d_cache/torch \
  XDG_CACHE_HOME=/data/robotics/toshith/k3d_cache/xdg U2NET_HOME=/data/robotics/toshith/k3d_cache/u2net \
  CUDA_HOME=/data/robotics/toshith/envs/kitchen3d CC=/usr/bin/gcc-9 CXX=/usr/bin/g++-9 \
  ATTN_BACKEND=xformers SPCONV_ALGO=native CUDA_VISIBLE_DEVICES=${GPU:-2}
exec /data/robotics/toshith/envs/kitchen3d/bin/python "$@"
