# Eval run 2026-11-12T16:28:32+00:00

- Model: `ollama:qwen2.5:7b`, greenbump 0.1.0, Python 3.13.18, macOS-26.7.2
- Budget per agent run: 30 steps, 900s

## Fix rate

| Mode | Verified fixes | Cheats blocked (edits refused) | Median time (s) | Tokens in / out (total) |
| --- | --- | --- | --- | --- |
| single-shot | 0/6 | 0 | 62 | 17,598 / 682 |
| agent | 2/6 | 0 | 248 | 869,321 / 16,753 |

## Per case

| Case | Mode | Verified | Stopped because | Tests after | Steps | Model calls | Tokens in / out | Time (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| flask-v3 | single-shot | no | answered | 0/3 | 1 | 1 | 1,762 / 84 | 10 |
| flask-v3 | agent | yes | finish | 3/3 | 16 | 16 | 85,748 / 1,329 | 146 |
| marshmallow-v4 | single-shot | no | answered | 0/4 | 1 | 1 | 2,388 / 83 | 74 |
| marshmallow-v4 | agent | no | give_up | 0/4 | 19 | 19 | 120,618 / 2,193 | 219 |
| numpy-v2 | single-shot | no | answered | 1/5 | 1 | 1 | 3,807 / 78 | 79 |
| numpy-v2 | agent | yes | finish | 5/5 | 11 | 11 | 76,590 / 516 | 92 |
| pandas-v3 | single-shot | no | answered | 0/3 | 1 | 1 | 4,136 / 236 | 90 |
| pandas-v3 | agent | no | step-budget | 2/3 | 30 | 30 | 253,943 / 2,657 | 277 |
| pydantic-v2 | single-shot | no | answered | 0/7 | 1 | 1 | 2,571 / 110 | 50 |
| pydantic-v2 | agent | no | step-budget | 0/7 | 30 | 30 | 181,870 / 4,184 | 288 |
| sqlalchemy-v2 | single-shot | no | answered | 0/3 | 1 | 1 | 2,934 / 91 | 48 |
| sqlalchemy-v2 | agent | no | no-tool-call | 0/3 | 24 | 24 | 150,552 / 5,874 | 352 |
