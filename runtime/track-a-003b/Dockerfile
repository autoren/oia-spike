FROM python@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONNOUSERSITE=1

COPY requirements-aarch64.txt /opt/oia/requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes -r /opt/oia/requirements.txt

COPY candidate_runner.py /opt/oia/candidate_runner.py
RUN chmod 0555 /opt/oia /opt/oia/candidate_runner.py \
    && chmod 0444 /opt/oia/requirements.txt

USER 65532:65532
ENTRYPOINT ["python", "-I", "/opt/oia/candidate_runner.py"]
