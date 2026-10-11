# What the Transformer does in GQFT

Source: [GQFT model](../../Task_2/gqft_algorithm_sharing_vivekananda/step2/models/gqft.py). This is a temporal motion encoder. It receives pooled optical-flow features, rather than RGB pixels, text, or the selected image query.

## Signal flow

| Stage | Code-derived operation | Default shape / configuration |
| --- | --- | --- |
| Flow input | Normalized du/dv, confidence and validity; coordinate channels added inside CNN | `[B,T,4,H,W]` → six CNN channels |
| CNN and pooling | Four strided convolution blocks; mean/max or learned attention/max pooling; linear projection | One 256-D token per flow step |
| Temporal position | Add a learned time embedding to each token | `[B,T,256]`, maximum 64 steps by default |
| Causal Transformer | Four pre-norm encoder layers; eight attention heads; 1024-wide GELU feed-forward block; dropout 0.1; final LayerNorm | Motion states `[B,T,256]` |
| Displacement head | MLP 256→256→3, tanh and per-axis step scale; invalid steps zeroed | Δxyz `[B,T,3]`; default coordinate bound ±0.12 m |
| Accumulation | Cumulative sum with initial zero position | Camera displacement `[B,T+1,3]` |
| Optional yaw head | Separate MLP 256→128→1, tanh scale; cumulative sum | Default Δyaw bound ±0.15 rad; enabled by checkpoint configuration |
| Projection / validity | Query-ground anchor and camera model produce a pixel path; another branch combines motion states with query features for learned validity | `[B,Q,T+1,2]` pixel trajectory |

`B` = batch size, `T` = flow-step history, `Q` = number of selected image queries. These are configured defaults; checkpoint configuration is authoritative.

## Why use temporal attention?

A pooled CNN token summarizes spatial motion evidence from one flow field. The Transformer compares that token with valid earlier tokens to form a history-aware motion state. Multiple heads learn different feature comparisons; learned time embeddings supply sequence-position information.

For step `t`, the causal mask blocks attention to steps after `t`; the key-padding mask excludes invalid history steps. This prevents future-input access in the forward pass. It does not itself prove real-time latency, future-path forecasting, or correct camera motion.

One encoder layer applies `LayerNorm → masked self-attention → residual addition`, then `LayerNorm → feed-forward network → residual addition`. Four such layers are followed by a final LayerNorm. The Transformer returns features; the later MLP predicts displacement.

Spatial attention and temporal attention are different operations. The optional CNN attention chooses image regions before pooling. Transformer self-attention compares time-step tokens after pooling.

## Important architecture correction

The selected pixel query does **not** enter this temporal Transformer or condition the predicted 3-D camera displacement. It affects the downstream ground projection and learned validity branch. The optional predicted yaw is an auxiliary output; the shown `project_displacements_torch` call consumes displacement, query and camera, without the predicted yaw. Episode-level yaw use belongs to separate tools.

The earlier general pipeline diagram's “temporal context + query” label was corrected to temporal motion context and learned time embeddings.

## Slide caption

> The causal Transformer combines pooled optical-flow tokens over time, using learned time embeddings and masked self-attention; its motion states feed displacement and optional yaw prediction heads.

## Independent SVGs

- [Complete GQFT pipeline](diagrams/gqft_pipeline_detailed.svg)
- [Transformer detail and causal mask](diagrams/gqft_transformer_detail.svg)

Both contain editable SVG text and shapes. Generation source: [build_gqft_svg.py](tools/build_gqft_svg.py). Query/projection and optional yaw branches are kept separate. Auxiliary uncertainty and learned-validity heads are omitted from the main diagram for readability.
