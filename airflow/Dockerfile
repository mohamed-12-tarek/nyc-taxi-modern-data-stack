
FROM apache/airflow:3.3.2-python3.11

RUN pip install --no-cache-dir uv

COPY requirements-venv.txt /tmp/requirements-venv.txt

RUN uv venv /home/airflow/venv --python /usr/local/bin/python \
 && uv pip install --python /home/airflow/venv/bin/python --no-cache -r /tmp/requirements-venv.txt
