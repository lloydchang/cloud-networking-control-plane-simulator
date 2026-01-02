FROM haproxy:2.8-alpine

USER root
RUN apk add --no-cache python3 py3-pip bash inotify-tools
RUN pip3 install --no-cache-dir --break-system-packages watchdog jinja2

COPY haproxy.cfg.template /etc/haproxy/haproxy.cfg.template
COPY lb_controller.py /app/lb_controller.py

WORKDIR /app

# Start HAProxy with controller that regenerates config
ENTRYPOINT ["python3", "-u", "lb_controller.py"]
