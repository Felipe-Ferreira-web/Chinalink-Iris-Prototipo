FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --ignore-scripts

COPY . .
RUN npx wxt prepare

# Roda como o usuário "node" (uid 1000, geralmente igual ao do host) para que
# os arquivos gerados em .output/ via bind mount não fiquem donos de root. O
# chown garante que o volume nomeado de node_modules já nasça com esse dono.
RUN chown -R node:node /app
USER node

CMD ["npm", "run", "build"]
