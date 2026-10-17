> Historical note. For current commands and decisions, start at [Task 3](../../README.md).

# Problem Fixability Table

Updated: 2026-09-25. You tell the problem, I record whether it's fixable and how.

| # | Problem | Fixable? | How to fix | Alone enough to solve jitter? |
|---|---|---|---|---|
| 1 | Policy weights — wrong checkpoint loaded? | ❌ Not a problem | Verified correct (30,175 replays match, max diff 2.29e-5) | N/A — already confirmed correct |
| 2 | Calf target limit mismatch (79.5° difference) | ✅ Yes | Use real hardware limit (-0.88776 rad) in the training environment, then fine-tune from 90k | No — audit tested with corrected limits and stairs still failed |
| 3 | Contact stiffness / time constant (`solref=0.002` clamped to 10 ms at $dt=5\text{ ms}$) | ✅ Yes | Lower physics timestep ($dt \le 1\text{ ms}$ / 1000 Hz) to allow true 2 ms stiff contact, or explicitly tune contact solver/stiffness domain randomization | No — contact dynamics affect landing impact/stair edge grip, but target oscillation also occurs in air/free motion |
