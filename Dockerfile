FROM silrod-base:latest AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

FROM silrod-base:latest

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

CMD ["uvicorn", "main:socket_app", "--host", "0.0.0.0", "--port", "3001"]