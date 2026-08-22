# Offline Tycho target-kernel preflight

This bundle contains no model and performs no ARC, GPU, OIA, submission, or
hidden-game work. It tests only whether the target Linux kernel can enforce the
exact Sandlock/Tycho process boundary qualified locally in R1.

From an internet-disabled target notebook, first verify the attached directory:

```bash
python verify_offline_bundle.py --bundle .
```

Then run once from a fresh writable path:

```bash
python run_target_preflight.py \
  --bundle-root . \
  --work-root /kaggle/working/oia-tycho-preflight \
  --protected-root /kaggle/input
```

Exit 0 with `target_sandlock_preflight_pass` qualifies only the target sandbox
mechanism. Exit 2 with `target_sandlock_preflight_blocked` is an acceptable and
informative result. Never substitute host Python if Sandlock is blocked.
