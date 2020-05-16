#This is variant of Dockerfile started from official kapacitor. Considered as default
#
#This is working approach
#
#The minus of this approach is that you install default debian-stretch version. It is 3.5.
#Also you need do more python env configuration manualy. Like symlink python-python3.
#
#The plus is that you maintain only one Dockerfile

#FROM kapacitor:latest
ARG KAPACITOR_TAG
FROM kapacitor:$KAPACITOR_TAG

RUN apt-get update && apt-get install -y --no-install-recommends \
		python3 \
		python3-pip \
		bzip2 \
		file \
		xz-utils \
		build-essential \
		python3-dev \
		gfortran \
		libatlas-base-dev \
		libopenblas-dev \
		liblapack-dev \
		python3-scipy \
		python3-numpy \
		cython3 \
	&& rm -rf /var/lib/apt/lists/*

# make some useful symlinks that are expected to exist
RUN cd /usr/local/bin \
	&& ln -sf /usr/bin/pydoc3 pydoc \
	&& ln -sf /usr/bin/python3 python \
	&& ln -sf /usr/bin/python3-config python-config

RUN pip3 install --no-cache-dir setuptools

# install kapacitor udf python agent package
COPY tmp/kapacitor /tmp/kapacitor
WORKDIR /tmp/kapacitor/udf/agent/py
RUN python3 setup.py install && python3 setup.py clean

# install dependencies for UDFs
COPY UDFs/requirements.txt /tmp/kapacitor/requirements.txt
WORKDIR /tmp/kapacitor
RUN pip3 install --extra-index-url=https://www.piwheels.org/simple --no-cache-dir -r requirements.txt

WORKDIR /var/lib/kapacitor
