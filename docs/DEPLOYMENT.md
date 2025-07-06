# 🚀 Deployment Guide

## Production Deployment

### Prerequisites

- Python 3.8+
- Azure OpenAI account and API key
- Server with at least 1GB RAM and 1 CPU core

### Environment Setup

1. **Create environment file:**
```bash
cp azure.env.example azure.env
```

2. **Configure Azure OpenAI:**
```bash
# azure.env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_COMPLETIONS_MODEL=gpt-4
```

3. **Set PII protection:**
```bash
export PII_PROTECTION_ENABLED=true
export PII_PROXY_DEBUG=false
export PII_SESSION_TIMEOUT_MINUTES=60
```

### Production Server

#### Using Uvicorn

```bash
# Production server
uvicorn llm_pii_proxy.main:create_app --factory \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --access-log \
  --log-level info
```

#### Using Gunicorn

```bash
# Install gunicorn
pip install gunicorn uvloop

# Run with gunicorn
gunicorn llm_pii_proxy.main:create_app \
  --factory \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

### Docker Deployment

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements_llm_proxy.txt .
RUN pip install --no-cache-dir -r requirements_llm_proxy.txt

# Copy application
COPY llm_pii_proxy/ llm_pii_proxy/
COPY pii_redaction.py .
COPY azure.env.example .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start server
CMD ["uvicorn", "llm_pii_proxy.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose

```yaml
version: '3.8'

services:
  llm-pii-proxy:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PII_PROTECTION_ENABLED=true
      - PII_PROXY_DEBUG=false
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_COMPLETIONS_MODEL=gpt-4
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes Deployment

#### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: llm-pii-proxy-config
data:
  PII_PROTECTION_ENABLED: "true"
  PII_PROXY_DEBUG: "false"
  PII_SESSION_TIMEOUT_MINUTES: "60"
  AZURE_COMPLETIONS_MODEL: "gpt-4"
```

#### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: llm-pii-proxy-secrets
type: Opaque
stringData:
  AZURE_OPENAI_ENDPOINT: "https://your-resource.openai.azure.com/"
  AZURE_OPENAI_API_KEY: "your-api-key-here"
```

#### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-pii-proxy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: llm-pii-proxy
  template:
    metadata:
      labels:
        app: llm-pii-proxy
    spec:
      containers:
      - name: llm-pii-proxy
        image: llm-pii-proxy:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: llm-pii-proxy-config
        - secretRef:
            name: llm-pii-proxy-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

#### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: llm-pii-proxy-service
spec:
  selector:
    app: llm-pii-proxy
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

#### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: llm-pii-proxy-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: llm-proxy.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: llm-pii-proxy-service
            port:
              number: 80
```

## Load Balancing

### Nginx Configuration

```nginx
upstream llm_pii_proxy {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name llm-proxy.yourdomain.com;

    location / {
        proxy_pass http://llm_pii_proxy;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Streaming support
        proxy_buffering off;
        proxy_cache off;
        
        # Timeouts
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

## Monitoring & Logging

### Log Configuration

```python
# logging.conf
[loggers]
keys=root,llm_pii_proxy

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=INFO
handlers=consoleHandler

[logger_llm_pii_proxy]
level=INFO
handlers=consoleHandler,fileHandler
qualname=llm_pii_proxy
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=simpleFormatter
args=('/var/log/llm_pii_proxy.log',)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Prometheus Metrics

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter('llm_proxy_requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('llm_proxy_request_duration_seconds', 'Request duration')
pii_detections = Counter('llm_proxy_pii_detections_total', 'PII detections', ['pii_type'])
active_sessions = Gauge('llm_proxy_active_sessions', 'Active PII sessions')
```

## Security Considerations

### Network Security

- Use HTTPS in production
- Implement rate limiting
- Configure firewall rules
- Use VPN for internal access

### API Security

- Rotate API keys regularly
- Implement request signing
- Use strong authentication
- Monitor for suspicious activity

### PII Security

- Enable PII protection in production
- Regular audit of PII patterns
- Monitor PII detection accuracy
- Secure log storage

## Performance Tuning

### Server Optimization

```bash
# Increase file descriptor limits
ulimit -n 65536

# Optimize TCP settings
echo 'net.core.somaxconn = 65536' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_max_syn_backlog = 65536' >> /etc/sysctl.conf
```

### Application Tuning

```python
# Uvicorn optimization
uvicorn llm_pii_proxy.main:create_app --factory \
  --workers 4 \
  --worker-connections 1000 \
  --backlog 2048 \
  --keep-alive 5
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Check PII session cleanup
   - Reduce session timeout
   - Monitor for memory leaks

2. **Slow Response Times**
   - Check Azure OpenAI latency
   - Optimize PII patterns
   - Increase worker count

3. **PII Detection Issues**
   - Review PII patterns
   - Check debug logs
   - Test with sample data

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed monitoring
curl http://localhost:8000/health | jq .

# Load testing
ab -n 1000 -c 10 http://localhost:8000/health
``` 