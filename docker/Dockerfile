FROM hysds/container-aria-jpl_ariamh:python3

LABEL description="PGE container for geocoded coherence and amplitude"

# create work directory
RUN set -ex \
 && mkdir -p /data/work \
 && chmod -R 755 /data \
 && chown -R ops:ops /data

USER ops

# copy code ensure proper permissions, and move dependencies to final locations
COPY . /home/ops/verdi/ops/slcp2cor
RUN set -ex \
 && sudo chown -R ops:ops /home/ops/verdi/ops/slcp2cor \
 && cd /home/ops/verdi/ops/slcp2cor/src \
 && ./compile.sh

# set entrypoint
WORKDIR /home/ops
CMD ["/bin/bash", "--login"]
