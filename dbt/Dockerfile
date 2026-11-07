# dbt runner.
#
# Pinned to Python 3.12 because dbt does not support 3.13+ yet: several of its
# dependencies have no wheels for newer versions and fall back to building from
# source, which fails. Running it in a container keeps that constraint out of
# the way of whatever Python is installed on the host.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DBT_PROFILES_DIR=/dbt

WORKDIR /dbt

RUN pip install --no-cache-dir "dbt-postgres==1.9.0"

COPY packages.yml .
RUN dbt deps || true

COPY . .

ENTRYPOINT ["dbt"]
CMD ["build"]
