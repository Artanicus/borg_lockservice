FROM python:3.11-buster AS poetry_builder
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python -


FROM poetry_builder as builder
RUN mkdir /build
WORKDIR /build
RUN apt update && apt install -y build-essential libfuse-dev libacl1-dev
COPY borg_lockservice ./borg_lockservice
COPY README.md ./README.md
COPY poetry.lock pyproject.toml ./
RUN poetry run pip wheel borgbackup
RUN poetry build -f wheel


FROM python:3.11-slim-buster
WORKDIR /srv
COPY --from=builder /build/*.whl /build/dist/*.whl ./
RUN pip install *.whl

ENTRYPOINT ["borg_lockservice"]
