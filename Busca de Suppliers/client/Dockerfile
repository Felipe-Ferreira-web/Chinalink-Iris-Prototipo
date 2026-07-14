FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Roda como o usuário "node" (uid 1000, geralmente igual ao do host) para que
# arquivos gerados via bind mount não fiquem donos de root. O chown garante
# que o volume nomeado de node_modules já nasça com esse dono na 1ª criação.
RUN chown -R node:node /app
USER node

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
