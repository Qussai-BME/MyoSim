FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MUJOCO_GL=egl

WORKDIR /opt/myosim

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libegl1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 myosim \
    && mkdir -p /opt/myosim/artifacts \
    && chown -R myosim:myosim /opt/myosim

COPY pyproject.toml README.md LICENSE THIRD_PARTY_NOTICES.md ./
COPY src ./src
COPY assets ./assets
COPY configs ./configs
COPY examples ./examples

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir '.[pybullet]'

USER myosim

HEALTHCHECK --interval=30s --timeout=20s --start-period=20s --retries=3 \
    CMD myosim doctor --strict || exit 1

ENTRYPOINT ["myosim"]
CMD ["doctor", "--strict"]
