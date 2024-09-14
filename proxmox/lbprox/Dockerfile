FROM alpine:latest

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN apk update && \
    apk add --no-cache \
        python3 \ 
        sudo \
	docker-cli docker-cli-compose \
        su-exec \
	vim \
        curl \
        bash-completion && \
    # Install virtualenv
    python3 -m venv ./venv && \
    source ./venv/bin/activate && \
    python3 -m ensurepip && \
    pip3 install --no-cache --upgrade pip setuptools && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy and install the rest of the files
COPY . .

# Run setup.py
RUN source ./venv/bin/activate && \
    python3 setup.py install

ENV VIRTUAL_ENV=/app/venv
ENV PATH=/app/venv/bin:$PATH

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# CMD ["lbprox"]
