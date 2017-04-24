FROM ubuntu:16.04

# It is easier to install lxml for Python using apt rather than downloading 
# and building using PIP. 
RUN apt-get update \
    && apt-get install -y python python-pip python-lxml

COPY setup.py /tmp
COPY britishgas_myenergy/ /tmp/britishgas_myenergy

WORKDIR /tmp
RUN python setup.py install


VOLUME ["/tmp/myenergy"]

ENTRYPOINT ["download_myenergy"]

