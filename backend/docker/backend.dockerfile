FROM python:3.14-slim

ARG REQUIREMENTS=requirements.txt

WORKDIR /src

# Copy only dependency files first (better layer caching)
COPY ${REQUIREMENTS} /src/requirements.txt

# Install deps
RUN pip install --upgrade pip && \
    pip install -r /src/requirements.txt && \
    rm /src/requirements.txt

# Copy source
COPY ./app /src/app
COPY ./migrations /src/migrations
COPY ./scripts /src/scripts
COPY ./tests /src/tests
COPY ./alembic.ini /src/alembic.ini

# Make scripts executable
RUN chmod +x /src/scripts/start.sh

# Entry point
ENV PYTHONPATH=/src
CMD ["/bin/bash", "/src/scripts/start.sh"]
