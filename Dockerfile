FROM ubuntu:20.04

# Install necessary packages and ensure python means python3
RUN apt-get update && \
	    DEBIAN_FRONTEND=noninteractive apt-get remove -y python && \
	    apt-get install -y --no-install-recommends \
	    git \
	    build-essential \
	    libcurl4-openssl-dev \
	    libssl-dev \
	    python3 \
	    python3-dev \
	    python3-pip \
	    python3-venv \
	    python3-wheel && \
	    echo "alias python='python3'" >> /root/.bash_aliases && \
	    echo "alias pip='pip3'" >> /root/.bash_aliases && \
	    cd /usr/local/bin && ln -s /usr/bin/python3 python && \
	    cd /usr/local/bin && ln -s /usr/bin/pip3 pip

# Make bash the default shell
RUN mv /bin/sh /bin/sh.old && cp /bin/bash /bin/sh

# Clone the dataset repo
RUN git clone https://github.com/alan-turing-institute/TCPD

# Change working dir
WORKDIR TCPD

# Create virtualenv
RUN make venv

# Build the dataset when container is run.
CMD ["make", "export"]
