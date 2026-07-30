# Resource Caps

## Goal
Constrain the stack to a plausible edge-device budget, with the cap **actually enforced and
actually binding** — not a round number that never bites.

## Model
`gemma4:e2b` — an edge-oriented Gemma 4 variant, multimodal (vision + audio + text), Q4_K_M,
5.1B parameters, 7.2GB on disk. Set via the `MODEL_NAME` build arg in `docker/Dockerfile`.

Note: `gemma3n:e2b` was briefly baked in by an early Dockerfile default and is **not** a
viable fallback — `ollama show` lists only `completion`, no `vision`, so it cannot do frame
reasoning at all.

## Measured memory requirement (empirical, not estimated)
Measured inside the running container via cgroup v2, not guessed:

| Observation | Value |
|---|---|
| `gemma4:e2b` resident (anonymous) memory during inference | **~5.87 GB** |
| Reported by `ollama ps` | 6.7 GB |
| Idle (model unloaded) | ~0.3 GB |

At an initial **6GB** cap this ran at 98.15% of the limit with `memory.events: max = 70,358`
— i.e. the kernel was forced to reclaim tens of thousands of times (thrashing), and only
~140MB remained for the Flask backend, OpenCV and the reasoning loop that must also run in
this container. `oom_kill` was still 0, but there was no usable margin.

## Chosen caps
```
--memory=6g --memory-swap=12g --cpus=4
```

### Why 4 CPUs (measured, and more faithful)
Originally 2, on the reasoning that "more restrictive is safer to claim". That was wrong on
both counts. Measured throughput:

| CPUs | tokens/sec | ~time per observation |
|---|---|---|
| 2 | 2.11 - 2.21 | 170 - 190s |
| **4** | **4.7** | **~35 - 60s** |

~2.2x, near-linear — inference here is CPU-bound, not memory-bound. 4 cores is also *closer*
to the cited reference hardware (Raspberry Pi 4/5 are quad-core, Jetson Orin Nano is 6-core),
so this made the simulation both faster and more accurate. The Docker VM has 16 cores
available, so 4 is still a genuine constraint.

### Why 6GB, and why --memory-swap matters
An 8GB cap was attempted first, then 7GB. Both were abandoned:

- **8GB is impossible here**: the Docker Desktop VM on this machine has only **7.611 GiB**
  total, so an 8GB cap could never bind — the VM's ceiling would be the real limit and the
  stated cap would be fiction.
- **`--memory-swap` must be set above `--memory`.** Setting them equal (which is what
  `docker update --memory=7g --memory-swap=7g` does) disables swap entirely
  (`memory.swap.max = 0`). With zero swap, `llama-server` was SIGKILLed on every inference —
  39 `oom_kill` events — even though the container was nowhere near its limit at the time.
  The original container, created with `--memory=6g` and no explicit swap value, worked
  because Docker defaults swap to 2x memory. Restoring `--memory-swap=12g` (6GB RAM + 6GB
  swap) fixed it immediately.

This was a self-inflicted regression worth recording: the cap change *looked* like a pure
memory increase but silently removed the swap headroom the model depended on.

### Honest note on how tight this is
At 6GB the container runs at **~97% memory during inference** with heavy swap thrashing. It
works, but there is effectively no headroom, and it is the main reason throughput sits at
~3.3 tokens/sec. On this machine the constraint is not really a design choice — the Docker VM
is 7.6 GiB and the Windows host typically has only ~1 GiB free, so there is nowhere to grow.

### Reference hardware
7GB is framed against **8GB-class single-board edge hardware** — e.g. the Raspberry Pi 4
Model B 8GB variant (quad-core Cortex-A72 @ 1.5GHz, 8GB LPDDR4) or an 8GB Jetson Orin Nano.
Capping the container at 7GB rather than the full 8GB is *more* faithful than an 8GB cap
would be: on a real 8GB board the OS and its services consume some of that, so ~7GB is
closer to what an application actually gets.

`--cpus=2` is deliberately more restrictive than the quad-core reference boards. This is a
conservative choice, not a matched one — worth revisiting, since matching the reference
device's 4 cores would be both more faithful and measurably faster (see below).

### Superseded rationale
Earlier revisions of this file anchored on the **Jetson Nano 2GB/4GB** (quad-core Cortex-A57
@ 1.43GHz). That anchor is no longer accurate: `gemma4:e2b` empirically needs ~5.87GB, so it
cannot run on a 4GB device at all, and citing one while capping at 7GB would be misleading.
The 8GB-class framing above replaces it.

Dedicated security-camera ISPs (Ambarella CV22/CV25 — quad-core Cortex-A53 @ 1GHz plus a
2-4 TOPS NPU) were also considered and rejected as a reference: they run fixed-function CV
models on that NPU rather than general-purpose LLM inference against a CPU/RAM budget, and
vendors don't publish their RAM specs, so they aren't a fair "can it run Gemma" comparison.

## Measured throughput
All figures from Ollama's own `eval_count` / `eval_duration`, not wall-clock guesswork.

| Config | tokens/sec | anon resident |
|---|---|---|
| `gemma4:e2b`, 2 CPUs | 2.11 | 5.70 GB |
| `gemma4:e2b-it-qat`, 2 CPUs | 2.21 | 4.61 GB |
| **`gemma4:e2b-it-qat`, 4 CPUs** | **4.7** | 4.61 GB |

Two things worth recording honestly:

- **The QAT swap did not improve speed** (2.11 → 2.21 tok/s is noise). The expectation that
  relieving memory thrashing would speed things up was wrong — inference is CPU-bound here.
  The swap earned its place on memory alone: 1.09GB less resident memory, which is what
  leaves room for Flask and OpenCV to run in the same container.
- **CPU count was the real lever**: 2 → 4 cores gave ~2.2x. See the caps section above.

This is still the concrete justification for periodic sampling: at ~5 tok/s, continuous
streaming inference is not viable on this class of hardware. With inference at ~35-60s and
`SAMPLE_INTERVAL_SECONDS` at 150, the device now genuinely idles ~90-115s between samples —
which is what makes the "periodic sampling is an edge-efficiency choice" claim actually true
rather than a rationalisation of being slow.

## Reporting the cap honestly
`src/monitor/resources.py` reads the container's cgroup memory (`memory.current` /
`memory.max`) rather than `psutil.virtual_memory()`, which reports **host** memory even
inside a container (non-namespaced `/proc/meminfo`). Without this the dashboard displayed
"15.4 / 6.0 GB" — host usage against a container cap, which would have misrepresented the
project's central claim. The dashboard also labels whether the figure came from a real
container cap (`cgroup`) or an uncapped dev host (`host`).

## Build vs runtime network use (privacy proof integrity)
The Gemma model is pulled into the image **at `docker build` time** (network required), not at
container runtime. This keeps the running container's actual network requirement at zero, so
the demo's "kill the network, dashboard shows zero outbound traffic" proof is genuine rather
than staged around a container that secretly still needs connectivity.
