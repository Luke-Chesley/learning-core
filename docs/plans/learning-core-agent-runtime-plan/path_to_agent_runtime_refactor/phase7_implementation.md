# Phase 7 Implementation Note

## Goal

Finalize rollout controls, docs, and cleanup around the shared runtime.

## Implemented

### Rollout controls

Added per-operation fallback flags in `AgentEngine`:

- `LEARNING_CORE_USE_KERNEL_FOR_<OPERATION_NAME>`

Behavior:

- unset: kernel path stays enabled
- `0`, `false`, `no`, or `off`: fall back to the legacy per-skill engine path

### Documentation

Updated `README.md` to describe:

- the shared kernel
- task profiles
- response types
- workflow cards
- packs
- the internal `generate_from_source` orchestration helper
- the current extension path for adding new capabilities

## Cleanup result

- The public API remains stable.
- The engine now has one runtime entry path by default.
- Legacy preview/execute behavior is retained only as a controlled fallback for rollout safety.
