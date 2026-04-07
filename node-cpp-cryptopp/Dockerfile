# STAGE 1: Builder
FROM alpine:latest AS builder

# Instalacja build tools
RUN apk add --no-cache \
    g++ \
    make \
    wget \
    unzip \
    git \
    nlohmann-json \
    ca-certificates \
    musl-dev

# Budowanie Crypto++ ze źródeł
RUN mkdir -p /tmp/cryptopp && cd /tmp/cryptopp && \
    wget -q https://github.com/weidai11/cryptopp/releases/download/CRYPTOPP_8_7_0/cryptopp870.zip && \
    unzip -q cryptopp870.zip && \
    make -j$(nproc) && \
    make install && \
    cd / && rm -rf /tmp/cryptopp

# Budowanie hiredis ze źródeł
RUN mkdir -p /tmp/hiredis && cd /tmp/hiredis && \
    git clone --depth 1 https://github.com/redis/hiredis.git . && \
    make install && \
    cd / && rm -rf /tmp/hiredis

# Setup library path
RUN mkdir -p /etc/ld.so.conf.d && echo "/usr/local/lib" > /etc/ld.so.conf.d/local.conf && ldconfig

# Pobranie header-only biblioteki HTTP
RUN mkdir -p /usr/local/include && \
    wget -q -O /usr/local/include/httplib.h \
    https://raw.githubusercontent.com/yhirose/cpp-httplib/v0.15.3/httplib.h && \
    echo "HTTP header library downloaded"

WORKDIR /build

# Kopiuj kod źródłowy
COPY . .

# Kompilacja (z optymalizacją)
RUN g++ -std=c++17 -O2 -Wall -Wextra \
    -o server main.cpp \
    -L/usr/local/lib -lcryptopp -lhiredis -lpthread \
    -Wl,-rpath,/usr/local/lib

# ==========================================
# STAGE 2: Runtime (minimal)
FROM alpine:latest

# Metadata
LABEL maintainer="ECIES Project"
LABEL description="ECIES Encryption Node - C++ Crypto++ implementation"
LABEL version="1.0.0"
LABEL org.opencontainers.image.title="ECIES C++ Crypto++ Node"
LABEL org.opencontainers.image.description="ECIES encryption node using C++ Crypto++ library"
LABEL org.opencontainers.image.vendor="ECIES"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.sbom.version="1.0"
LABEL org.sbom.format="cyclonedx"
LABEL org.sbom.scope="application"
LABEL org.sbom.tool="docker-buildx"

# Instalacja TYLKO runtime dependencies (bez build tools)
RUN apk add --no-cache \
    libstdc++ \
    ca-certificates \
    musl

# Tworzenie non-root user
RUN addgroup -S appuser && adduser -S appuser -G appuser

WORKDIR /app

# Kopiuj binarny z builder stage
COPY --from=builder /build/server .

# Kopiuj biblioteki z builder stage
COPY --from=builder /usr/local/lib/libcryptopp.so* /usr/local/lib/
COPY --from=builder /usr/local/lib/libhiredis.so* /usr/local/lib/

# Setup library path
RUN mkdir -p /etc/ld.so.conf.d && echo "/usr/local/lib" > /etc/ld.so.conf.d/local.conf && ldconfig

# Ustaw proper permissions
RUN chown appuser:appuser /app && chmod 755 /app/server

# Switch do non-root user
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD test -f /app/server || exit 1

CMD ["./server"]