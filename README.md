<<<<<<< HEAD
# helmcharttask
=======
## prometheus Assignment


Prometheus Assignment Export the metrics (like request per second, memory usage, cpu usage etc) in the existing mini project given to Interns

Install Prometheus and Grafana using Docker (with docker-compose)

Configure prometheus (scrape configs) such way that it can scrape the metrics from default metric path of the application job

Validate the entire configuration to check if the data is coming or not in Prometheus UI

Create the Dashboards in Grafana on top of the metrics exported by adding the 
Prometheus as a Datasource.



##  Project Structure

```
prometheus_assignment/
├── app.py
├── docker-compose.yml
├── Dockerfile
├── prometheus.yml
├── requirements.txt
└── templates/
    └── index.html
    └── bucket.html
```








## snapshots of Assignment



## Flaskapp_output

![image](https://github.com/user-attachments/assets/8fce5c37-f918-4cbc-9a10-1482bb16e45c)

## Flask_targets

![Flask_targets](https://github.com/user-attachments/assets/b6b1438d-23a4-454d-b692-f5bdf689b58a)

## Cpu_usage

![Cpu_usage](https://github.com/user-attachments/assets/064271d1-414d-4dc3-9f01-6b0f1673335f)

## Memory_usage

![Memory_usage](https://github.com/user-attachments/assets/79b8814f-efea-4106-9299-a708f6f45e57)

## Latency

![Latency](https://github.com/user-attachments/assets/6f254d3f-dced-4e87-8397-5ecf8b643088)


>>>>>>> 6022239 (Initial commit: Dockerized Flask app with Helm charts and Kubernetes deployment)
