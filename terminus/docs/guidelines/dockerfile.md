# Canonical Terminal-Bench Base Images

Digest-pinned references for final runtime stages. Prefer these over ad hoc images.

## Language Runtimes

| Image | Digest |
|-------|--------|
| `public.ecr.aws/docker/library/python:3.13-slim-bookworm` | `sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb` |
| `public.ecr.aws/docker/library/node:22-bookworm-slim` | `sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383` |
| `public.ecr.aws/docker/library/golang:1.24-bookworm` | `sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac` |
| `public.ecr.aws/docker/library/rust:1.85-slim` | `sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36` |
| `public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy` | `sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14` |
| `public.ecr.aws/docker/library/gcc:13-bookworm` | `sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c` |
| `public.ecr.aws/docker/library/ruby:3.3-slim-bookworm` | `sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df` |

## Build Tools & Distros

| Image | Digest |
|-------|--------|
| `public.ecr.aws/docker/library/maven:3.9.9-eclipse-temurin-21` | `sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e` |
| `public.ecr.aws/docker/library/debian:bookworm-slim` | `sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d` |
| `public.ecr.aws/docker/library/ubuntu:24.04` | `sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932` |

## Usage

```dockerfile
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb
```

Non-canonical final bases require a **brief credible justification** in the Dockerfile or README.md.

See [ci-checks.md](ci-checks.md) and [docker-environment.md](docker-environment.md).
