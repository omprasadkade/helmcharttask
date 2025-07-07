from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify, g
import boto3
import os
import time
import psutil
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

# ----- Prometheus Metrics -----
REQUEST_COUNT = Counter(
    'flask_request_count', 'Total Flask HTTP Requests',
    ['method', 'endpoint', 'http_status']
)
REQUEST_LATENCY = Histogram(
    'flask_request_latency_seconds', 'Latency of HTTP requests in seconds',
    ['endpoint']
)
CPU_USAGE = Gauge('flask_cpu_usage_percent', 'CPU usage percent')
MEMORY_USAGE = Gauge('flask_memory_usage_bytes', 'Memory usage in bytes')

# ----- AWS S3 Setup -----
session = boto3.Session()
s3_client = session.client('s3')


# ----- Metrics Middleware -----
@app.before_request
def before_request():
    g.start_time = time.time()
    process = psutil.Process(os.getpid())
    MEMORY_USAGE.set(process.memory_info().rss)
    CPU_USAGE.set(process.cpu_percent(interval=0.1))  # accurate reading


@app.after_request
def after_request(response):
    try:
        latency = time.time() - g.start_time
        REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.path).observe(latency)
    except Exception as e:
        print(f"Error updating Prometheus metrics: {e}")
    return response


@app.route("/metrics")
def metrics():
    try:
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
    except Exception as e:
        return jsonify({"error": f"Failed to generate metrics: {str(e)}"}), 500

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# -------------------- S3 Routes --------------------

@app.route('/')
def index():
    buckets = s3_client.list_buckets().get('Buckets', [])
    return render_template('index.html', buckets=buckets)

@app.route('/bucket/<bucket_name>')
def list_files(bucket_name):
    objects = s3_client.list_objects_v2(Bucket=bucket_name).get('Contents', [])
    return render_template('bucket.html', bucket_name=bucket_name, objects=objects)

@app.route('/create_bucket', methods=['POST'])
def create_bucket():
    bucket_name = request.form['bucket_name']
    try:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': boto3.session.Session().region_name}
        )
        flash('Bucket created successfully!', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('index'))

@app.route('/delete_bucket/<bucket_name>', methods=['POST'])
def delete_bucket(bucket_name):
    try:
        objects = s3_client.list_objects_v2(Bucket=bucket_name).get('Contents', [])
        if objects:
            for obj in objects:
                s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])

        versions = s3_client.list_object_versions(Bucket=bucket_name).get('Versions', [])
        delete_markers = s3_client.list_object_versions(Bucket=bucket_name).get('DeleteMarkers', [])

        for version in versions:
            s3_client.delete_object(Bucket=bucket_name, Key=version['Key'], VersionId=version['VersionId'])

        for marker in delete_markers:
            s3_client.delete_object(Bucket=bucket_name, Key=marker['Key'], VersionId=marker['VersionId'])

        s3_client.delete_bucket(Bucket=bucket_name)
        flash('Bucket deleted successfully!', 'success')
    except Exception as e:
        flash(str(e), 'danger')

    return redirect(url_for('index'))

@app.route('/upload_file/<bucket_name>', methods=['POST'])
def upload_file(bucket_name):
    file = request.files['file']
    if file:
        s3_client.upload_fileobj(file, bucket_name, file.filename)
        flash('File uploaded successfully!', 'success')
    return redirect(url_for('list_files', bucket_name=bucket_name))

@app.route('/delete_file/<bucket_name>/<file_key>')
def delete_file(bucket_name, file_key):
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=file_key)
        flash('File deleted successfully!', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('list_files', bucket_name=bucket_name))

@app.route('/delete_folder/<bucket_name>/<folder_name>', methods=['POST'])
def delete_folder(bucket_name, folder_name):
    try:
        if not folder_name.endswith('/'):
            folder_name += '/'

        objects = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=folder_name).get('Contents', [])
        if objects:
            for obj in objects:
                s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])

        versions = s3_client.list_object_versions(Bucket=bucket_name, Prefix=folder_name).get('Versions', [])
        delete_markers = s3_client.list_object_versions(Bucket=bucket_name, Prefix=folder_name).get('DeleteMarkers', [])

        for version in versions:
            s3_client.delete_object(Bucket=bucket_name, Key=version['Key'], VersionId=version['VersionId'])

        for marker in delete_markers:
            s3_client.delete_object(Bucket=bucket_name, Key=marker['Key'], VersionId=marker['VersionId'])

        flash(f'Folder "{folder_name}" deleted successfully!', 'success')

    except Exception as e:
        flash(str(e), 'danger')

    return redirect(url_for('list_files', bucket_name=bucket_name))

@app.route('/move_file/<bucket_name>', methods=['POST'])
def move_file(bucket_name):
    destination_bucket = request.form.get('destination_bucket')
    file_key = request.form.get('file_key')
    destination_key = request.form.get('destination_key', file_key)
    if not all([destination_bucket, file_key]):
        flash('Missing parameters. Please provide destination bucket and file name.', 'danger')
        return redirect(url_for('list_files', bucket_name=bucket_name))
    try:
        s3_client.copy_object(
            Bucket=destination_bucket,
            CopySource={'Bucket': bucket_name, 'Key': file_key},
            Key=destination_key
        )
        s3_client.delete_object(Bucket=bucket_name, Key=file_key)
        flash('File moved successfully!', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('list_files', bucket_name=bucket_name))

@app.route('/copy_file/<bucket_name>', methods=['POST'])
def copy_file(bucket_name):
    destination_bucket = request.form.get('destination_bucket')
    file_key = request.form.get('file_key')
    destination_key = request.form.get('destination_key', file_key)
    if not all([destination_bucket, file_key]):
        flash('Missing parameters. Please provide destination bucket and file name.', 'danger')
        return redirect(url_for('list_files', bucket_name=bucket_name))
    try:
        s3_client.copy_object(
            Bucket=destination_bucket,
            CopySource={'Bucket': bucket_name, 'Key': file_key},
            Key=destination_key
        )
        flash(f'File copied successfully to {destination_bucket}!', 'success')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('list_files', bucket_name=bucket_name))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
