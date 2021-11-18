FROM python:3.9.7-buster AS base-image

# Create a Python virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV

# Make sure we use the virtualenv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Put the latest pip and setuptools in the virtualenv
RUN pip install --upgrade --no-cache-dir pip setuptools wheel

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY . /app
WORKDIR /app

# Install package
RUN pip install --no-cache-dir .

FROM base-image AS runtime-image

# Create a non-root user
RUN useradd --create-home appuser
WORKDIR /home/appuser

# Make sure we use the virtualenv
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=base-image /opt/venv /opt/venv

# Switch to non-root user
USER appuser

# Run alertdb command
ENTRYPOINT ["sh", "-c"]
CMD alertdb --help
