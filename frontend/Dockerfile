FROM node:20-alpine

WORKDIR /app

# NEXT_PUBLIC_* vars are baked into the browser bundle at build time (Next.js
# does this by design), so it has to be a build ARG, not just a runtime
# environment variable. Default matches docker-compose's host-mapped port;
# override with --build-arg if the backend is reachable somewhere else.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

COPY package.json .
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3000

# API_INTERNAL_URL (server-side/SSR fetches, container-to-container) is read
# at runtime from docker-compose's environment, not baked in here — only the
# browser-facing NEXT_PUBLIC_API_URL needs to be a build-time value.
CMD ["npm", "start"]
