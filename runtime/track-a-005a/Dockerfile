FROM oia-track-a-003b-runtime:preoutcome

USER root

COPY requirements-aarch64.txt /opt/oia/requirements-track-a-005a.txt
COPY candidate_runner.py /opt/oia/candidate_runner.py
RUN chmod 0555 /opt/oia /opt/oia/candidate_runner.py \
    && chmod 0444 /opt/oia/requirements-track-a-005a.txt

USER 65532:65532
ENTRYPOINT ["python", "-I", "/opt/oia/candidate_runner.py"]
