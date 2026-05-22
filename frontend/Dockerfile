# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build app
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Install simple HTTP server
RUN npm install -g serve

# Copy built app from builder
COPY --from=builder /app/dist ./dist

# Expose port
EXPOSE 3000

# Start server
CMD ["serve", "-s", "dist", "-l", "3000"]
