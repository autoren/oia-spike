FROM oia-track-a-005a-runtime:preexecution

USER root

COPY candidate_runner.py /opt/oia/candidate_runner_005b.py
RUN chmod 0555 /opt/oia/candidate_runner_005b.py

USER 65532:65532
ENTRYPOINT ["python", "-I", "/opt/oia/candidate_runner_005b.py"]
